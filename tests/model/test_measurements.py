"""Medição real como evidência versionada.

Com o corpus atual, apenas `tucano-2b4-instruct` tem execução publicada. Sem estes testes, o
ramo medido de `Assessment.build` — capacidade real, telemetria real, Failure Atlas real —
atravessaria o ciclo exercitado só pelo script, e trocar a leitura por outra errada manteria a
suíte verde. É a mesma lição do `G-014` do Silicon Atlas, agora do lado da medição.
"""

from __future__ import annotations

import json

import pytest

from douvras_core.status import Status
from model_atlas.assessment import Assessment, AssessmentInputs
from model_atlas.capability import GAP_NO_EXECUTION
from model_atlas.measurements import Measurement, MeasurementError, available


#: Modelo do corpus sem pesos locais. Fixar um id aqui é frágil por natureza — a primeira versão
#: destes testes usava `smollm3-3b`, que passou a ser medido no mesmo ciclo e derrubou dois
#: testes. A guarda em `test_o_corpus_ainda_tem_um_modelo_sem_execucao` existe para que a próxima
#: vez falhe com a mensagem certa em vez de passar por vacuidade.
SEM_EXECUCAO = "qwen3.5-0.8b"


def test_o_corpus_tem_ao_menos_uma_medicao_publicada() -> None:
    """Premissa dos testes abaixo. Se cair, eles passariam por vacuidade."""
    assert "tucano-2b4-instruct" in available()


def test_o_corpus_ainda_tem_um_modelo_sem_execucao() -> None:
    """Se este cair, escolha outro `SEM_EXECUCAO` — não relaxe a asserção do teste seguinte."""
    assert SEM_EXECUCAO not in available()


def test_modelo_sem_execucao_nao_tem_medicao() -> None:
    assert Measurement.load(SEM_EXECUCAO) is None


def test_execucao_diagnostica_nao_e_carregada_como_medicao() -> None:
    """`ADR-0007` do lado do few-shot: modo diagnóstico não vira escore publicado."""
    m = Measurement.load("tucano-2b4-instruct")
    assert m is not None
    assert m.fewshot is False


def test_medicao_sem_proveniencia_e_recusada() -> None:
    with pytest.raises(MeasurementError, match="prompt_version"):
        Measurement.from_doc({"model_id": "x", "model_file": "y", "grades": []})


def test_medicao_real_autoriza_capacidade_medida() -> None:
    m = Measurement.load("tucano-2b4-instruct")
    run = m.to_run_result()
    assert run.synthetic is False, "sem isto o fingerprint recusaria emitir capacidade"
    assert len(run.grades) == m.tasks


def test_o_resultado_medido_e_zero_com_zero_chamadas_de_ferramenta() -> None:
    """Fixa o achado do ciclo. Se mudar, é porque houve nova execução — e aí o assessment,
    a `CHANGELOG` e este teste mudam juntos, de propósito."""
    m = Measurement.load("tucano-2b4-instruct")
    assert m.tasks == 96
    assert m.tool_calls == 0
    assert sum(1 for g in m.grades if g.passed) == 0
    assert m.prompt_version == "agent-ptbr-v2"
    assert m.quantization == "q4"


def test_assessment_de_modelo_medido_publica_capacidade_e_telemetria(registry, tasks_corpus) -> None:
    a = Assessment.build(
        AssessmentInputs(model_id="tucano-2b4-instruct", run_id="20260815T000000Z"),
        registry,
        tasks_corpus,
    )
    assert a.evaluable is True
    assert a.measurement is not None

    for f in a.fingerprint.scores.values():
        assert f.value is not None, "capacidade medida nao pode sair como ausencia"
        assert f.status is Status.OBSERVATION
        assert GAP_NO_EXECUTION not in f.gaps

    tokens = a.findings.by_name("tokens_por_segundo")
    assert tokens.value is not None and tokens.status is Status.OBSERVATION

    texto = a.render()
    assert "0 chamadas de ferramenta" in texto
    assert "nenhuma capacidade foi medida" not in texto.lower()
    assert "agent-ptbr-v2" in texto


def test_assessment_de_modelo_sem_pesos_continua_declarando_ausencia(registry, tasks_corpus) -> None:
    """O caminho antigo não pode ter regredido: os dois convivem no mesmo corpus."""
    a = Assessment.build(
        AssessmentInputs(model_id=SEM_EXECUCAO, run_id="20260815T000000Z"), registry, tasks_corpus
    )
    assert a.evaluable is False
    assert a.findings.by_name("tokens_por_segundo").value is None
    texto = a.render()
    assert "nenhuma capacidade foi medida" in texto.lower()


def test_o_segundo_modelo_medido_chama_ferramentas() -> None:
    """Contraexemplo que retratou `C-108` (ver `R-102`). Fixa o número que derrubou a alegação."""
    m = Measurement.load("smollm3-3b")
    assert m is not None
    assert m.tool_calls == 78, "78 chamadas contra zero do tucano — o falsificador de C-108"
    assert m.conversation_format == "chat-template"
    assert m.system_mode == "/no_think", "modo declarado: em modelo hibrido ele decide o escore"


def test_a_margem_agregada_entre_os_dois_modelos_reais_continua_abaixo_do_limiar() -> None:
    """A segunda medição **não** desfaz `R-101`, e este teste impede que alguém suponha que sim.

    Entre um modelo que nunca chama ferramenta e um que chama 78 vezes, o escore agregado
    difere em 0,104 — abaixo do limiar de 0,20 declarado em `F3`. O sinal está no perfil por
    capacidade, não no agregado.
    """
    a, b = Measurement.load("tucano-2b4-instruct"), Measurement.load("smollm3-3b")
    esc = lambda m: sum(1 for g in m.grades if g.passed) / len(m.grades)  # noqa: E731
    assert esc(b) - esc(a) < 0.20

    por_cap = lambda m: {  # noqa: E731
        c: [g.passed for g in m.grades if g.capability is c] for c in {g.capability for g in m.grades}
    }
    ca, cb = por_cap(a), por_cap(b)
    margens = [
        sum(cb[c]) / len(cb[c]) - sum(ca[c]) / len(ca[c]) for c in cb if c in ca and ca[c] and cb[c]
    ]
    assert max(margens) > 0.20, "alguma capacidade tem de separar, ou C-109 cai"


def test_o_artefato_publicado_carrega_a_proveniencia_da_execucao() -> None:
    """Uma medição sem hash dos pesos, runtime e quantização não é interpretável depois."""
    from model_atlas.measurements import RUNS_DIR

    doc = json.loads(
        (RUNS_DIR / "RUN-tucano-2b4-instruct-agent-ptbr-v2.json").read_text(encoding="utf-8")
    )
    for campo in ("model_sha256", "runtime", "quantization", "prompt_version", "max_steps", "host"):
        assert doc.get(campo), f"medicao sem `{campo}`"
    assert len(doc["model_sha256"]) == 64
