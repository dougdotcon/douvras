"""Capability fingerprint: o vetor de capacidades de um modelo — quando ha modelo.

O irmao do `fingerprint.py` do Silicon Atlas. La, o fingerprint e estrutural e sai de um
`config.json`; aqui ele e comportamental e so pode sair de **execucao**.

E ai mora a unica decisao importante deste modulo:

> execucao sintetica nao produz capacidade medida.

Uma sonda de calibracao diz coisas verdadeiras sobre o grader e nada sobre um modelo. Se
`from_run` aceitasse um `RunResult` sintetico e devolvesse `tool_selection: 0.83`, o numero
atravessaria o assessment, entraria no CSS, viraria alvo de dataset e ninguem lembraria da
origem tres arquivos depois. Por isso a recusa e no tipo, na fronteira, uma vez — e o
resultado e ausencia declarada com `G-101`, nao um zero silencioso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from douvras_core.status import Finding, FindingSet, Status

from .runner import RunResult
from .tasks import Capability

#: Lacuna que trava qualquer afirmacao sobre modelo enquanto nao houver execucao real.
GAP_NO_EXECUTION = "G-101"


@dataclass
class CapabilityFingerprint:
    """Vetor de capacidades, cada uma com seu proprio status epistemico."""

    model_id: str
    measured: bool
    scores: dict[Capability, Finding] = field(default_factory=dict)
    source: str = ""

    @classmethod
    def from_run(cls, model_id: str, run: RunResult) -> "CapabilityFingerprint":
        """Constroi o fingerprint a partir de uma execucao.

        Execucao sintetica devolve ausencias declaradas — uma por capacidade, para que o
        relatorio mostre *quais* capacidades nao foram medidas em vez de omitir a secao.
        """
        fp = cls(model_id=model_id, measured=not run.synthetic, source=run.respondent_id)
        por_cap = run.score_by_capability()
        for cap in Capability:
            if cap not in por_cap:
                continue
            if run.synthetic:
                fp.scores[cap] = Finding(
                    f"capacidade.{cap}",
                    None,
                    Status.OPEN_GAP,
                    gaps=(GAP_NO_EXECUTION,),
                    note=(
                        f"execucao sintetica ({run.respondent_id}) mede o instrumento, "
                        f"nao o modelo"
                    ),
                )
            else:
                fp.scores[cap] = Finding(
                    f"capacidade.{cap}",
                    round(por_cap[cap], 4),
                    Status.OBSERVATION,
                    note=f"medido em {run.respondent_id} sobre o corpus BR-Agent-Bench",
                )
        return fp

    @classmethod
    def unmeasured(cls, model_id: str, capabilities: list[Capability]) -> "CapabilityFingerprint":
        """Fingerprint de um modelo que nunca foi executado."""
        fp = cls(model_id=model_id, measured=False, source="nenhuma execucao")
        for cap in capabilities:
            fp.scores[cap] = Finding(
                f"capacidade.{cap}",
                None,
                Status.OPEN_GAP,
                gaps=(GAP_NO_EXECUTION,),
                note="nenhum peso local; ver ADR-0006 e G-101",
            )
        return fp

    # -- consultas ------------------------------------------------------------------
    def vector(self) -> dict[str, float | None]:
        return {str(c): f.value for c, f in sorted(self.scores.items(), key=lambda kv: str(kv[0]))}

    @property
    def weakest(self) -> tuple[Capability, float] | None:
        """A capacidade com pior escore — o alvo natural de dataset. `None` sem medicao."""
        medidos = [(c, f.value) for c, f in self.scores.items() if f.value is not None]
        return min(medidos, key=lambda kv: kv[1]) if medidos else None

    def findings(self) -> FindingSet:
        fs = FindingSet(f"capacidades — {self.model_id}")
        fs.extend(self.scores[c] for c in sorted(self.scores, key=str))
        return fs

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "measured": self.measured,
            "source": self.source,
            "capabilities": self.vector(),
            "weakest": (str(self.weakest[0]) if self.weakest else None),
        }

    def render(self) -> str:
        linhas = ["| Capacidade | Escore | Status |", "|---|---:|---|"]
        for c, f in sorted(self.scores.items(), key=lambda kv: str(kv[0])):
            valor = "—" if f.value is None else f"{f.value:.1%}"
            linhas.append(f"| `{c}` | {valor} | `{f.status.name}` |")
        if not self.measured:
            linhas += [
                "",
                "Nenhuma capacidade foi medida: o corpus nao tem pesos locais e nenhuma "
                "execucao real ocorreu. Os tracos nao sao zeros — sao ausencias declaradas.",
            ]
        return "\n".join(linhas)


__all__ = ["CapabilityFingerprint", "GAP_NO_EXECUTION"]
