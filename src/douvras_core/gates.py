"""Portoes D0 -> S6 do Metodo DOUVRAS, como vocabulario compartilhado.

Os *criterios* de cada portao sao especificos do atlas: o que conta como "cobertura
observacional" para nove `config.json` de modelo nao e o que conta para um corpus de
tarefas de avaliacao. O que **nao** e especifico e a regra que os governa:

- um portao verifica **conteudo**, nunca existencia de caminho — um portao satisfeito por
  a pasta existir nao e portao, e foi assim que `U2` passou um ciclo inteiro sendo uma
  identidade aritmetica sempre verdadeira;
- um portao bloqueado nao interrompe o ciclo: ele impede promocao de status;
- a evidencia que sustenta o veredicto e impressa junto com ele, sempre.

Este modulo carrega essa regra e a renderizacao. Cada atlas monta seus `Gate`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

#: Os sete portoes do Metodo, na ordem das fases.
GATE_TITLES: tuple[tuple[str, str], ...] = (
    ("D0", "identidade do problema"),
    ("O1", "cobertura observacional"),
    ("U2", "estrutura candidata"),
    ("V3", "sobrevivencia minima"),
    ("R4", "estrutura minima operavel"),
    ("A5", "prototipo verificavel"),
    ("S6", "operacao cumulativa"),
)

_TITLES = dict(GATE_TITLES)


@dataclass(frozen=True)
class Gate:
    """Veredicto de um portao, com a evidencia que o sustenta."""

    id: str
    passed: bool
    evidence: str
    title: str = ""

    def __post_init__(self) -> None:
        if not self.title:
            object.__setattr__(self, "title", _TITLES.get(self.id, ""))

    @property
    def label(self) -> str:
        return f"{self.id} — {self.title}" if self.title else self.id

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "passed": self.passed,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class GapCount:
    """Contagem de lacunas por estado.

    Existe porque `README` e CLI discordavam: o documento dizia "14 lacunas abertas" e o
    comando dizia 13. Ambos estavam certos sobre coisas diferentes — 14 registradas, 13
    abertas, 1 parcial. Um numero que depende de qual dos dois voce leu nao e um numero.
    """

    open: int
    partial: int

    @property
    def total(self) -> int:
        return self.open + self.partial

    def __str__(self) -> str:
        if self.partial:
            return f"{self.open} abertas, {self.partial} parcial(is) — {self.total} registradas"
        return f"{self.open} abertas"


@dataclass
class GateReport:
    gates: list[Gate]
    gaps: GapCount | None = None

    @property
    def blocked(self) -> list[str]:
        return [g.id for g in self.gates if not g.passed]

    @property
    def passed_count(self) -> int:
        return sum(1 for g in self.gates if g.passed)

    def render(self) -> str:
        width = max((len(g.label) for g in self.gates), default=10) + 2
        lines = [f"{'portao':<{width}}{'estado':<12}evidencia"]
        for g in self.gates:
            lines.append(
                f"{g.label:<{width}}{'PASSOU' if g.passed else 'BLOQUEADO':<12}{g.evidence}"
            )
        if self.gaps is not None:
            lines.append("")
            lines.append(f"lacunas no GAP_REGISTER: {self.gaps}")
        if self.blocked:
            lines.append(f"portoes bloqueados: {', '.join(self.blocked)}")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "gates": [g.as_dict() for g in self.gates],
            "passed": self.passed_count,
            "total": len(self.gates),
            "blocked": self.blocked,
        }
        if self.gaps is not None:
            out["gaps"] = {
                "open": self.gaps.open,
                "partial": self.gaps.partial,
                "total": self.gaps.total,
            }
        return out


# --------------------------------------------------------------------------------------
# Verificadores de conteudo
# --------------------------------------------------------------------------------------


def has_all(path: Path, needles: Sequence[str]) -> bool:
    """Todos os marcadores aparecem no arquivo. Arquivo ausente reprova, nunca aprova."""
    if not path.exists():
        return False
    txt = path.read_text(encoding="utf-8")
    return all(n in txt for n in needles)


def has_numbered_falsifiers(path: Path, prefix: str = "F") -> bool:
    """O documento declara ao menos um criterio de falha numerado (`F1`, `F2`, ...).

    O Metodo 6.1 exige criterio de falha **antes** do experimento. Um documento que fala
    genericamente em "criterios de falha" sem enumera-los nao cumpre isso.
    """
    if not path.exists():
        return False
    return bool(re.search(rf"\b{re.escape(prefix)}[1-9]\b", path.read_text(encoding="utf-8")))


def count_gaps(gap_register: Path) -> GapCount:
    """Conta lacunas por estado no GAP_REGISTER.

    A tabela marca `| OPEN |` para lacuna aberta e `PARCIAL` para lacuna cujos casos
    conhecidos foram fechados mas cuja classe permanece. As duas contagens sao reportadas
    separadamente: somar as duas esconde progresso, e ignorar a segunda esconde divida.
    """
    if not gap_register.exists():
        return GapCount(0, 0)
    txt = gap_register.read_text(encoding="utf-8")
    return GapCount(open=txt.count("| OPEN |"), partial=txt.count("PARCIAL"))


def verified_suite(path: Path) -> tuple[bool, dict]:
    """Le o registro de verificacao da suite gravado pelo script de ciclo.

    O portao A5 exige verificacao **registrada**, nao a existencia de um diretorio `tests/`.
    """
    if not path.exists():
        return False, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    ok = bool(data.get("tests_passed")) and data.get("failed", 1) == 0
    return ok, data


def external_reviews(directory: Path) -> list[Path]:
    """Revisoes externas registradas. Apenas arquivos `ER-*.md` contam.

    Um `README` no diretorio nao e revisao — e exatamente o erro que transformaria o portao
    V3 numa formalidade satisfeita por existir a pasta.
    """
    if not directory.exists():
        return []
    return sorted(directory.glob("ER-*.md"))


def summarize(gates: Iterable[Gate], gaps: GapCount | None = None) -> GateReport:
    return GateReport(list(gates), gaps)


__all__ = [
    "Gate",
    "GateReport",
    "GapCount",
    "GATE_TITLES",
    "has_all",
    "has_numbered_falsifiers",
    "count_gaps",
    "verified_suite",
    "external_reviews",
    "summarize",
]
