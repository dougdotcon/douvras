"""Modelagem de quantizacao (Metodo 12.4 / 15, dias 46-60).

Este modulo e o mais perigoso do Atlas, e por isso o mais restrito: ele estima *quanto se
ganha* ao baixar precisao, mas **nao mede quanto se perde em qualidade**. A perda e a lacuna
G-002. Enquanto ela estiver aberta, todo plano sai marcado como hipotese a validar em bancada,
nunca como recomendacao.

O ganho estimado e real e verificavel (bytes e tempo sao aritmetica); o custo estimado e um
prior de literatura. Misturar os dois num unico numero de "beneficio" seria exatamente o
cherry-picking que a auditoria adversarial do Metodo 4.4 procura.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .hardware import CONFIG_DIR, Device
from .ir.graph import Graph, OpKind, Workload
from .profiler import PhaseProfile, profile
from douvras_core.status import Finding, Status

QUANTIZABLE_KINDS = (OpKind.LINEAR, OpKind.EMBEDDING)


@dataclass
class QuantPriors:
    """Priors de tolerancia por papel. Versionados e sobrescritiveis por medicao."""

    roles: dict[str, dict[str, float]]
    position_penalty: dict[str, Any]
    moe_penalty: dict[str, Any]
    acceptance_threshold: float
    version: str = "1.0"
    measured: dict[str, dict[str, float]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "QuantPriors":
        doc = json.loads(
            (path or CONFIG_DIR / "quantization_priors.v1.json").read_text(encoding="utf-8")
        )
        return cls(
            roles=doc["roles"],
            position_penalty=doc["position_penalty"],
            moe_penalty=doc["moe_penalty"],
            acceptance_threshold=float(doc["acceptance_threshold"]["value"]),
            version=doc["_meta"]["version"],
        )

    def with_evidence(self, measured: Mapping[str, Mapping[str, float]]) -> "QuantPriors":
        """Substitui priors por medicoes reais, fechando parcialmente G-002.

        Chaves medidas tem precedencia absoluta sobre priors: evidencia experimental nao e
        combinada com palpite, ela o substitui.
        """
        new = QuantPriors(
            roles=dict(self.roles),
            position_penalty=self.position_penalty,
            moe_penalty=self.moe_penalty,
            acceptance_threshold=self.acceptance_threshold,
            version=self.version,
        )
        new.measured = {k: dict(v) for k, v in measured.items()}
        return new

    # -- consulta -------------------------------------------------------------------
    def tolerance(
        self,
        role: str,
        precision: str,
        *,
        layer: int | None = None,
        num_layers: int | None = None,
        is_moe: bool = False,
    ) -> Finding:
        """Tolerancia do papel a precisao, com status conforme a origem do numero."""
        if role in self.measured and precision in self.measured[role]:
            return Finding(
                name=f"quant.{role}.{precision}",
                value=float(self.measured[role][precision]),
                status=Status.EXPERIMENTAL_EVIDENCE,
                unit="tolerancia [0,1]",
                note="medido; substitui o prior",
            )

        base = self.roles.get(role, {}).get(precision)
        if base is None:
            return Finding(
                name=f"quant.{role}.{precision}",
                value=0.0,
                status=Status.OPEN_GAP,
                unit="tolerancia [0,1]",
                gaps=("G-002",),
                note=f"sem prior para o papel {role!r} em {precision}",
            )

        val = float(base)
        notes = []
        pp = self.position_penalty
        if layer is not None and num_layers:
            if layer < int(pp["first_layers"]) or layer >= num_layers - int(pp["last_layers"]):
                val *= float(pp["factor"])
                notes.append("penalidade de camada de borda")
        if is_moe:
            val *= float(self.moe_penalty["factor"])
            notes.append("penalidade de roteamento esparso")

        return Finding(
            name=f"quant.{role}.{precision}",
            value=val,
            status=Status.ASSUMPTION,
            unit="tolerancia [0,1]",
            assumptions=("A-004",),
            gaps=("G-002",),
            note="; ".join(notes) or "prior de literatura, nao medido",
        )

    def best_precision(
        self, role: str, *, layer: int | None = None, num_layers: int | None = None,
        is_moe: bool = False, candidates: Sequence[str] = ("ternary", "int4", "int8"),
    ) -> tuple[str, Finding]:
        """Precisao mais agressiva cuja tolerancia ainda passa do limite de aceitacao."""
        for prec in candidates:  # do mais agressivo ao mais conservador
            f = self.tolerance(role, prec, layer=layer, num_layers=num_layers, is_moe=is_moe)
            if f.value >= self.acceptance_threshold:
                return prec, f
        return "bf16", Finding(
            name=f"quant.{role}.bf16",
            value=1.0,
            status=Status.ASSUMPTION,
            unit="tolerancia [0,1]",
            assumptions=("A-004",),
            gaps=("G-002",),
            note="nenhuma precisao reduzida passa do limite; mantem precisao nativa",
        )


@dataclass
class QuantPlan:
    """Atribuicao de precisao por papel de operador, com justificativa por papel."""

    name: str
    by_role: dict[str, str]
    tolerance: dict[str, Finding] = field(default_factory=dict)
    priors_version: str = "1.0"

    def precision_for(self, role: str, default: str = "bf16") -> str:
        return self.by_role.get(role, default)

    @property
    def weakest_status(self) -> Status:
        return Status(min((f.status for f in self.tolerance.values()), default=int(Status.OPEN_GAP)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "priors_version": self.priors_version,
            "weakest_status": self.weakest_status.name,
            "by_role": self.by_role,
            "tolerance": {k: round(float(v.value), 3) for k, v in sorted(self.tolerance.items())},
        }


def uniform_plan(graph: Graph, precision: str) -> QuantPlan:
    """Plano ingenuo: tudo na mesma precisao. Serve de baseline, nao de recomendacao."""
    roles = {n.role for n in graph if n.kind in QUANTIZABLE_KINDS}
    return QuantPlan(name=f"uniform-{precision}", by_role={r: precision for r in roles})


def sensitivity_plan(
    graph: Graph,
    priors: QuantPriors,
    *,
    is_moe: bool = False,
    candidates: Sequence[str] = ("ternary", "int4", "int8"),
) -> QuantPlan:
    """Plano heterogeneo: cada papel recebe a precisao mais agressiva que seu prior admite.

    Camadas de borda e roteadores acabam em precisao mais alta que o miolo — que e
    exatamente a estrutura estratificada que a tese C-005 preve.
    """
    L = graph.num_layers
    chosen: dict[str, str] = {}
    tol: dict[str, Finding] = {}
    for n in graph:
        if n.kind not in QUANTIZABLE_KINDS:
            continue
        prec, f = priors.best_precision(
            n.role, layer=n.layer, num_layers=L, is_moe=is_moe, candidates=candidates
        )
        # papel presente em varias camadas: fica com a precisao mais conservadora exigida
        order = {"ternary": 0, "int4": 1, "int8": 2, "bf16": 3}
        if n.role not in chosen or order[prec] > order[chosen[n.role]]:
            chosen[n.role] = prec
            tol[n.role] = f
    return QuantPlan(
        name="sensitivity", by_role=chosen, tolerance=tol, priors_version=priors.version
    )


@dataclass
class PlanEvaluation:
    """Ganho estimado de um plano — e a declaracao explicita do que nao foi medido."""

    plan: QuantPlan
    baseline: PhaseProfile
    quantized: PhaseProfile

    @property
    def weight_bytes_before(self) -> float:
        return self.baseline.weight_bytes

    @property
    def weight_bytes_after(self) -> float:
        return self.quantized.weight_bytes

    @property
    def memory_reduction(self) -> float:
        b = self.weight_bytes_before
        return 1.0 - (self.weight_bytes_after / b) if b else 0.0

    @property
    def speedup(self) -> float:
        t = self.quantized.total_time
        return (self.baseline.total_time / t) if t else float("inf")

    def findings(self) -> list[Finding]:
        common = dict(assumptions=("A-002", "A-004", "A-005"), gaps=("G-002", "G-003"))
        return [
            Finding(
                name=f"quant.{self.plan.name}.memory_reduction",
                value=self.memory_reduction,
                status=Status.CONDITIONAL_RESULT,
                unit="fracao",
                note="aritmetica exata sobre bytes de peso; nao depende de prior",
                **{k: v for k, v in common.items() if k != "assumptions"},
                assumptions=("A-004",),
            ),
            Finding(
                name=f"quant.{self.plan.name}.speedup",
                value=self.speedup,
                status=Status.CONDITIONAL_RESULT,
                unit="x sobre baseline",
                **common,
            ),
            Finding(
                name=f"quant.{self.plan.name}.quality_delta",
                value=None,
                status=Status.OPEN_GAP,
                unit="perplexidade / acuracia",
                gaps=("G-002",),
                note="NAO MEDIDO. Sem isto o plano nao e recomendavel, apenas testavel.",
            ),
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.as_dict(),
            "weight_gb_before": self.weight_bytes_before / 1e9,
            "weight_gb_after": self.weight_bytes_after / 1e9,
            "memory_reduction": round(self.memory_reduction, 4),
            "time_ms_before": self.baseline.total_time * 1e3,
            "time_ms_after": self.quantized.total_time * 1e3,
            "speedup": round(self.speedup, 3),
            "quality_delta": "UNMEASURED (G-002)",
            "findings": [f.as_dict() for f in self.findings()],
        }


def evaluate_plan(
    graph: Graph,
    plan: QuantPlan,
    workload: Workload,
    device: Device,
    baseline_precision: str = "bf16",
) -> PlanEvaluation:
    """Perfila o grafo com e sem o plano, no mesmo dispositivo e workload."""
    base = profile(graph, workload, device, weight_precision=baseline_precision)
    quant = profile(
        graph,
        workload,
        device,
        weight_precision=baseline_precision,
        precision_plan=plan.by_role,
    )
    return PlanEvaluation(plan=plan, baseline=base, quantized=quant)


def quantizable_cost_share(graph: Graph, prof: PhaseProfile, priors: QuantPriors,
                           precision: str = "int4") -> Finding:
    """Fracao do custo concentrada em papeis que o prior considera quantizaveis.

    Responde a pergunta que decide o projeto: mesmo que a quantizacao funcione perfeitamente,
    quanto do custo ela alcanca?
    """
    L = graph.num_layers
    ok_roles = {
        n.role
        for n in graph
        if n.kind in QUANTIZABLE_KINDS
        and priors.tolerance(n.role, precision, layer=n.layer, num_layers=L).value
        >= priors.acceptance_threshold
    }
    share = sum(v["share"] for r, v in prof.by_role().items() if r in ok_roles)
    return Finding(
        name=f"quant.reachable_cost_share.{precision}",
        value=share,
        status=Status.CONDITIONAL_RESULT,
        unit="fracao do tempo",
        assumptions=("A-002", "A-004"),
        gaps=("G-002", "G-003"),
        note=f"papeis alcancados: {', '.join(sorted(ok_roles)) or 'nenhum'}",
    )


__all__ = [
    "QuantPriors",
    "QuantPlan",
    "PlanEvaluation",
    "uniform_plan",
    "sensitivity_plan",
    "evaluate_plan",
    "quantizable_cost_share",
    "QUANTIZABLE_KINDS",
]
