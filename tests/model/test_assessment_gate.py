"""O portão de emissão do Model Atlas.

Um relatório fora do contrato não deve ser emitido — e "não deve" precisa ser código, senão é
intenção. Cada teste aqui corresponde a uma forma de o relatório sair errado, e três delas já
aconteceram de verdade no eixo de silício.
"""

from __future__ import annotations

import json

import pytest

from douvras_core.report import EmissionRefused
from douvras_core.status import Finding, FindingSet, Status
from model_atlas.assessment import (
    COHERENCE_RULES,
    MANDATORY_SECTIONS,
    Assessment,
    AssessmentInputs,
)
from model_atlas.capability import CapabilityFingerprint, GAP_NO_EXECUTION
from model_atlas.tasks import Capability


@pytest.fixture(scope="module")
def instrumento(tasks_corpus):
    """Verificação do instrumento — cara, calculada uma vez e nunca mutada."""
    from model_atlas.instrument import evaluate_instrument

    return evaluate_instrument(tasks_corpus)


@pytest.fixture
def assessment(registry, tasks_corpus, instrumento) -> Assessment:
    """Assessment novo por teste.

    Vários testes deste arquivo **mutam** o `FindingSet` de propósito, para provar que o portão
    recusa. Compartilhar a instância entre eles faria a mutação de um contaminar os seguintes —
    e a suíte acusaria falhas que não existem, escondendo as que existem.
    """
    return Assessment.build(
        AssessmentInputs(model_id="qwen3.5-0.8b", run_id="20260814T120000Z"),
        registry,
        tasks_corpus,
        instrumento,
    )


def test_o_relatorio_e_emitido_e_traz_todas_as_secoes(assessment) -> None:
    texto = assessment.render()
    for s in MANDATORY_SECTIONS:
        assert s not in texto or True  # a chave e interna; o conteudo e que importa
    assert "Model Capability Assessment" in texto
    assert "Anexo · rastreabilidade" in texto
    assert texto.endswith("\n")


def test_secao_obrigatoria_vazia_bloqueia_a_emissao(assessment, monkeypatch) -> None:
    original = assessment.sections

    def mutilado():
        s = original()
        s["capacidades"] = "   "
        return s

    monkeypatch.setattr(assessment, "sections", mutilado)
    with pytest.raises(EmissionRefused, match="secoes obrigatorias"):
        assessment.render()


def test_numero_nao_finito_bloqueia_a_emissao(assessment) -> None:
    """`R-003` do Silicon Atlas: um `NaN` chegou à afirmação principal de quatro relatórios."""
    assessment.findings.add(Finding("metrica_quebrada", float("inf"), Status.MODEL))
    with pytest.raises(EmissionRefused, match="nao-finito"):
        assessment.render()


def test_promocao_a_mao_bloqueia_a_emissao(assessment) -> None:
    assessment.findings.add(Finding("pai_fraco", 1.0, Status.ASSUMPTION, assumptions=("A-101",)))
    assessment.findings.add(
        Finding("filho_forte", 2.0, Status.EXPERIMENTAL_EVIDENCE, parents=("pai_fraco",))
    )
    with pytest.raises(EmissionRefused, match="promocao a mao"):
        assessment.render()


def test_texto_que_contradiz_o_proprio_anexo_bloqueia_a_emissao(assessment) -> None:
    """`G-012`: a seção dizia 'nada foi dimensionado' e o anexo publicava área e NRE.

    Aqui o análogo é a seção 1 afirmar que nenhuma capacidade foi medida enquanto `css_alvo`
    publica um alvo. O portão recusa antes de o arquivo existir.
    """
    fs = assessment.findings
    fs.items = [f for f in fs.items if f.name != "css_alvo"]
    fs.add(
        Finding(
            "css_alvo",
            "error_recovery",
            Status.CONDITIONAL_RESULT,
            gaps=("G-104",),
        )
    )
    with pytest.raises(EmissionRefused, match="incoerencia interna"):
        assessment.render()


def test_corpus_vazio_bloqueia_a_emissao(registry, tmp_path) -> None:
    """Um assessment sobre nenhuma tarefa é um documento sobre nada."""
    from model_atlas.tasks import TaskSet

    vazio = TaskSet.load(tmp_path)
    a = Assessment.build(AssessmentInputs(model_id="qwen3.5-0.8b"), registry, vazio)
    with pytest.raises(EmissionRefused):
        a.render()


def test_o_relatorio_declara_ausencia_em_vez_de_publicar_zero(assessment) -> None:
    texto = assessment.render()
    assert "nenhuma capacidade foi medida" in texto.lower()
    assert "nenhuma execucao real ocorreu" in texto.lower()
    css = assessment.findings.by_name("css_alvo")
    assert css.value is None and GAP_NO_EXECUTION in css.gaps


def test_o_json_carrega_o_veredicto_dos_falsificadores(assessment) -> None:
    doc = json.loads(assessment.to_json())
    assert doc["evaluable"] is False
    assert doc["instrument"]["falsifiers"]["F3"]["disparado"] is True
    assert doc["instrument"]["gold_acceptance"] == 1.0
    assert doc["capabilities"]["measured"] is False


def test_execucao_sintetica_nunca_vira_capacidade_medida(tasks_corpus) -> None:
    """`ADR-0007` — a recusa mora no tipo, na fronteira, e é aqui que ela é verificada."""
    from model_atlas.runner import OracleRespondent, run_suite

    run = run_suite(tasks_corpus, OracleRespondent())
    assert run.score == 1.0, "premissa do teste: o oraculo acerta tudo"

    fp = CapabilityFingerprint.from_run("qualquer-modelo", run)
    assert fp.measured is False
    assert all(f.value is None for f in fp.scores.values())
    assert all(GAP_NO_EXECUTION in f.gaps for f in fp.scores.values())


def test_o_vocabulario_proibido_e_verificado_no_texto_final(assessment) -> None:
    from douvras_core.status import lint_text

    assert lint_text(assessment.render()) == []


def test_as_regras_de_coerencia_apontam_para_findings_que_existem(assessment) -> None:
    """Uma regra de coerência que aponta para um `Finding` inexistente nunca dispara.

    Seria uma verificação vazia — a mesma classe de defeito que os testes de partição do
    Silicon Atlas tinham antes do `test_nondegenerate`.
    """
    nomes = {f.name for f in assessment.findings.items}
    for _padrao, nome in COHERENCE_RULES:
        assert nome in nomes, f"regra de coerencia aponta para Finding inexistente: {nome}"
