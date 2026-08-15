"""Silicon Readiness Engine (Metodo 12.6): LHS e SRS.

Os dois scores implementam literalmente as formulas do Metodo, com uma adicao que o proprio
Metodo exige e que costuma ser omitida na pratica: **a analise de sensibilidade dos pesos**.

Um score composto por sete fatores com pesos escolhidos a mao produz um ranking que parece
objetivo. Se esse ranking troca quando os pesos variam 20 por cento, ele nao decide nada — e
qualquer recomendacao derivada dele deve ser retratada (falsificador F3, alegacao C-006).
Por isso `sensitivity()` nao e opcional no fluxo: `Assessment` recusa emitir sem ela.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import numpy as np

from .hardware import CONFIG_DIR
from .ir.graph import Graph, OpKind
from .quantization import QuantPriors
from douvras_core.status import Finding, Status, derive


class CostProfile(Protocol):
    """Qualquer coisa que saiba dizer a participacao de cada papel no custo."""

    def by_role(self) -> dict[str, dict[str, float]]: ...


# --------------------------------------------------------------------------------------
# Pesos versionados
# --------------------------------------------------------------------------------------


@dataclass
class Weights:
    version: str
    lhs: dict[str, float]
    srs: dict[str, float]
    bands: dict[str, tuple[float, float]]
    sensitivity: dict[str, Any]
    calibration_status: str = "UNCALIBRATED"

    @classmethod
    def load(cls, path: Path | None = None) -> "Weights":
        doc = json.loads(
            (path or CONFIG_DIR / "readiness_weights.v1.json").read_text(encoding="utf-8")
        )
        bands = {
            k: (float(v[0]), float(v[1]))
            for k, v in doc["SRS"]["decision_bands"].items()
            if isinstance(v, list)
        }
        return cls(
            version=doc["_meta"]["version"],
            lhs=dict(doc["LHS"]["weights"]),
            srs=dict(doc["SRS"]["weights"]),
            bands=bands,
            sensitivity=dict(doc["sensitivity"]),
            calibration_status=doc["_meta"].get("calibration_status", "UNCALIBRATED"),
        )

    def band_for(self, score: float) -> str:
        for name, (lo, hi) in sorted(self.bands.items(), key=lambda kv: kv[1][0]):
            if lo <= score < hi:
                return name
        return "weights_partially_fixed" if score >= 0 else "software"


# --------------------------------------------------------------------------------------
# Candidato a endurecimento
# --------------------------------------------------------------------------------------


def _log_norm(x: float, lo: float, hi: float) -> float:
    """Normaliza em escala log para [0,1], saturando fora da faixa."""
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return math.log10(x / lo) / math.log10(hi / lo)


@dataclass
class ScoreCard:
    """Um score decomposto: cada fator e um Finding com status proprio."""

    name: str
    kind: str                       # "LHS" ou "SRS"
    factors: dict[str, Finding]
    weights: dict[str, float]
    #: Versao do arquivo de pesos. Vem de `_meta.version`; ler de `weights['_version']` sempre
    #: devolvia "1.0" porque a chave nunca existiu no dicionario de pesos.
    weights_version: str = "1.0"

    @property
    def score(self) -> float:
        return sum(self.weights.get(k, 0.0) * float(f.value) for k, f in self.factors.items())

    @property
    def contributions(self) -> dict[str, float]:
        return {
            k: self.weights.get(k, 0.0) * float(f.value) for k, f in self.factors.items()
        }

    def finding(self) -> Finding:
        return derive(
            f"{self.kind}.{self.name}",
            self.score,
            list(self.factors.values()),
            ceiling=Status.COMPUTATIONAL_EVIDENCE,
            unit=f"score {self.kind}",
            note=f"pesos v{self.weights_version}",
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "score": round(self.score, 4),
            "status": self.finding().status.name,
            "factors": {
                k: {
                    "value": round(float(f.value), 4),
                    "weight": self.weights.get(k, 0.0),
                    "contribution": round(self.contributions[k], 4),
                    "status": f.status.name,
                    "note": f.note,
                }
                for k, f in self.factors.items()
            },
        }


@dataclass
class HardeningCandidate:
    """Um papel de operador avaliado como candidato a virar circuito fixo."""

    role: str
    block_role: str
    instances_per_token: float
    cost_share: float
    scorecard: ScoreCard
    precision: str = "bf16"
    weight_elems: int = 0
    kind: str = ""

    @property
    def lhs(self) -> float:
        return self.scorecard.score

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "block": self.block_role,
            "instances_per_token": self.instances_per_token,
            "cost_share": round(self.cost_share, 4),
            "recommended_precision": self.precision,
            "weight_elems": self.weight_elems,
            "LHS": round(self.lhs, 4),
            "scorecard": self.scorecard.as_dict(),
        }


def build_candidates(
    graph: Graph,
    prof: CostProfile,
    priors: QuantPriors,
    weights: Weights,
    *,
    stability_by_block: Mapping[str, Finding] | None = None,
    lifetime_by_family: Finding | None = None,
    is_moe: bool = False,
    min_cost_share: float = 0.005,
) -> list[HardeningCandidate]:
    """Constroi um candidato por papel de operador com peso, ordenado por LHS.

    Papeis sem peso (softmax, residual, RoPE) nao sao candidatos a *endurecimento de pesos*;
    entram na analise pela participacao de custo, mas nao viram bloco de IP com ROM.
    """
    shares = {r: d["share"] for r, d in prof.by_role().items()}
    L = graph.num_layers

    by_role: dict[str, list] = {}
    for n in graph:
        by_role.setdefault(n.role, []).append(n)

    out: list[HardeningCandidate] = []
    for role, nodes in by_role.items():
        share = shares.get(role, 0.0)
        if share < min_cost_share:
            continue
        n0 = nodes[0]
        quantizable = n0.kind in (OpKind.LINEAR, OpKind.EMBEDDING)

        # E — estabilidade estrutural do bloco que contem o papel
        block_role = n0.block.split(".")[-1]
        if stability_by_block and block_role in stability_by_block:
            e_f = stability_by_block[block_role]
            E = Finding(f"E.{role}", float(e_f.value), e_f.status, unit="[0,1]",
                        assumptions=e_f.assumptions, gaps=e_f.gaps, note=e_f.note)
        else:
            E = Finding(f"E.{role}", 0.0, Status.OPEN_GAP, unit="[0,1]", gaps=("G-001",),
                        note="estabilidade nao computada para este bloco")

        # F — fracao do custo (aritmetica sobre o perfil)
        F = Finding(f"F.{role}", share, Status.CONDITIONAL_RESULT, unit="fracao do tempo",
                    assumptions=("A-002", "A-005"), gaps=("G-003",))

        # R — regularidade: 1 - fracao de nos com controle dinamico
        dyn = sum(1 for n in nodes if n.dynamic) / len(nodes)
        R = Finding(f"R.{role}", 1.0 - dyn, Status.MODEL, unit="[0,1]",
                    gaps=("G-001",), note=f"{len(nodes)} nos, {dyn:.0%} dinamicos")

        # Q — tolerancia a quantizacao, avaliada numa camada representativa.
        # Usar a camada 0 aplicaria a penalidade de borda a papeis que ocupam todas as camadas;
        # a camada mediana representa o caso tipico, e as bordas ficam a cargo do plano
        # heterogeneo por camada (`quantization.sensitivity_plan`).
        if quantizable:
            layers = sorted({n.layer for n in nodes if n.layer is not None})
            rep_layer = layers[len(layers) // 2] if layers else None
            prec, q_f = priors.best_precision(
                role, layer=rep_layer, num_layers=L, is_moe=is_moe
            )
            where = f"camada representativa {rep_layer}" if rep_layer is not None else "sem indice de camada"
            Q = Finding(f"Q.{role}", float(q_f.value), q_f.status, unit="[0,1]",
                        assumptions=q_f.assumptions, gaps=q_f.gaps,
                        note=f"melhor precisao aceitavel: {prec} ({where})")
        else:
            prec = "bf16"
            Q = Finding(f"Q.{role}", 0.0, Status.MODEL, unit="[0,1]",
                        note="papel sem pesos: quantizacao de peso nao se aplica")

        # V — volume de execucao por token
        inst = sum(n.active_count for n in nodes)
        V = Finding(f"V.{role}", _log_norm(inst + 1, 1.0, 256.0), Status.MODEL, unit="[0,1]",
                    note=f"{inst} instancias por token")

        # M — previsibilidade de memoria
        dda = sum(1 for n in nodes if n.data_dependent_addressing) / len(nodes)
        M = Finding(f"M.{role}", 1.0 - dda, Status.MODEL, unit="[0,1]",
                    note=f"{dda:.0%} com enderecamento dependente de dado")

        # L — vida util esperada da estrutura
        if lifetime_by_family is not None:
            Lf = Finding(f"L.{role}", float(lifetime_by_family.value), lifetime_by_family.status,
                         unit="[0,1]", assumptions=lifetime_by_family.assumptions,
                         gaps=lifetime_by_family.gaps, note=lifetime_by_family.note)
        else:
            Lf = Finding(f"L.{role}", 0.0, Status.OPEN_GAP, unit="[0,1]", gaps=("G-006",),
                         note="vida util nao estimada")

        sc = ScoreCard(
            name=role,
            kind="LHS",
            factors={"E": E, "F": F, "R": R, "Q": Q, "V": V, "M": M, "L": Lf},
            weights=weights.lhs,
            weights_version=weights.version,
        )
        out.append(
            HardeningCandidate(
                role=role,
                block_role=block_role,
                instances_per_token=inst,
                cost_share=share,
                scorecard=sc,
                precision=prec,
                weight_elems=sum(n.weight_elems for n in nodes),
                kind=str(n0.kind),
            )
        )

    return sorted(out, key=lambda c: -c.lhs)


# --------------------------------------------------------------------------------------
# SRS — nivel do caso, nao do bloco
# --------------------------------------------------------------------------------------


def build_srs(
    weights: Weights,
    *,
    architectural_stability: Finding,
    hotspot_concentration: Finding,
    annual_tokens: float,
    perf_per_watt_gain: Finding,
    low_precision_robustness: Finding,
    data_availability: Finding,
    codesign_compatibility: Finding,
    revenue_potential: Finding,
    obsolescence_risk: Finding,
    nre_risk: Finding,
    case_name: str = "case",
) -> ScoreCard:
    """Monta o SRS do caso. Cada fator entra como Finding, com seu proprio status."""
    T = Finding(
        "T.throughput",
        _log_norm(max(annual_tokens, 1.0), 1e9, 1e15),
        Status.ASSUMPTION,
        unit="[0,1]",
        assumptions=("A-007",),
        gaps=("G-009",),
        note=f"{annual_tokens:.3g} tokens/ano declarados pelo caso",
    )
    return ScoreCard(
        name=case_name,
        kind="SRS",
        weights_version=weights.version,
        factors={
            "A": architectural_stability,
            "H": hotspot_concentration,
            "T": T,
            "P": perf_per_watt_gain,
            "Q": low_precision_robustness,
            "D": data_availability,
            "C": codesign_compatibility,
            "R": revenue_potential,
            "O": obsolescence_risk,
            "N": nre_risk,
        },
        weights=weights.srs,
    )


def data_availability_factor(spec, versions_in_corpus: int) -> Finding:
    """D — disponibilidade de dados e benchmarks. Computavel a partir do registro."""
    open_license = (spec.license or "").lower() in {"apache-2.0", "mit", "bsd-3-clause"}
    checks = {
        "licenca permissiva": open_license,
        "duas ou mais versoes no corpus": versions_in_corpus >= 2,
        "contagem de parametros publicada": bool(spec.published_params),
        "proveniencia verificada": spec.provenance.verified,
    }
    val = sum(checks.values()) / len(checks)
    return Finding(
        "D.data_availability",
        val,
        Status.OBSERVATION if spec.provenance.verified else Status.ASSUMPTION,
        unit="[0,1]",
        assumptions=() if spec.provenance.verified else ("A-009",),
        gaps=() if spec.provenance.verified else ("G-008",),
        note="; ".join(f"{k}={'sim' if v else 'nao'}" for k, v in checks.items()),
    )


def codesign_compatibility_factor(candidates: Sequence[HardeningCandidate]) -> Finding:
    """C — compatibilidade com codesign: regularidade e previsibilidade ponderadas por custo."""
    tot = sum(c.cost_share for c in candidates) or 1.0
    val = sum(
        c.cost_share
        * 0.5
        * (float(c.scorecard.factors["R"].value) + float(c.scorecard.factors["M"].value))
        for c in candidates
    ) / tot
    return Finding(
        "C.codesign",
        val,
        Status.MODEL,
        unit="[0,1]",
        gaps=("G-001",),
        note="media de regularidade e previsibilidade de memoria ponderada por custo",
    )


def low_precision_factor(candidates: Sequence[HardeningCandidate]) -> Finding:
    """Q — robustez a baixa precisao, ponderada pelo custo que cada papel representa."""
    tot = sum(c.cost_share for c in candidates) or 1.0
    val = sum(c.cost_share * float(c.scorecard.factors["Q"].value) for c in candidates) / tot
    return Finding(
        "Q.low_precision",
        val,
        Status.ASSUMPTION,
        unit="[0,1]",
        assumptions=("A-004",),
        gaps=("G-002",),
        note="media dos priors ponderada por custo; nao medido",
    )


# --------------------------------------------------------------------------------------
# Analise de sensibilidade — falsificador F3 / alegacao C-006
# --------------------------------------------------------------------------------------


@dataclass
class SensitivityResult:
    """Resultado da perturbacao dos pesos. Decide se o score pode sustentar recomendacao."""

    perturbation: float
    samples: int
    top1_stability: float
    top3_stability: float
    band_stability: float | None
    winners: dict[str, int]
    threshold: float
    dominant_factor: str | None = None
    score_spread: float = 0.0
    noise_band: float = 0.0
    inert_weight: float = 0.0
    varying_factors: tuple[str, ...] = ()
    margin: float = 0.0
    contenders: tuple[str, ...] = ()
    contender_inert_weight: float = 0.0
    #: Findings dos fatores que entraram no ranking. Necessarios para que o status da
    #: estabilidade herde o elo mais fraco em vez de ser afirmado (ADR-0002, retratacao R-002).
    factor_findings: tuple[Finding, ...] = ()

    @property
    def decidable(self) -> bool:
        return self.top1_stability >= self.threshold

    @property
    def discriminates(self) -> bool:
        """O lider vence o primeiro concorrente **distinto** por mais que o ruido dos pesos?

        Distincao que `top1_stability` sozinha nao faz. Um ranking pode ser instavel porque os
        candidatos sao genuinamente equivalentes — `gate_proj` e `up_proj` tem exatamente os
        mesmos fatores, e ordena-los e sem sentido — ou porque o score nao mede o que deveria.
        Empates exatos sao agrupados antes da comparacao justamente para nao confundir os dois.
        """
        return self.margin > self.noise_band

    @property
    def diagnosis(self) -> str:
        if self.decidable and self.discriminates:
            return "score decidivel e discriminante"
        if self.decidable:
            return (
                f"top-1 estavel, mas a margem sobre o concorrente ({self.margin:.4f}) nao supera "
                f"o ruido dos pesos ({self.noise_band:.4f}): a ordem pode ser artefato"
            )
        if not self.discriminates:
            return (
                f"score NAO discrimina: entre os {len(self.contenders)} candidatos que disputam "
                f"a primeira posicao, {self.contender_inert_weight:.0%} do peso esta em fatores "
                f"identicos; a margem ({self.margin:.4f}) e menor que o ruido ({self.noise_band:.4f})"
            )
        return "candidatos proximos: ranking instavel apesar de a margem superar o ruido"

    def finding(self) -> Finding:
        return derive(
            "readiness.rank_stability",
            self.top1_stability,
            self.factor_findings
            or [Finding("readiness.no_candidates", 0.0, Status.OPEN_GAP, gaps=("G-011",))],
            ceiling=Status.COMPUTATIONAL_EVIDENCE,
            unit="fracao das amostras com mesmo top-1",
            note=(
                f"perturbacao +-{self.perturbation:.0%}, {self.samples} amostras; "
                f"{'DECIDIVEL' if self.decidable else 'NAO DECIDIVEL — F3 disparado'}; "
                f"{self.diagnosis}"
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "perturbation": self.perturbation,
            "samples": self.samples,
            "top1_stability": round(self.top1_stability, 4),
            "top3_stability": round(self.top3_stability, 4),
            "band_stability": round(self.band_stability, 4) if self.band_stability is not None else None,
            "threshold": self.threshold,
            "decidable": self.decidable,
            "discriminates": self.discriminates,
            "score_spread": round(self.score_spread, 5),
            "noise_band": round(self.noise_band, 5),
            "margin": round(self.margin, 5) if self.margin != float("inf") else None,
            "inert_weight": round(self.inert_weight, 3),
            "contenders": list(self.contenders),
            "contender_inert_weight": round(self.contender_inert_weight, 3),
            "varying_factors": list(self.varying_factors),
            "diagnosis": self.diagnosis,
            "winners": self.winners,
            "dominant_factor": self.dominant_factor,
        }


def sensitivity(
    candidates: Sequence[HardeningCandidate],
    weights: Weights,
    srs: ScoreCard | None = None,
) -> SensitivityResult:
    """Perturba os pesos e mede se o ranking e a banda de decisao sobrevivem.

    Implementa o falsificador F3 da PROBLEM_CHARTER. Um resultado abaixo do limite nao e um
    aviso: e instrucao de retratar a recomendacao derivada do score.
    """
    cfg = weights.sensitivity
    pert = float(cfg.get("perturbation", 0.20))
    n = int(cfg.get("samples", 2000))
    thr = float(cfg.get("rank_stability_threshold", 0.95))
    rng = np.random.default_rng(int(cfg.get("seed", 0)))

    if not candidates:
        return SensitivityResult(pert, n, 0.0, 0.0, None, {}, thr)

    keys = list(weights.lhs)
    base_w = np.array([weights.lhs[k] for k in keys])
    values = np.array(
        [[float(c.scorecard.factors[k].value) for k in keys] for c in candidates]
    )  # (n_cand, n_factor)

    factors = rng.uniform(1 - pert, 1 + pert, size=(n, len(keys)))
    sampled = values @ (base_w * factors).T          # (n_cand, n_samples)
    order = np.argsort(-sampled, axis=0)

    base_scores = values @ base_w
    base_order = np.argsort(-base_scores)
    base_top1, base_top3 = int(base_order[0]), set(base_order[:3].tolist())

    top1 = order[0, :]
    top1_stability = float(np.mean(top1 == base_top1))
    top3_stability = float(
        np.mean([set(order[:3, s].tolist()) == base_top3 for s in range(n)])
    )
    winners: dict[str, int] = {}
    for idx in top1:
        r = candidates[int(idx)].role
        winners[r] = winners.get(r, 0) + 1

    band_stability = None
    if srs is not None:
        s_keys = list(weights.srs)
        s_w = np.array([weights.srs[k] for k in s_keys])
        s_v = np.array([float(srs.factors[k].value) for k in s_keys])
        s_fac = rng.uniform(1 - pert, 1 + pert, size=(n, len(s_keys)))
        s_scores = (s_v * (s_w * s_fac)).sum(axis=1)
        base_band = weights.band_for(float(s_v @ s_w))
        band_stability = float(
            np.mean([weights.band_for(float(x)) == base_band for x in s_scores])
        )

    # fator que mais move o resultado: maior contribuicao absoluta no vencedor
    contrib = candidates[base_top1].scorecard.contributions
    dominant = max(contrib, key=lambda k: abs(contrib[k])) if contrib else None

    # Diagnostico de discriminacao: um fator constante entre os candidatos que disputam a
    # primeira posicao gasta peso sem separar nada.
    spread = float(base_scores.max() - base_scores.min())
    noise = float(np.std(sampled - base_scores[:, None]))
    stds = values.std(axis=0)
    varying = tuple(k for k, s in zip(keys, stds) if s > 1e-9)
    total_w = sum(abs(v) for v in weights.lhs.values()) or 1.0
    inert = sum(abs(weights.lhs[k]) for k, s in zip(keys, stds) if s <= 1e-9)

    # Margem sobre o primeiro concorrente **distinto**: empates exatos sao equivalencia
    # genuina (mesmo vetor de fatores), nao indecisao do score.
    lead = float(base_scores.max())
    distinct = np.unique(np.round(base_scores, 12))[::-1]
    margin = float(distinct[0] - distinct[1]) if distinct.size > 1 else float("inf")

    # Candidatos dentro do ruido do lider: os que efetivamente disputam.
    idx = np.where(base_scores >= lead - noise)[0]
    contenders = tuple(candidates[int(i)].role for i in idx)
    if idx.size > 1:
        cstds = values[idx].std(axis=0)
        c_inert = sum(abs(weights.lhs[k]) for k, s in zip(keys, cstds) if s <= 1e-9) / total_w
    else:
        c_inert = 0.0

    return SensitivityResult(
        perturbation=pert,
        samples=n,
        top1_stability=top1_stability,
        top3_stability=top3_stability,
        band_stability=band_stability,
        winners=dict(sorted(winners.items(), key=lambda kv: -kv[1])),
        threshold=thr,
        dominant_factor=dominant,
        score_spread=spread,
        noise_band=noise,
        inert_weight=inert / total_w,
        varying_factors=varying,
        margin=margin,
        contenders=contenders,
        contender_inert_weight=c_inert,
        factor_findings=tuple(f for c in candidates for f in c.scorecard.factors.values()),
    )


__all__ = [
    "Weights",
    "ScoreCard",
    "HardeningCandidate",
    "SensitivityResult",
    "build_candidates",
    "build_srs",
    "sensitivity",
    "data_availability_factor",
    "codesign_compatibility_factor",
    "low_precision_factor",
]
