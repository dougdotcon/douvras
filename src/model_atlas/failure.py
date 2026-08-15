"""Failure Atlas: a distribuicao de falhas por capacidade, nao o escore agregado.

O Documento 2 diz que o diferencial nao e o leaderboard, e este arquivo e o motivo. Saber que
um agente acerta 61 % nao muda nenhuma decisao. Saber que 42 % das falhas de recuperacao sao
`timeout` e 31 % sao `malformed_json` diz qual dataset construir na semana seguinte.

Um detalhe de leitura importa: o atlas conta **rotulos**, nao tarefas. Uma trajetoria pode
falhar por dois motivos ao mesmo tempo — chamar a ferramenta errada *e* inventar um numero — e
espremer isso num rotulo unico jogaria fora metade da informacao acionavel. Por isso a soma
das taxas pode passar de 100 %, e a coluna de tarefas reprovadas existe separada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .runner import RunResult
from .tasks import Capability, FailureMode


@dataclass
class FailureAtlas:
    """Falhas por capacidade e por modo, com a origem da execucao sempre a vista."""

    source: str
    synthetic: bool
    per_capability: dict[Capability, dict[FailureMode, int]] = field(default_factory=dict)
    attempts: dict[Capability, int] = field(default_factory=dict)
    failed_tasks: dict[Capability, int] = field(default_factory=dict)

    @classmethod
    def from_run(cls, run: RunResult) -> "FailureAtlas":
        atlas = cls(source=run.respondent_id, synthetic=run.synthetic)
        for g in run.grades:
            atlas.attempts[g.capability] = atlas.attempts.get(g.capability, 0) + 1
            if not g.passed:
                atlas.failed_tasks[g.capability] = atlas.failed_tasks.get(g.capability, 0) + 1
            cel = atlas.per_capability.setdefault(g.capability, {})
            for f in g.failures:
                cel[f] = cel.get(f, 0) + 1
        return atlas

    @classmethod
    def merged(cls, runs: list[RunResult], source: str) -> "FailureAtlas":
        """Une varias execucoes — usado para mostrar que a taxonomia inteira esta viva."""
        atlas = cls(source=source, synthetic=all(r.synthetic for r in runs))
        for r in runs:
            parcial = cls.from_run(r)
            for cap, n in parcial.attempts.items():
                atlas.attempts[cap] = atlas.attempts.get(cap, 0) + n
            for cap, n in parcial.failed_tasks.items():
                atlas.failed_tasks[cap] = atlas.failed_tasks.get(cap, 0) + n
            for cap, cel in parcial.per_capability.items():
                alvo = atlas.per_capability.setdefault(cap, {})
                for modo, n in cel.items():
                    alvo[modo] = alvo.get(modo, 0) + n
        return atlas

    # -- consultas ------------------------------------------------------------------
    def rate(self, cap: Capability, mode: FailureMode) -> float:
        n = self.attempts.get(cap, 0)
        return self.per_capability.get(cap, {}).get(mode, 0) / n if n else 0.0

    def observed_modes(self) -> set[FailureMode]:
        return {m for cel in self.per_capability.values() for m in cel}

    def dominant(self) -> list[tuple[Capability, FailureMode, float]]:
        """As celulas mais quentes, do pior para o melhor. E a lista de alvos de dataset."""
        out = [
            (cap, modo, self.rate(cap, modo))
            for cap, cel in self.per_capability.items()
            for modo in cel
        ]
        return sorted(out, key=lambda t: -t[2])

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "synthetic": self.synthetic,
            "per_capability": {
                str(cap): {
                    str(m): {"count": n, "rate": round(self.rate(cap, m), 4)}
                    for m, n in sorted(cel.items(), key=lambda kv: -kv[1])
                }
                for cap, cel in sorted(self.per_capability.items(), key=lambda kv: str(kv[0]))
            },
            "attempts": {str(k): v for k, v in sorted(self.attempts.items(), key=lambda kv: str(kv[0]))},
        }

    def render_tree(self) -> str:
        """A arvore do Documento 2, secao 10."""
        linhas = [f"FONTE  {self.source}" + ("  (sintetica)" if self.synthetic else ""), "│"]
        caps = sorted(self.per_capability, key=str)
        for i, cap in enumerate(caps):
            ult_cap = i == len(caps) - 1
            linhas.append(f"{'└──' if ult_cap else '├──'} {str(cap).upper()}")
            cel = sorted(self.per_capability[cap].items(), key=lambda kv: -kv[1])
            for j, (modo, _n) in enumerate(cel):
                ult = j == len(cel) - 1
                prefixo = "    " if ult_cap else "│   "
                nome = str(modo).replace("FAIL_", "").lower()
                linhas.append(
                    f"{prefixo}{'└──' if ult else '├──'} {nome:<18} {self.rate(cap, modo):>6.1%}"
                )
            if not ult_cap:
                linhas.append("│")
        if self.synthetic:
            linhas += [
                "",
                "Estas taxas descrevem as sondas de calibracao, nao um modelo. Elas mostram que",
                "a taxonomia esta viva — cada celula preenchida e um modo que o grader consegue",
                "detectar quando acontece.",
            ]
        return "\n".join(linhas)


__all__ = ["FailureAtlas"]
