"""CSS — Capability Specialization Score.

Responde: *esta capacidade e boa candidata a especializacao por dados?* E o irmao declarado do
`Layer Hardening Score` do Silicon Atlas, e herda dele a licao mais cara do ciclo C-001.

O LHS parecia o componente mais sofisticado do sistema e nao discriminava: entre candidatos do
mesmo modelo, 70 % do peso estava em fatores identicos, e o lider vencia por menos que o ruido
dos proprios pesos (`CE-001`). A alegacao foi retratada em vez de o instrumento ser reponderado
ate concordar — reponderar ate o ranking estabilizar seria ajustar o instrumento ao resultado.

O CSS nasce com o diagnostico de discriminacao **embutido**, nao anexado depois: toda pontuacao
sai acompanhada da margem do lider e do ruido dos pesos, e `discrimina` e um campo do resultado.
Um CSS que nao separa capacidades e um CSS que nao deve escolher alvo de dataset, e o tipo diz
isso antes de alguem perguntar.

Sem capacidade medida, nao ha CSS: `score()` devolve ausencia declarada. Ele nunca inventa o
deficit que existe para medir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from douvras_core.paths import project_root
from douvras_core.status import Finding, Status, derive

from .capability import CapabilityFingerprint, GAP_NO_EXECUTION
from .tasks import Capability

CONFIG_DIR = project_root("model-atlas") / "config"


@dataclass(frozen=True)
class Weights:
    """Pesos dos fatores do CSS. Versionados em arquivo — afrouxar aparece no diff."""

    factors: Mapping[str, float]
    seed: int
    version: str
    perturbation: float = 0.20

    @classmethod
    def load(cls, path: Path | None = None) -> "Weights":
        doc = json.loads(
            (path or CONFIG_DIR / "css_weights.v1.json").read_text(encoding="utf-8")
        )
        return cls(
            factors=dict(doc["factors"]),
            seed=int(doc["seed"]),
            version=str(doc.get("version", "1.0")),
            perturbation=float(doc.get("perturbation", 0.20)),
        )

    def vector(self, keys: Sequence[str]) -> np.ndarray:
        return np.array([float(self.factors[k]) for k in keys], dtype=float)


@dataclass(frozen=True)
class CapabilityCandidate:
    """Uma capacidade como candidata a especializacao, com seus fatores em [0, 1]."""

    capability: Capability
    deficit: float          # D — quanto falta para o teto; so existe com medicao
    tractability: float     # T — quao ensinavel por dados (prior versionado)
    value: float            # V — peso da capacidade no uso real
    dataset_cost: float     # C — custo de construir o dataset, ja invertido (1 = barato)
    stability: float        # S — a capacidade se comporta parecido entre modelos

    FACTOR_KEYS = ("D", "T", "V", "C", "S")

    def factors(self) -> np.ndarray:
        return np.array(
            [self.deficit, self.tractability, self.value, self.dataset_cost, self.stability],
            dtype=float,
        )


@dataclass
class CSSResult:
    """Pontuacao com o diagnostico de discriminacao junto, nunca separado."""

    ranking: list[tuple[Capability, float]] = field(default_factory=list)
    top1_stability: float = 0.0
    leader_margin: float = 0.0
    weight_noise: float = 0.0
    samples: int = 0

    @property
    def leader(self) -> Capability | None:
        return self.ranking[0][0] if self.ranking else None

    @property
    def discriminates(self) -> bool:
        """O lider vence por mais que o ruido dos proprios pesos?

        A pergunta que o `CE-001` ensinou a fazer. Ranking perfeitamente estavel e margem menor
        que o ruido convivem sem contradicao — e foi assim que o `mistral-7b` liderou 100 % das
        amostras sem que isso significasse nada.
        """
        return self.samples > 0 and self.leader_margin > self.weight_noise

    def as_dict(self) -> dict[str, Any]:
        return {
            "ranking": [(str(c), round(v, 4)) for c, v in self.ranking],
            "leader": str(self.leader) if self.leader else None,
            "top1_stability": round(self.top1_stability, 4),
            "leader_margin": round(self.leader_margin, 6),
            "weight_noise": round(self.weight_noise, 6),
            "discriminates": self.discriminates,
            "samples": self.samples,
        }


def build_candidates(
    fp: CapabilityFingerprint, priors: Mapping[str, Mapping[str, float]]
) -> list[CapabilityCandidate]:
    """Monta candidatos a partir de um fingerprint **medido**.

    Devolve lista vazia se nada foi medido — e a forma de o CSS nao existir em vez de existir
    com deficit inventado.
    """
    out: list[CapabilityCandidate] = []
    for cap, finding in fp.scores.items():
        if finding.value is None:
            continue
        p = priors.get(str(cap), {})
        out.append(
            CapabilityCandidate(
                capability=cap,
                deficit=max(0.0, 1.0 - float(finding.value)),
                tractability=float(p.get("tractability", 0.5)),
                value=float(p.get("value", 0.5)),
                dataset_cost=float(p.get("dataset_cost", 0.5)),
                stability=float(p.get("stability", 0.5)),
            )
        )
    return out


def score(candidates: Sequence[CapabilityCandidate], w: Weights) -> CSSResult:
    """Pontua e mede a propria capacidade de discriminar, na mesma passada."""
    if not candidates:
        return CSSResult()
    keys = list(CapabilityCandidate.FACTOR_KEYS)
    base = w.vector(keys)
    base = base / base.sum()
    M = np.stack([c.factors() for c in candidates])  # (n_cand, n_fator)

    pontos = M @ base
    ordem = np.argsort(-pontos)
    ranking = [(candidates[i].capability, float(pontos[i])) for i in ordem]

    rng = np.random.default_rng(w.seed)
    n = 4000
    ruidos = rng.uniform(1.0 - w.perturbation, 1.0 + w.perturbation, size=(n, len(keys)))
    pesos = base * ruidos
    pesos = pesos / pesos.sum(axis=1, keepdims=True)
    amostras = pesos @ M.T                                  # (n, n_cand)
    top1 = np.argmax(amostras, axis=1)
    estabilidade = float((top1 == ordem[0]).mean())

    margem = (
        float(pontos[ordem[0]] - pontos[ordem[1]]) if len(candidates) > 1 else float(pontos[ordem[0]])
    )
    ruido = float(amostras[:, ordem[0]].std())

    return CSSResult(
        ranking=ranking,
        top1_stability=estabilidade,
        leader_margin=margem,
        weight_noise=ruido,
        samples=n,
    )


def css_finding(fp: CapabilityFingerprint, result: CSSResult) -> Finding:
    """O CSS como `Finding`, com o status que sua origem autoriza.

    Sem medicao: ausencia declarada com `G-101`. Com medicao sintetica: nunca chega aqui,
    porque `CapabilityFingerprint` ja recusou antes. Com medicao real: `CONDITIONAL_RESULT`,
    porque os priors de tratabilidade e custo continuam nao calibrados (`G-104`).
    """
    if not fp.measured or result.leader is None:
        return Finding(
            "css_alvo",
            None,
            Status.OPEN_GAP,
            gaps=(GAP_NO_EXECUTION,),
            note="sem capacidade medida nao existe deficit, e sem deficit nao existe CSS",
        )
    base = Finding(
        "css_lider_bruto",
        round(result.ranking[0][1], 4),
        Status.COMPUTATIONAL_EVIDENCE,
        note=f"{result.samples} amostras de perturbacao dos pesos",
    )
    return derive(
        "css_alvo",
        str(result.leader) if result.discriminates else None,
        [base],
        note=(
            f"margem {result.leader_margin:.5f} contra ruido {result.weight_noise:.5f}; "
            + ("discrimina" if result.discriminates else "NAO discrimina — alvo nao decidido")
        ),
        extra_gaps=("G-104",),
    )


def load_priors(path: Path | None = None) -> dict[str, dict[str, float]]:
    doc = json.loads(
        (path or CONFIG_DIR / "capability_priors.v1.json").read_text(encoding="utf-8")
    )
    return {k: dict(v) for k, v in doc["capabilities"].items()}


__all__ = [
    "Weights",
    "CapabilityCandidate",
    "CSSResult",
    "build_candidates",
    "score",
    "css_finding",
    "load_priors",
    "CONFIG_DIR",
]
