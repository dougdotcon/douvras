"""Hybrid Partitioning Engine (Metodo 12.7).

Divide o caminho de inferencia em quatro regioes e — o ponto central deste modulo — calcula
o **teto de Amdahl** da particao. Endurecer 70 por cento do custo com aceleracao infinita
rende no maximo 3,3x no total. Nenhuma quantidade de silicio muda essa aritmetica.

E por isso que o Metodo classifica "ganho de 100x" como CONDITIONAL_HYPOTHESIS (C-004): so
sobrevive se a fracao endurecida for quase tudo **e** o resto for movido junto. Este modulo
torna essa condicao explicita em vez de deixa-la implicita no entusiasmo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any, Sequence

from .hardware import CONFIG_DIR
from .readiness import HardeningCandidate
from douvras_core.status import Finding, Status, derive


class Level(IntEnum):
    """Escada de especializacao do Metodo 6.5. Quanto maior, maior ganho e maior risco."""

    GENERIC_SOFTWARE = 0
    OPTIMIZED_KERNEL = 1
    OPERATOR_FAMILY_COMPILER = 2
    ARCHITECTURE_ACCELERATOR = 3
    MODEL_FAMILY_ACCELERATOR = 4
    PARTIAL_FIXED_WEIGHTS = 5
    FULLY_FIXED_CIRCUIT = 6

    @property
    def label(self) -> str:
        return {
            0: "software generico",
            1: "kernels otimizados",
            2: "compilacao por familia de operadores",
            3: "acelerador por arquitetura",
            4: "acelerador por familia de modelos",
            5: "modelo e pesos parcialmente fixados",
            6: "modelo ou circuito integralmente fixado",
        }[int(self)]


class Region(StrEnum):
    FIXED = "fixed"                    # ASIC / IP com pesos em ROM
    CONFIGURABLE = "configurable"      # memoria programavel: LoRA, adapters, por cliente
    RECONFIGURABLE = "reconfigurable"  # FPGA / eFPGA: operadores emergentes, roteamento
    PROGRAMMABLE = "programmable"      # CPU/GPU: controle, sampling, fallback

    @property
    def target(self) -> str:
        return {
            "fixed": "ASIC/IP fixo",
            "configurable": "memoria programavel",
            "reconfigurable": "FPGA/eFPGA",
            "programmable": "CPU/GPU",
        }[self.value]


DEFAULT_POLICY: dict[str, Any] = {
    "version": "1.0",
    "fixed": {"min_lhs": 0.55, "min_regularity": 0.9, "min_memory_predictability": 0.9,
              "min_quant_tolerance": 0.6, "min_stability": 0.6},
    "reconfigurable": {"max_regularity": 0.9, "or_data_dependent": True},
    "programmable_roles": ["sampling", "expert_combine", "router", "expert_dispatch"],
    "configurable_note": "Todo bloco fixo recebe sobreposicao de delta (LoRA/adapters) — "
                         "e o que preserva adaptabilidade sobre uma base endurecida.",
}


def load_policy(path: Path | None = None) -> dict[str, Any]:
    p = path or CONFIG_DIR / "partition_policy.v1.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return dict(DEFAULT_POLICY)


class Blocker(StrEnum):
    """Por que um candidato nao entrou na regiao fixa.

    Existe porque "bloqueado pela estabilidade" e "bloqueado por irregularidade" pedem acoes
    opostas — observar mais versoes contra reprojetar o operador — e o relatorio atribuia os dois
    a mesma causa (retratacao R-002, grupo D.4).
    """

    NONE = "none"
    STABILITY = "estabilidade"
    IRREGULAR = "irregularidade"
    QUANTIZATION = "quantizacao"
    RUNTIME_POLICY = "politica de runtime"


@dataclass
class Assignment:
    candidate: HardeningCandidate
    region: Region
    reason: str
    blocker: Blocker = Blocker.NONE

    @property
    def cost_share(self) -> float:
        return self.candidate.cost_share


@dataclass
class Partition:
    """Resultado do particionamento, com cobertura de custo por regiao."""

    model_id: str
    phase_label: str
    assignments: list[Assignment] = field(default_factory=list)
    uncovered_share: float = 0.0
    policy_version: str = "1.0"

    def by_region(self, region: Region) -> list[Assignment]:
        return [a for a in self.assignments if a.region is region]

    def share(self, region: Region) -> float:
        return sum(a.cost_share for a in self.by_region(region))

    @property
    def hardened_share(self) -> float:
        """Fracao do custo que a regiao fixa cobre. E o `f` da lei de Amdahl."""
        return self.share(Region.FIXED)

    def blocked_share(self, blocker: Blocker) -> float:
        """Fracao do custo barrada por um motivo especifico.

        Distinguir os motivos muda a acao recomendada: bloqueio por estabilidade pede observar
        mais versoes; bloqueio por irregularidade pede reprojetar o operador. Somar os dois numa
        frase unica atribuia 87 pontos percentuais do Mixtral a causa errada (R-002, D.4).
        """
        return sum(a.cost_share for a in self.assignments if a.blocker is blocker)

    def blockers(self) -> dict[str, float]:
        return {
            b.value: self.blocked_share(b)
            for b in Blocker
            if b is not Blocker.NONE and self.blocked_share(b) > 0
        }

    @property
    def level(self) -> Level:
        """Nivel de especializacao implicado pela particao (escada do Metodo 6.5).

        Regioes fixa e reconfiguravel puxam para niveis diferentes: fixar pesos e nivel 5,
        enquanto acelerar operadores regulares em logica reprogramavel e nivel 3. Uma particao
        sem regiao fixa mas com quase todo o custo em operadores regulares nao e "software
        generico" — e um acelerador de arquitetura esperando validacao.
        """
        f = self.hardened_share
        r = self.share(Region.RECONFIGURABLE)
        if f >= 0.75:
            return Level.PARTIAL_FIXED_WEIGHTS
        if f >= 0.55:
            return Level.MODEL_FAMILY_ACCELERATOR
        if f >= 0.35 or r >= 0.50:
            return Level.ARCHITECTURE_ACCELERATOR
        if f >= 0.15 or r >= 0.25:
            return Level.OPERATOR_FAMILY_COMPILER
        return Level.OPTIMIZED_KERNEL

    def amdahl_ceiling(self, hardened_speedup: float = float("inf")) -> float:
        """Aceleracao maxima do sistema dado que so a regiao fixa acelera.

        Com ``hardened_speedup=inf`` devolve 1/(1-f): o teto absoluto da particao.
        """
        f = self.hardened_share
        if hardened_speedup == float("inf"):
            return 1.0 / (1.0 - f) if f < 1.0 else float("inf")
        return 1.0 / ((1.0 - f) + f / hardened_speedup)

    def required_speedup_for(self, target: float) -> float | None:
        """Aceleracao necessaria na regiao fixa para o sistema atingir ``target``.

        Devolve None quando o alvo e inalcancavel — o que responde diretamente a C-004.
        """
        f = self.hardened_share
        denom = 1.0 / target - (1.0 - f)
        if denom <= 0:
            return None
        return f / denom

    def findings(self) -> list[Finding]:
        parents = [
            c.candidate.scorecard.finding() for c in self.assignments
        ] or [Finding("partition.empty", 0.0, Status.OPEN_GAP, gaps=("G-001",))]
        return [
            derive(
                f"{self.model_id}.partition.hardened_share",
                self.hardened_share,
                parents,
                ceiling=Status.COMPUTATIONAL_EVIDENCE,
                unit="fracao do tempo",
                note=f"regiao fixa sob politica v{self.policy_version}",
            ),
            derive(
                f"{self.model_id}.partition.amdahl_ceiling",
                self.amdahl_ceiling(),
                parents,
                ceiling=Status.COMPUTATIONAL_EVIDENCE,
                unit="x sobre baseline",
                note="teto com aceleracao infinita na regiao fixa; o resto permanece no host",
            ),
        ]

    def as_text(self) -> str:
        """Bloco de recomendacao no formato do Metodo 12.7."""
        lines = []
        for region in (Region.FIXED, Region.CONFIGURABLE, Region.RECONFIGURABLE, Region.PROGRAMMABLE):
            items = self.by_region(region)
            if not items:
                continue
            head = f"{region.target}: {self.share(region):.1%} do custo"
            lines.append(head)
            for a in sorted(items, key=lambda x: -x.cost_share):
                lines.append(f"  ├── {a.candidate.role:<20} {a.cost_share:6.1%}  {a.reason}")
            if lines:
                lines[-1] = lines[-1].replace("├──", "└──")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "phase": self.phase_label,
            "policy_version": self.policy_version,
            "level": int(self.level),
            "level_label": self.level.label,
            "hardened_share": round(self.hardened_share, 4),
            "amdahl_ceiling": round(self.amdahl_ceiling(), 3),
            "uncovered_share": round(self.uncovered_share, 4),
            "blocked_by": {k: round(v, 4) for k, v in self.blockers().items()},
            "regions": {
                r.value: {
                    "target": r.target,
                    "share": round(self.share(r), 4),
                    "roles": [
                        {"role": a.candidate.role, "share": round(a.cost_share, 4),
                         "precision": a.candidate.precision, "reason": a.reason}
                        for a in sorted(self.by_region(r), key=lambda x: -x.cost_share)
                    ],
                }
                for r in Region
                if self.by_region(r)
            },
        }


def partition(
    candidates: Sequence[HardeningCandidate],
    *,
    model_id: str,
    phase_label: str = "serving",
    policy: dict[str, Any] | None = None,
) -> Partition:
    """Atribui cada candidato a uma regiao segundo a politica declarada.

    A politica e `ENGINEERING_DECISION` versionada, nao descoberta: os limiares saem de
    um arquivo de configuracao e mudar de opiniao sobre eles exige mudar o arquivo, nao o
    codigo — e o diff fica no historico.
    """
    pol = policy or load_policy()
    fx = pol["fixed"]
    prog_roles = set(pol.get("programmable_roles", []))

    part = Partition(model_id=model_id, phase_label=phase_label,
                     policy_version=str(pol.get("version", "1.0")))

    for c in candidates:
        region, reason, blocker = _assign(c, fx, prog_roles)
        part.assignments.append(
            Assignment(candidate=c, region=region, reason=reason, blocker=blocker)
        )

    # Sobreposicao configuravel: toda regiao fixa admite deltas por cliente (LoRA/adapters).
    if part.by_region(Region.FIXED):
        pass  # representado no relatorio; nao consome fracao de custo propria

    part.uncovered_share = max(0.0, 1.0 - sum(a.cost_share for a in part.assignments))
    return part


def _assign(
    c: HardeningCandidate, fx: dict[str, Any], prog_roles: set[str]
) -> tuple[Region, str, Blocker]:
    """Decide a regiao de um candidato e explica **qual** condicao decidiu.

    A razao textual importa tanto quanto a regiao: "instavel ou nao quantizavel" nao permite
    que ninguem discorde de forma produtiva. "E=0.48 abaixo do limite 0.60" permite.
    """
    f = c.scorecard.factors
    R, M, Q, E = (float(f[k].value) for k in ("R", "M", "Q", "E"))
    fails: list[str] = []
    if c.lhs < fx["min_lhs"]:
        fails.append(f"LHS={c.lhs:.2f} < {fx['min_lhs']}")
    if E < fx["min_stability"]:
        fails.append(f"E={E:.2f} < {fx['min_stability']}")
    if Q < fx["min_quant_tolerance"]:
        fails.append(f"Q={Q:.2f} < {fx['min_quant_tolerance']}")

    if c.role in prog_roles:
        return (
            Region.PROGRAMMABLE,
            "controle dinamico ou politica de runtime",
            Blocker.RUNTIME_POLICY,
        )

    # Tabela indexada (embeddings): acesso dependente de dado, mas e memoria, nao logica.
    # Mandar para FPGA seria confundir "irregular" com "reconfiguravel".
    if c.kind == "embedding":
        if not fails:
            return (
                Region.FIXED,
                f"tabela indexada estavel: ROM enderecada por token ({c.precision})",
                Blocker.NONE,
            )
        return (
            Region.CONFIGURABLE,
            f"tabela indexada, mas {'; '.join(fails)} — memoria carregavel, nao ROM",
            Blocker.STABILITY if E < fx["min_stability"] else Blocker.QUANTIZATION,
        )

    if R < fx["min_regularity"] or M < fx["min_memory_predictability"]:
        return (
            Region.RECONFIGURABLE,
            f"irregular (R={R:.2f}, M={M:.2f}): operador emergente ou roteamento",
            Blocker.IRREGULAR,
        )

    if not fails:
        return (
            Region.FIXED,
            f"LHS={c.lhs:.2f}, estavel (E={E:.2f}), quantizavel em {c.precision}",
            Blocker.NONE,
        )

    # Regular e quantizavel, mas instavel: prototipar em logica reprogramavel antes de mascara.
    blocker = Blocker.STABILITY if E < fx["min_stability"] else Blocker.QUANTIZATION
    if Q >= fx["min_quant_tolerance"]:
        return (
            Region.RECONFIGURABLE,
            f"regular e quantizavel, porem {'; '.join(fails)}: prototipar antes de fixar",
            blocker,
        )
    return Region.PROGRAMMABLE, "; ".join(fails), blocker


def hardening_ceiling_finding(part: Partition, claimed_gain: float = 100.0) -> Finding:
    """Confronta um ganho alegado com o teto da particao. Ferramenta anti-C-004.

    O teto e aritmetica exata sobre `hardened_share`, mas `hardened_share` sai de fatores com
    premissas e lacunas. Emitir `COMPUTATIONAL_EVIDENCE` direto publicava o mesmo valor em duas
    linhas do Anexo D com status diferentes — uma `ASSUMPTION` com quatro lacunas, outra sem
    nenhuma (retratacao R-002, grupo K).
    """
    ceiling = part.amdahl_ceiling()
    needed = part.required_speedup_for(claimed_gain)
    if needed is None:
        note = (
            f"IMPOSSIVEL nesta particao: teto e {ceiling:.2f}x mesmo com aceleracao infinita "
            f"na regiao fixa ({part.hardened_share:.1%} do custo). Alcancar {claimed_gain:g}x "
            f"exigiria mover tambem a regiao programavel para o mesmo silicio."
        )
    else:
        note = (
            f"exigiria {needed:.1f}x na regiao fixa ({part.hardened_share:.1%} do custo) "
            f"mantendo o resto no host"
        )
    parents = [a.candidate.scorecard.finding() for a in part.assignments] or [
        Finding("partition.empty", 0.0, Status.OPEN_GAP, gaps=("G-001",))
    ]
    return derive(
        "partition.claim_check",
        ceiling,
        parents,
        ceiling=Status.COMPUTATIONAL_EVIDENCE,
        unit="x (teto do sistema)",
        note=note,
    )


__all__ = [
    "Level",
    "Region",
    "Assignment",
    "Partition",
    "partition",
    "load_policy",
    "hardening_ceiling_finding",
    "DEFAULT_POLICY",
]
