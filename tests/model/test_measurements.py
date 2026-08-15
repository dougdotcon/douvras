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


def test_o_corpus_tem_ao_menos_uma_medicao_publicada() -> None:
    """Premissa dos testes abaixo. Se cair, eles passariam por vacuidade."""
    assert "tucano-2b4-instruct" in available()


def test_modelo_sem_execucao_nao_tem_medicao() -> None:
    assert Measurement.load("smollm3-3b") is None


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
        AssessmentInputs(model_id="smollm3-3b", run_id="20260815T000000Z"), registry, tasks_corpus
    )
    assert a.evaluable is False
    assert a.findings.by_name("tokens_por_segundo").value is None
    texto = a.render()
    assert "nenhuma capacidade foi medida" in texto.lower()


def test_o_artefato_publicado_carrega_a_proveniencia_da_execucao() -> None:
    """Uma medição sem hash dos pesos, runtime e quantização não é interpretável depois."""
    from model_atlas.measurements import RUNS_DIR

    doc = json.loads(
        (RUNS_DIR / "RUN-tucano-2b4-instruct-agent-ptbr-v2.json").read_text(encoding="utf-8")
    )
    for campo in ("model_sha256", "runtime", "quantization", "prompt_version", "max_steps", "host"):
        assert doc.get(campo), f"medicao sem `{campo}`"
    assert len(doc["model_sha256"]) == 64
