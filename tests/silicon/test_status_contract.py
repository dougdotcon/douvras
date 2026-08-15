"""O contrato epistemico como codigo executavel (ADR-0002).

Se estes testes passarem, a regra "nenhuma conclusao mais forte que sua dependencia mais fraca"
deixa de depender de disciplina humana.
"""

from __future__ import annotations

import pytest

from douvras_core.status import (
    Finding,
    FindingSet,
    Status,
    StatusViolation,
    assumed,
    derive,
    lint_text,
    measured,
)


def test_status_order_is_total_and_meaningful() -> None:
    assert Status.ASSUMPTION < Status.HYPOTHESIS < Status.COMPUTATIONAL_EVIDENCE
    assert Status.EXPERIMENTAL_EVIDENCE < Status.EXTERNALLY_VERIFIED
    assert Status.RETRACTED < Status.OPEN_GAP
    assert Status.EXPERIMENTAL_EVIDENCE.supports_tapeout
    assert not Status.HYPOTHESIS.supports_tapeout


def test_derive_takes_the_weakest_link() -> None:
    strong = measured("medido", 10.0)
    weak = assumed("chutado", 2.0, assumption_id="A-001")
    out = derive("produto", 20.0, [strong, weak], ceiling=Status.EXPERIMENTAL_EVIDENCE)
    assert out.status is Status.ASSUMPTION
    assert out.assumptions == ("A-001",)
    assert set(out.parents) == {"medido", "chutado"}


def test_ceiling_limits_even_perfect_inputs() -> None:
    """Um roofline analitico nao vira evidencia experimental por ter boas entradas."""
    a = measured("a", 1.0)
    b = measured("b", 2.0)
    out = derive("modelo", 3.0, [a, b], ceiling=Status.COMPUTATIONAL_EVIDENCE)
    assert out.status is Status.COMPUTATIONAL_EVIDENCE


def test_a_new_gap_caps_the_derived_status() -> None:
    """Uma lacuna aberta durante o calculo rebaixa o resultado, ainda que as entradas sejam medidas."""
    parent = measured("medido", 1.0)
    assert parent.status is Status.OBSERVATION
    out = derive(
        "filho", 2.0, [parent], ceiling=Status.EXPERIMENTAL_EVIDENCE, extra_gaps=["G-002"]
    )
    assert out.status is Status.CONDITIONAL_RESULT
    assert out.gaps == ("G-002",)


def test_gap_propagates_from_parent_to_child() -> None:
    parent = Finding("com_lacuna", 1.0, Status.CONDITIONAL_RESULT, gaps=("G-003",))
    out = derive("filho", 2.0, [parent], ceiling=Status.EXPERIMENTAL_EVIDENCE)
    assert out.status is Status.CONDITIONAL_RESULT
    assert out.gaps == ("G-003",)


def test_cannot_promote_a_finding_with_open_gaps() -> None:
    with pytest.raises(StatusViolation):
        Finding("x", 1.0, Status.EXPERIMENTAL_EVIDENCE, gaps=("G-005",))


def test_status_must_be_typed() -> None:
    with pytest.raises(StatusViolation):
        Finding("x", 1.0, "EXPERIMENTAL_EVIDENCE")  # type: ignore[arg-type]


def test_findingset_ignores_declared_absences_in_weakest() -> None:
    fs = FindingSet("t")
    fs.add(Finding("resultado", 1.0, Status.CONDITIONAL_RESULT, gaps=("G-003",)))
    fs.add(Finding("nao_medido", None, Status.OPEN_GAP, gaps=("G-002",)))
    assert fs.weakest is Status.CONDITIONAL_RESULT
    assert [f.name for f in fs.declared_absences] == ["nao_medido"]
    assert "G-002" in fs.open_gaps, "a lacuna continua visivel, so nao rebaixa o resultado"


# ------------------------------------------------------------------------------ lint ---


def test_lint_catches_forbidden_vocabulary() -> None:
    problems = lint_text("O problema esta resolvido e o metodo e universal.")
    terms = {p.term for p in problems}
    assert "resolvido" in terms and "universal" in terms


def test_lint_rejects_unqualified_multiplier() -> None:
    problems = lint_text("O ASIC e 100x mais rapido.")
    assert any("qualificadores" in p.reason for p in problems)


def test_lint_respects_word_boundaries() -> None:
    """"aprovado" contem "provado" e nao pode disparar.

    Antes desta correcao o lint acusava o DECISION_LOG por dizer "sem candidato aprovado".
    """
    assert lint_text("Sem candidato aprovado, nao ha o que gerar.") == []
    assert lint_text("O resultado foi comprovado externamente.") == []
    assert [p.term for p in lint_text("Esta provado.")] == ["provado"]


def test_lint_allow_marker_exempts_the_line() -> None:
    """A politica precisa citar os termos que proibe."""
    from douvras_core.status import LINT_ALLOW

    assert lint_text(f"resolvido, garantido, universal {LINT_ALLOW}") == []
    assert lint_text("resolvido, garantido, universal") != []


def test_governance_documents_pass_their_own_lint() -> None:
    """Os documentos que definem a regra precisam obedece-la.

    Varre as fases do Silicon Atlas **e** a governanca compartilhada na raiz do monorepo,
    onde a `STATUS_POLICY` passou a morar quando o contrato virou `douvras_core`.
    """
    from douvras_core.paths import PHASES, REPO_ROOT, project_root

    root = project_root("silicon-atlas")
    alvos = [root / d for d in PHASES] + [REPO_ROOT / "00_GOVERNANCE"]
    problemas = []
    for d in alvos:
        for f in d.rglob("*.md"):
            problemas += [f"{f.name}:{p.line_no}: {p.term}" for p in lint_text(
                f.read_text(encoding="utf-8")
            )]
    assert not problemas, problemas


def test_lint_accepts_fully_qualified_claim() -> None:
    text = (
        "No modelo llama-3.1-8b, fase decode, lote 1, contexto 4096, precisao int8, "
        "contra o baseline h100-sxm com consumo de servidor declarado, "
        "o prototipo apresentou 3x mais rapido em throughput. "
        "Resultado nao reproduzido externamente."
    )
    assert lint_text(text) == []
