"""Nucleo epistemico do DOUVRAS — compartilhado por todos os atlas.

Implementa o contrato do Metodo DOUVRAS 3.1 como codigo executavel: nenhum valor
numerico trafega entre motores sem status, e nenhuma conclusao pode ser mais forte
que a mais fraca de suas dependencias (ADR-0002).

Este modulo nasceu como `silicon_atlas/status.py` e foi promovido a `douvras_core`
no ciclo C-002 (ADR-0005). A promocao e o teste do proprio contrato: se a escala de
status so servisse para hardware, ela seria vocabulario de dominio, nao epistemologia.
O Model Atlas usa exatamente as mesmas classes, sem uma linha de adaptacao — e um
`Finding` de capacidade medida se combina com um `Finding` de custo analitico pela
mesma regra do elo mais fraco.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field, replace
from enum import IntEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class Status(IntEnum):
    """Escala de status do Metodo DOUVRAS, ordenada por forca epistemica.

    A ordem e total e o valor inteiro *e* a forca: ``min()`` sobre um conjunto de
    status devolve o elo mais fraco, que e exatamente a regra de propagacao.
    """

    RETRACTED = 0
    OPEN_GAP = 10
    ANALOGY = 20
    ASSUMPTION = 30
    CONJECTURE = 35
    DEFINITION = 40
    HYPOTHESIS = 50
    MODEL = 55
    COMPUTATIONAL_EVIDENCE = 60
    PARTIAL_RESULT = 65
    CONDITIONAL_RESULT = 70
    OBSERVATION = 75
    EXPERIMENTAL_EVIDENCE = 85
    ENGINEERING_DECISION = 90
    EXTERNALLY_VERIFIED = 100

    @property
    def label(self) -> str:
        return self.name

    @property
    def rank(self) -> int:
        """Posicao na ordem de forca epistemica, de 0 (mais fraco) a N-1 (mais forte).

        A `STATUS_POLICY` declara que `Status.rank` implementa a ordem; sem esta propriedade a
        politica descrevia um mecanismo inexistente.
        """
        return sorted(Status).index(self)

    @property
    def supports_tapeout(self) -> bool:
        """Status forte o bastante para sustentar uma decisao irreversivel de fabricacao."""
        return self >= Status.EXPERIMENTAL_EVIDENCE


#: Status abaixo do qual um resultado nao pode ser apresentado como conclusao.
DECISION_FLOOR = Status.CONDITIONAL_RESULT


class StatusViolation(RuntimeError):
    """Tentativa de promover uma afirmacao acima do que suas dependencias permitem."""


# --------------------------------------------------------------------------------------
# Vocabulario proibido (Metodo 3.2)
# --------------------------------------------------------------------------------------

FORBIDDEN_TERMS: tuple[str, ...] = (
    "resolvido",
    "provado",
    "100% completo",
    "revolucionario",
    "revolucionário",
    "universal",
    "garantido",
)

#: "100x", "10 vezes mais rapido" etc. sem qualificadores.
_MULTIPLIER_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:x|vezes)\s+(?:mais\s+)?"
    r"(?:rapido|rápido|barato|eficiente|melhor)\b",
    re.IGNORECASE,
)

#: Qualificadores exigidos pelo CLAIM_LEDGER C-004 para qualquer alegacao de ganho.
REQUIRED_MULTIPLIER_QUALIFIERS: tuple[str, ...] = (
    "modelo",
    "baseline",
    "precis",  # precisao / precision
    "lote|batch",
    "context",
    "prefill|decode",
)


@dataclass(frozen=True)
class LintFinding:
    line_no: int
    term: str
    line: str
    reason: str


#: Marcador explicito de isencao. Existe porque a propria politica precisa **citar** os termos
#: que proibe, e um lint que nao consegue descrever a si mesmo e inutilizavel.
LINT_ALLOW = "<!-- lint:allow -->"

#: Fronteira de palavra por termo. Sem isto, "aprovado" e "comprovado" disparavam por conter
#: "provado", e o lint acusava o DECISION_LOG por dizer "sem candidato aprovado".
_TERM_RES = {
    t: re.compile(rf"(?<![0-9a-zà-ú]){re.escape(t)}(?![0-9a-zà-ú])", re.IGNORECASE)
    for t in FORBIDDEN_TERMS
}


def lint_text(text: str) -> list[LintFinding]:
    """Varre texto em busca do vocabulario proibido pelo Metodo 3.2.

    Um multiplicador ("100x mais rapido") so passa se a mesma linha, ou a adjacente,
    trouxer os qualificadores exigidos pelo C-004. Linhas marcadas com ``<!-- lint:allow -->``
    sao ignoradas.
    """
    out: list[LintFinding] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if LINT_ALLOW in line:
            continue
        for term, rx in _TERM_RES.items():
            if rx.search(line):
                out.append(
                    LintFinding(i + 1, term, line.strip(), "termo sem objeto/metrica/baseline")
                )
        m = _MULTIPLIER_RE.search(line)
        if m:
            window = " ".join(lines[max(0, i - 2) : i + 3]).lower()
            missing = [
                q for q in REQUIRED_MULTIPLIER_QUALIFIERS if not re.search(q, window)
            ]
            if missing:
                out.append(
                    LintFinding(
                        i + 1,
                        m.group(0),
                        line.strip(),
                        "ganho sem qualificadores: " + ", ".join(missing),
                    )
                )
    return out


# --------------------------------------------------------------------------------------
# Finding: valor com proveniencia epistemica
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """Um valor acompanhado do que autoriza acreditar nele.

    ``value`` pode ser numero, string ou estrutura. ``status`` e obrigatorio.
    ``assumptions`` lista ids do ASSUMPTIONS.md; ``gaps`` lista ids do GAP_REGISTER.md.
    """

    name: str
    value: Any
    status: Status
    unit: str = ""
    assumptions: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    note: str = ""
    parents: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, Status):
            raise StatusViolation(f"{self.name}: status obrigatorio e tipado")
        if self.gaps and self.status > Status.CONDITIONAL_RESULT:
            raise StatusViolation(
                f"{self.name}: possui lacunas abertas {list(self.gaps)} e nao pode "
                f"receber status {self.status.name}"
            )

    # -- aritmetica que propaga status ---------------------------------------------
    def derive(
        self,
        name: str,
        value: Any,
        *,
        ceiling: Status = Status.COMPUTATIONAL_EVIDENCE,
        unit: str = "",
        others: Sequence["Finding"] = (),
        note: str = "",
        extra_gaps: Sequence[str] = (),
    ) -> "Finding":
        """Deriva um novo Finding cujo status e o elo mais fraco, limitado por ``ceiling``."""
        return derive(
            name,
            value,
            [self, *others],
            ceiling=ceiling,
            unit=unit,
            note=note,
            extra_gaps=extra_gaps,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "status": self.status.name,
            "assumptions": list(self.assumptions),
            "gaps": list(self.gaps),
            "parents": list(self.parents),
            "note": self.note,
        }

    def __str__(self) -> str:  # pragma: no cover - conveniencia de depuracao
        v = self.value
        v = f"{v:,.4g}" if isinstance(v, float) else str(v)
        u = f" {self.unit}" if self.unit else ""
        return f"{self.name} = {v}{u} [{self.status.name}]"


def derive(
    name: str,
    value: Any,
    parents: Iterable[Finding],
    *,
    ceiling: Status = Status.COMPUTATIONAL_EVIDENCE,
    unit: str = "",
    note: str = "",
    extra_gaps: Sequence[str] = (),
) -> Finding:
    """Combina Findings: status = min(status dos pais, ceiling); premissas/lacunas somam.

    ``ceiling`` e o teto que o *metodo de calculo* permite. Um roofline analitico nunca
    produz EXPERIMENTAL_EVIDENCE, por melhores que sejam suas entradas.
    """
    ps = list(parents)
    weakest = min((p.status for p in ps), default=ceiling)
    status = Status(min(int(weakest), int(ceiling)))
    gaps = tuple(sorted({g for p in ps for g in p.gaps} | set(extra_gaps)))
    if gaps:
        status = Status(min(int(status), int(Status.CONDITIONAL_RESULT)))
    return Finding(
        name=name,
        value=value,
        status=status,
        unit=unit,
        assumptions=tuple(sorted({a for p in ps for a in p.assumptions})),
        gaps=gaps,
        note=note,
        parents=tuple(p.name for p in ps),
    )


def assumed(name: str, value: Any, *, unit: str = "", assumption_id: str, note: str = "") -> Finding:
    """Atalho para uma entrada declaradamente nao demonstrada."""
    return Finding(
        name=name,
        value=value,
        status=Status.ASSUMPTION,
        unit=unit,
        assumptions=(assumption_id,),
        note=note,
    )


def measured(name: str, value: Any, *, unit: str = "", note: str = "") -> Finding:
    """Atalho para medicao com protocolo documentado."""
    return Finding(name=name, value=value, status=Status.OBSERVATION, unit=unit, note=note)


def modeled(name: str, value: Any, *, unit: str = "", note: str = "", gaps: Sequence[str] = ()) -> Finding:
    """Atalho para saida de representacao formal (a IR, por exemplo)."""
    return Finding(
        name=name,
        value=value,
        status=Status.MODEL,
        unit=unit,
        note=note,
        gaps=tuple(gaps),
    )


# --------------------------------------------------------------------------------------
# Claim ledger
# --------------------------------------------------------------------------------------


@dataclass
class Claim:
    id: str
    statement: str
    status: str
    falsifiers: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    owner: str = "unassigned"
    last_reviewed: str = ""
    note: str = ""

    @property
    def status_enum(self) -> Status | None:
        try:
            return Status[self.status]
        except KeyError:
            return None  # ex.: CONDITIONAL_HYPOTHESIS, status composto do documento

    def check_falsified(self, observed: Mapping[str, bool]) -> list[str]:
        """Devolve os falsificadores que a evidencia observada dispara."""
        return [f for f in self.falsifiers if observed.get(f, False)]


class ClaimLedger:
    """Leitura e escrita do 00_GOVERNANCE/CLAIM_LEDGER.yaml."""

    def __init__(self, claims: Sequence[Claim], path: Path | None = None):
        self.claims = list(claims)
        self.path = path

    @classmethod
    def load(cls, path: Path) -> "ClaimLedger":
        import yaml  # dependencia declarada em pyproject

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        claims = [
            Claim(
                id=str(c["id"]),
                statement=str(c.get("statement", "")).strip(),
                status=str(c.get("status", "CONJECTURE")),
                falsifiers=list(c.get("falsifiers") or []),
                assumptions=list(c.get("assumptions") or []),
                evidence=[str(e) for e in (c.get("evidence") or [])],
                owner=str(c.get("owner", "unassigned")),
                last_reviewed=str(c.get("last_reviewed", "")),
                note=str(c.get("note", "") or ""),
            )
            for c in raw
        ]
        return cls(claims, path)

    def __getitem__(self, claim_id: str) -> Claim:
        for c in self.claims:
            if c.id == claim_id:
                return c
        raise KeyError(claim_id)

    def record_run(
        self, results: Mapping[str, Any], run_id: str, reviewed_on: str | None = None
    ) -> None:
        """Anexa evidencia gerada por execucao, sem promover status automaticamente.

        Idempotente por construcao: reexecutar o ciclo com o mesmo `run_id` nao duplica tag nem
        motivo. Antes disso, `CLAIM_LEDGER.yaml` acumulou seis tags e a mesma frase repetida
        quatro vezes numa nota de 616 caracteres.

        ``reviewed_on`` vem do `run_id`, nao de `date.today()`: um artefato de saida que muda
        conforme o dia da execucao quebra o contrato de reprodutibilidade.
        """
        stamp = reviewed_on or (run_id[:8] and f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}")
        for cid, payload in results.items():
            try:
                claim = self[cid]
            except KeyError:
                continue
            tag = f"RUN:{run_id}"
            if tag not in claim.evidence:
                claim.evidence.append(tag)
            claim.last_reviewed = stamp
            if payload.get("falsified"):
                claim.status = "RETRACTED"
                reason = str(payload.get("reason", "falsificador disparado"))
                if reason not in claim.note:
                    claim.note = (claim.note + " | " if claim.note else "") + reason

    def to_yaml(self) -> str:
        import yaml

        docs = [
            {
                "id": c.id,
                "statement": c.statement,
                "status": c.status,
                "assumptions": c.assumptions,
                "evidence": c.evidence,
                "falsifiers": c.falsifiers,
                "owner": c.owner,
                "last_reviewed": c.last_reviewed,
                **({"note": c.note} if c.note else {}),
            }
            for c in self.claims
        ]
        return yaml.safe_dump(docs, sort_keys=False, allow_unicode=True, width=100)

    def save(self, path: Path | None = None) -> Path:
        target = path or self.path
        if target is None:
            raise ValueError("sem caminho para salvar o ledger")
        target.write_text(self.to_yaml(), encoding="utf-8")
        return target


# --------------------------------------------------------------------------------------
# Bundle de resultado auditavel
# --------------------------------------------------------------------------------------


@dataclass
class FindingSet:
    """Colecao nomeada de Findings com resumo epistemico agregado."""

    title: str
    items: list[Finding] = field(default_factory=list)

    def add(self, f: Finding) -> Finding:
        self.items.append(f)
        return f

    def extend(self, fs: Iterable[Finding]) -> None:
        self.items.extend(fs)

    @property
    def weakest(self) -> Status:
        """Status do elo mais fraco entre os resultados que carregam valor.

        Findings com ``value is None`` sao *declaracoes de ausencia* — o registro explicito de
        algo que nao foi medido. Eles pertencem ao relatorio (e aparecem em `declared_absences`),
        mas rebaixar a cadeia inteira por causa deles apagaria a diferenca entre "este resultado
        e fraco" e "declaramos honestamente o que falta medir".
        """
        vals = [f.status for f in self.items if f.value is not None]
        return Status(min(vals, default=int(Status.OPEN_GAP)))

    @property
    def declared_absences(self) -> list["Finding"]:
        return [f for f in self.items if f.value is None]

    def evidence_debt(self) -> float:
        """Fracao dos resultados cujo status e ASSUMPTION ou mais fraco (Metodo 6.3).

        E a divida de evidencia medida em vez de estimada. Se ela sobe de um ciclo para o outro,
        o sistema esta acumulando modelagem mais rapido que evidencia — o modo de falha mais
        provavel deste tipo de projeto, e o mais dificil de perceber de dentro.
        """
        vals = [f for f in self.items if f.value is not None]
        if not vals:
            return 1.0
        return sum(1 for f in vals if f.status <= Status.ASSUMPTION) / len(vals)

    def status_histogram(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.items:
            out[f.status.name] = out.get(f.status.name, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    @property
    def open_gaps(self) -> list[str]:
        return sorted({g for f in self.items for g in f.gaps})

    @property
    def assumptions(self) -> list[str]:
        return sorted({a for f in self.items for a in f.assumptions})

    def by_name(self, name: str) -> Finding:
        for f in self.items:
            if f.name == name:
                return f
        raise KeyError(name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "weakest_status": self.weakest.name,
            "open_gaps": self.open_gaps,
            "assumptions": self.assumptions,
            "declared_absences": [f.name for f in self.declared_absences],
            "evidence_debt": round(self.evidence_debt(), 4),
            "status_histogram": self.status_histogram(),
            "findings": [f.as_dict() for f in self.items],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=False, default=str)


__all__ = [
    "Status",
    "StatusViolation",
    "Finding",
    "FindingSet",
    "Claim",
    "ClaimLedger",
    "LintFinding",
    "derive",
    "assumed",
    "measured",
    "modeled",
    "lint_text",
    "DECISION_FLOOR",
    "FORBIDDEN_TERMS",
    "replace",
]
