"""O contrato do `douvras_core`, testado sem nenhum dominio.

Estes testes existem porque a extracao do core e uma afirmacao: a de que a escala de status,
os portoes e o portao de emissao sao epistemologia e nao vocabulario de hardware. Se algum
deles precisasse de um `ModelSpec` ou de um `Device` para passar, a afirmacao seria falsa.

Nenhum arquivo aqui importa `silicon_atlas` ou `model_atlas`.
"""

from __future__ import annotations

import math

import pytest

from douvras_core import gates as G
from douvras_core.paths import PHASES, PROJECTS, REPO_ROOT, UnknownProject, project_root
from douvras_core.report import (
    EmissionRefused,
    check_coherence,
    check_finite,
    check_no_hand_promotion,
    check_sections,
    check_vocabulary,
    evidence_appendix,
)
from douvras_core.status import (
    Finding,
    FindingSet,
    Status,
    StatusViolation,
    derive,
)

# ------------------------------------------------------------------ escala de status ---


def test_status_order_is_total_and_min_is_the_weakest_link() -> None:
    ordered = sorted(Status)
    assert ordered[0] is Status.RETRACTED
    assert ordered[-1] is Status.EXTERNALLY_VERIFIED
    assert min(Status.OBSERVATION, Status.ASSUMPTION) is Status.ASSUMPTION


def test_status_policy_document_lists_every_enum_member() -> None:
    """A politica descreve o codigo, ou a politica esta mentindo.

    Regressao registrada no ciclo C-001: `STATUS_POLICY.md` citava `Status.rank`, que nao
    existia. Um documento normativo que descreve um mecanismo inexistente e pior que ausente.
    """
    txt = (REPO_ROOT / "00_GOVERNANCE" / "STATUS_POLICY.md").read_text(encoding="utf-8")
    ausentes = [s.name for s in Status if f"`{s.name}`" not in txt]
    assert not ausentes, f"status sem linha na politica: {ausentes}"


def test_rank_is_dense_and_ordered() -> None:
    ranks = [s.rank for s in sorted(Status)]
    assert ranks == list(range(len(Status)))


# --------------------------------------------------------------------- propagacao ---


def test_derive_takes_the_weakest_parent() -> None:
    forte = Finding("forte", 1.0, Status.OBSERVATION)
    fraco = Finding("fraco", 2.0, Status.ASSUMPTION, assumptions=("A-1",))
    out = derive("filho", 3.0, [forte, fraco], ceiling=Status.EXPERIMENTAL_EVIDENCE)
    assert out.status is Status.ASSUMPTION
    assert out.assumptions == ("A-1",)


def test_ceiling_caps_a_strong_parent() -> None:
    """Um metodo analitico nao vira evidencia experimental por ter boas entradas."""
    pai = Finding("medido", 1.0, Status.EXPERIMENTAL_EVIDENCE)
    out = derive("modelado", 2.0, [pai], ceiling=Status.COMPUTATIONAL_EVIDENCE)
    assert out.status is Status.COMPUTATIONAL_EVIDENCE


def test_open_gap_caps_at_conditional_result() -> None:
    pai = Finding("com_lacuna", 1.0, Status.CONDITIONAL_RESULT, gaps=("G-101",))
    out = derive("filho", 2.0, [pai], ceiling=Status.EXTERNALLY_VERIFIED)
    assert out.status is Status.CONDITIONAL_RESULT
    assert out.gaps == ("G-101",)


def test_finding_with_gap_cannot_be_born_promoted() -> None:
    with pytest.raises(StatusViolation):
        Finding("promovido", 1.0, Status.EXPERIMENTAL_EVIDENCE, gaps=("G-101",))


def test_status_must_be_typed() -> None:
    with pytest.raises(StatusViolation):
        Finding("sem_tipo", 1.0, "COMPUTATIONAL_EVIDENCE")  # type: ignore[arg-type]


# ------------------------------------------------------------------------- portoes ---


def test_has_all_refuses_a_missing_file(tmp_path) -> None:
    """Arquivo ausente reprova. Um portao que aprova por ausencia nao e portao."""
    assert G.has_all(tmp_path / "nao_existe.md", ("qualquer",)) is False


def test_has_all_requires_every_needle(tmp_path) -> None:
    p = tmp_path / "doc.md"
    p.write_text("tem A e tem B", encoding="utf-8")
    assert G.has_all(p, ("A", "B")) is True
    assert G.has_all(p, ("A", "C")) is False


def test_numbered_falsifiers_are_required_not_just_the_word(tmp_path) -> None:
    p = tmp_path / "charter.md"
    p.write_text("Este estudo tem criterios de falha bem definidos.", encoding="utf-8")
    assert G.has_numbered_falsifiers(p) is False
    p.write_text("Criterios: F1, F2, F3.", encoding="utf-8")
    assert G.has_numbered_falsifiers(p) is True


def test_gap_count_separates_open_from_partial(tmp_path) -> None:
    """O numero que o README publicava e o que o CLI imprimia discordavam por isto."""
    p = tmp_path / "GAP_REGISTER.md"
    p.write_text(
        "| G-1 | x | y | z | OPEN |\n"
        "| G-2 | x | y | z | OPEN |\n"
        "| G-3 | x | y | z | **PARCIAL** — caso conhecido fechado |\n",
        encoding="utf-8",
    )
    c = G.count_gaps(p)
    assert (c.open, c.partial, c.total) == (2, 1, 3)
    assert "2 abertas" in str(c) and "3 registradas" in str(c)


