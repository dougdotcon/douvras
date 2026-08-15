"""Portao de emissao do assessment (Metodo 3.2 e 3.3).

O relatorio nao e um template preenchido: e um artefato que so sai se o contrato for cumprido.
Estes testes verificam que a recusa funciona — um portao que nunca fecha nao e portao.
"""

from __future__ import annotations

import pytest

from silicon_atlas.assessment import (
    MANDATORY_SECTIONS,
    Assessment,
    AssessmentInputs,
    EmissionRefused,
)
from douvras_core.status import Status, lint_text


@pytest.fixture(scope="module")
def result() -> Assessment:
    return Assessment.build(
        AssessmentInputs(model_id="llama-3.1-8b", mc_samples=3000, annual_tokens=1e13)
    )


def test_assessment_runs_end_to_end(result: Assessment) -> None:
    assert result.spec.id == "llama-3.1-8b"
    assert len(result.candidates) > 0
    assert result.serving.decode_time_share > 0.5
    assert result.sens_lhs.samples > 0


def test_verdict_is_a_sentence_and_caveats_are_separate(result: Assessment) -> None:
    """Regressao: `verdict` chegou a devolver None por falta de `return` apos refatoracao.

    E as ressalvas ficam numa lista propria porque encavala-las no veredito produzia um periodo
    ilegivel com negrito aninhado quebrando o markdown.
    """
    assert isinstance(result.verdict, str) and result.verdict
    for marcador in ("F3 disparado", "do custo", "Ressalva", "porem o ranking"):
        assert marcador not in result.verdict, (
            f"ressalva concatenada no veredito: {marcador!r}"
        )
    assert "**" not in result.verdict, "negrito aninhado quebra o markdown da afirmacao principal"
    assert all(isinstance(c, str) and c for c in result.caveats)
    texto = result.render()
    assert f"**Recomendacao: {result.verdict}.**" in texto
    if result.caveats:
        assert "Ressalvas que qualificam esta recomendacao" in texto


def test_report_contains_all_mandatory_sections(result: Assessment) -> None:
    text = result.render()
    headings = (
        "Pergunta principal", "Afirmacao principal", "Hipoteses", "Dependencias",
        "Criterios de falha", "Resultados", "Limitacoes", "NAO demonstra",
    )
    for h in headings:
        assert h in text, f"secao obrigatoria ausente: {h}"
    assert len(MANDATORY_SECTIONS) == 8


def test_report_passes_its_own_lint(result: Assessment) -> None:
    """O relatorio nao pode violar a regra que ele mesmo impoe ao resto do projeto."""
    assert lint_text(result.render()) == []


def test_emission_is_refused_without_sensitivity(result: Assessment) -> None:
    import dataclasses

    broken = dataclasses.replace(result, sens_lhs=dataclasses.replace(result.sens_lhs, samples=0))
    with pytest.raises(EmissionRefused, match="sensibilidade"):
        broken.render()


def test_emission_is_refused_on_forbidden_vocabulary(result: Assessment, monkeypatch) -> None:
    import silicon_atlas.assessment as mod

    original = mod._render_sections

    def poisoned(a):
        s = original(a)
        s["resultados"] += "\n\nO problema esta resolvido e o ganho e garantido."
        return s

    monkeypatch.setattr(mod, "_render_sections", poisoned)
    with pytest.raises(EmissionRefused, match="vocabulario proibido"):
        result.render()


def test_every_falsifier_is_evaluated(result: Assessment) -> None:
    fs = result.falsifier_status()
    assert set(fs) == {"F1", "F2", "F3", "F4", "F5"}
    for key, data in fs.items():
        # None e um terceiro estado legitimo: "nao avaliavel" nao e "nao disparou".
        assert data["disparado"] in (True, False, None), key
        assert data["observado"], f"{key} sem valor observado"


@pytest.mark.falsifier
def test_falsifiers_actually_fire(result: Assessment) -> None:
    """O estado dos falsificadores e travado por valor, nao por tipo.

    A versao anterior deste teste so verificava que `disparado` era um bool. Com ela, forcar
    todos os falsificadores para False mantinha a suite verde — ou seja, a suite nao detectava
    a inversao do proprio mecanismo de falsificacao. Alterar a lista abaixo exige entrada
    correspondente em `00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md`.
    """
    fs = result.falsifier_status()
    disparados = sorted(k for k, v in fs.items() if v["disparado"] is True)
    nao_avaliaveis = sorted(k for k, v in fs.items() if v["disparado"] is None)
    assert disparados == ["F1", "F2", "F3"], (
        f"estado esperado para llama-3.1-8b no ciclo C-001; obtido: {disparados}"
    )
    assert nao_avaliaveis == ["F4"], (
        "F4 nao e avaliavel sem ponto de projeto (R-003); obtido: " + str(nao_avaliaveis)
    )
    assert fs["F5"]["disparado"] is False


@pytest.mark.falsifier
def test_f3_fires_when_ranking_is_unstable(result: Assessment) -> None:
    """Gatilho sintetico: se a estabilidade do ranking cair, F3 precisa disparar."""
    import dataclasses

    estavel = dataclasses.replace(
        result, sens_lhs=dataclasses.replace(result.sens_lhs, top1_stability=0.99, margin=1.0)
    )
    assert estavel.falsifier_status()["F3"]["disparado"] is False
    instavel = dataclasses.replace(
        result, sens_lhs=dataclasses.replace(result.sens_lhs, top1_stability=0.10, margin=1.0)
    )
    assert instavel.falsifier_status()["F3"]["disparado"] is True


@pytest.mark.falsifier
def test_f5_fires_when_param_count_diverges(result: Assessment) -> None:
    """Gatilho sintetico: contagem publicada errada precisa disparar F5."""
    import dataclasses

    quebrado = dataclasses.replace(result, spec=dataclasses.replace(result.spec, published_params=1))
    assert quebrado.falsifier_status()["F5"]["disparado"] is True


def test_f5_is_not_triggered_for_corpus_models(result: Assessment) -> None:
    assert result.falsifier_status()["F5"]["disparado"] is False


def test_no_finding_claims_tapeout_grade_evidence(result: Assessment) -> None:
    """Enquanto houver lacuna aberta, nada no relatorio pode sustentar uma decisao irreversivel."""
    for f in result.findings.items:
        assert not f.status.supports_tapeout, f"{f.name} = {f.status.name}"


def test_weakest_status_is_reported_and_bounded(result: Assessment) -> None:
    assert result.findings.weakest <= Status.CONDITIONAL_RESULT
    assert result.findings.open_gaps, "um assessment sem lacunas declaradas seria suspeito"


def test_json_export_is_serializable(result: Assessment) -> None:
    import json

    doc = json.loads(result.to_json())
    for key in ("recommendation", "verdict", "falsifiers", "economics", "partition", "srs"):
        assert key in doc


def test_scope_effect_is_surfaced(result: Assessment) -> None:
    """O escopo de comparacao muda o numero e precisa aparecer no relatorio, nao no rodape."""
    text = result.render()
    assert "Efeito do escopo" in text
    assert result.stability.recent_exact_stability is not None


def test_claimed_gain_is_confronted_with_the_ceiling(result: Assessment) -> None:
    text = result.render()
    assert "Amdahl" in text
    check = result.findings.by_name("partition.claim_check")
    assert check.note