def test_external_reviews_ignores_a_readme(tmp_path) -> None:
    """O erro que transformaria V3 numa formalidade satisfeita por existir a pasta."""
    d = tmp_path / "EXTERNAL_REVIEWS"
    d.mkdir()
    (d / "README.md").write_text("indice", encoding="utf-8")
    assert G.external_reviews(d) == []
    (d / "ER-001-silva.md").write_text("revisao", encoding="utf-8")
    assert len(G.external_reviews(d)) == 1


def test_verified_suite_requires_zero_failures(tmp_path) -> None:
    p = tmp_path / "last_verification.json"
    p.write_text('{"tests_passed": true, "passed": 10, "failed": 2}', encoding="utf-8")
    ok, _ = G.verified_suite(p)
    assert ok is False
    p.write_text('{"tests_passed": true, "passed": 10, "failed": 0}', encoding="utf-8")
    ok, data = G.verified_suite(p)
    assert ok is True and data["passed"] == 10


def test_gate_report_lists_blocked_gates() -> None:
    r = G.summarize(
        [G.Gate("D0", True, "ok"), G.Gate("V3", False, "sem revisao externa")],
        G.GapCount(open=3, partial=1),
    )
    assert r.blocked == ["V3"]
    assert r.passed_count == 1
    texto = r.render()
    assert "BLOQUEADO" in texto and "V3 — sobrevivencia minima" in texto


# --------------------------------------------------------------- portao de emissao ---


def test_missing_section_refuses_emission() -> None:
    with pytest.raises(EmissionRefused, match="secoes obrigatorias"):
        check_sections({"a": "conteudo", "b": "   "}, ["a", "b"])


def test_non_finite_number_refuses_emission() -> None:
    """`inf` e resposta a pergunta mal-posta. Publicar a resposta esconde a pergunta."""
    fs = FindingSet("t")
    fs.add(Finding("bom", 1.0, Status.OBSERVATION))
    fs.add(Finding("break_even", math.inf, Status.MODEL))
    with pytest.raises(EmissionRefused, match="nao-finito"):
        check_finite(fs)


def test_declared_absence_passes_the_finite_check() -> None:
    fs = FindingSet("t")
    fs.add(Finding("nao_medido", None, Status.OPEN_GAP, gaps=("G-101",)))
    check_finite(fs)  # nao levanta: ausencia declarada e o comportamento correto


def test_forbidden_vocabulary_refuses_emission() -> None:
    with pytest.raises(EmissionRefused, match="vocabulario proibido"):
        check_vocabulary("O problema esta resolvido e o metodo e universal.")


def test_coherence_catches_text_contradicting_its_own_findings() -> None:
    """G-012: a secao dizia 'nada foi dimensionado' e o anexo publicava area e NRE."""
    fs = FindingSet("t")
    fs.add(Finding("nre_total", 40e6, Status.ASSUMPTION, assumptions=("A-6",)))
    texto = "Nenhum NRE foi estimado, porque nao existe ponto de projeto."
    with pytest.raises(EmissionRefused, match="incoerencia interna"):
        check_coherence(texto, fs, [(r"nenhum NRE foi estimado", "nre_total")])


def test_coherence_passes_when_the_absence_is_real() -> None:
    fs = FindingSet("t")
    fs.add(Finding("nre_total", None, Status.OPEN_GAP, gaps=("G-5",)))
    check_coherence(
        "Nenhum NRE foi estimado.", fs, [(r"nenhum NRE foi estimado", "nre_total")]
    )


def test_hand_promotion_is_refused() -> None:
    fs = FindingSet("t")
    fs.add(Finding("pai", 1.0, Status.ASSUMPTION, assumptions=("A-1",)))
    fs.add(Finding("filho", 2.0, Status.EXPERIMENTAL_EVIDENCE, parents=("pai",)))
    with pytest.raises(EmissionRefused, match="promocao a mao"):
        check_no_hand_promotion(fs)


def test_derive_output_survives_the_hand_promotion_check() -> None:
    """A verificacao nao pode acusar quem usou o caminho correto."""
    fs = FindingSet("t")
    pai = fs.add(Finding("pai", 1.0, Status.ASSUMPTION, assumptions=("A-1",)))
    fs.add(derive("filho", 2.0, [pai]))
    check_no_hand_promotion(fs)


def test_evidence_appendix_shows_absences_instead_of_hiding_them() -> None:
    fs = FindingSet("t")
    fs.add(Finding("medido", 0.42, Status.OBSERVATION, unit="s"))
    fs.add(Finding("nao_medido", None, Status.OPEN_GAP, gaps=("G-102",)))
    txt = evidence_appendix(fs)
    assert "ausencia declarada" in txt
    assert "G-102" in txt and "OPEN_GAP" in txt
    assert "Divida de evidencia" in txt


# --------------------------------------------------------------------------- paths ---


def test_unknown_project_raises_instead_of_returning_a_dead_path() -> None:
    with pytest.raises(UnknownProject):
        project_root("atlas-que-nao-existe")


def test_every_declared_project_exists_with_its_phases() -> None:
    for name in PROJECTS:
        root = project_root(name)
        assert root.is_dir(), f"{name} declarado em PROJECTS mas ausente do disco"
        faltando = [p for p in PHASES if not (root / p).is_dir()]
        assert not faltando, f"{name} sem fases DOUVRAS: {faltando}"


def test_env_override_redirects_the_project_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOUVRAS_MODEL_ATLAS_ROOT", str(tmp_path))
    assert project_root("model-atlas") == tmp_path.resolve()
