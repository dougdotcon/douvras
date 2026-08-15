"""Os seis falsificadores do ciclo C-002, como testes.

Cada teste aqui implementa um critério de falha declarado na `PROBLEM_CHARTER` **antes** da
execução. Não são testes de regressão: são a carta do problema executando.

O teste mais importante deste arquivo é `test_f3_dispara_e_permanece_disparado`. Ele fixa uma
conclusão negativa — se alguém baixar o limiar para fazê-lo passar, o teste quebra e o diff
mostra exatamente o que foi afrouxado.
"""

from __future__ import annotations

import pytest

from model_atlas.graders import grade
from model_atlas.instrument import (
    MIN_DISCRIMINATION_MARGIN,
    MIN_TASKS_PER_CAPABILITY,
    evaluate_instrument,
)
from model_atlas.runner import PROBES, counterexample_trajectory, run_suite, run_task
from model_atlas.tasks import FailureMode, TaskSet


@pytest.fixture(scope="module")
def tasks() -> TaskSet:
    return TaskSet.load()


@pytest.fixture(scope="module")
def report(tasks: TaskSet):
    return evaluate_instrument(tasks)


@pytest.mark.falsifier
def test_f2_todo_gabarito_passa_no_proprio_criterio(tasks: TaskSet) -> None:
    """F2 — o grader não pode rejeitar a trajetória de referência de nenhuma tarefa.

    Se este falha, a regra de acerto contradiz o exemplo de acerto que a acompanha, e nenhum
    número derivado do corpus significa coisa alguma.
    """
    from model_atlas.runner import OracleRespondent

    oraculo = OracleRespondent()
    reprovadas = []
    for t in tasks:
        g = grade(t, run_task(t, oraculo))
        if not g.passed:
            reprovadas.append((t.id, [str(f) for f in g.failures], list(g.details)))
    assert not reprovadas, f"gabarito reprovado pelo proprio criterio: {reprovadas[:5]}"


@pytest.mark.falsifier
def test_f1_todo_contraexemplo_e_rejeitado_com_o_rotulo_certo(tasks: TaskSet) -> None:
    """F1 — cada trajetória declarada como errada é reprovada, e pelo motivo declarado.

    Reprovar pelo motivo errado é quase tão ruim quanto não reprovar: manda quem lê o Failure
    Atlas construir o dataset errado.
    """
    problemas = []
    for t in tasks:
        for ce in t.counterexamples:
            esperado = FailureMode(ce["expect_failure"])
            g = grade(t, counterexample_trajectory(ce))
            if g.passed:
                problemas.append(f"{t.id}[{ce['label']}]: ACEITO")
            elif esperado not in g.failures:
                problemas.append(
                    f"{t.id}[{ce['label']}]: esperado {esperado}, "
                    f"observado {[str(x) for x in g.failures]}"
                )
    assert not problemas, problemas[:5]


@pytest.mark.falsifier
def test_f3_dispara_e_permanece_disparado(report) -> None:
    """F3 — a margem agregada está abaixo do limiar declarado, e isso fica registrado.

    Este teste **fixa uma conclusão negativa**. `C-102` foi retratada em `R-101` com base nele.
    Se um dia a margem subir de verdade, este teste quebra e o caminho correto é atualizar a
    retratação — não o contrário: baixar `MIN_DISCRIMINATION_MARGIN` para o teste passar seria
    ajustar o instrumento ao resultado, e o diff mostraria exatamente isso.
    """
    assert MIN_DISCRIMINATION_MARGIN == 0.20, (
        "o limiar de F3 mudou; se foi decisão, registre no DECISION_LOG e atualize CE-101"
    )
    assert not report.discriminates
    assert report.discrimination_margin < MIN_DISCRIMINATION_MARGIN
    assert report.falsifiers()["F3"]["disparado"] is True


@pytest.mark.falsifier
def test_f4_duas_execucoes_produzem_os_mesmos_vereditos(tasks: TaskSet) -> None:
    """F4 — sem determinismo, o resultado não é auditável."""
    for probe, _ in PROBES:
        a = run_suite(tasks, probe)
        b = run_suite(tasks, probe)
        assert [g.as_dict() for g in a.grades] == [g.as_dict() for g in b.grades], probe.id


@pytest.mark.falsifier
def test_f5_toda_tarefa_e_avaliavel_e_a_cobertura_e_declarada(report, tasks: TaskSet) -> None:
    """F5 — regra sem grader, ou capacidade com corpus fino, torna a cobertura declarada falsa."""
    assert not report.ungradable, report.ungradable
    finas = {c: n for c, n in report.coverage.items() if n < MIN_TASKS_PER_CAPABILITY}
    assert not finas, f"capacidades abaixo de {MIN_TASKS_PER_CAPABILITY} tarefas: {finas}"
    sem_ce = [t.id for t in tasks if not t.counterexamples]
    assert not sem_ce, f"tarefas sem contraexemplo — o criterio nao e testavel: {sem_ce[:5]}"


@pytest.mark.falsifier
def test_f6_nenhum_modo_declarado_fica_sem_sonda(report) -> None:
    """F6 — um modo que nenhuma sonda provoca é célula morta na taxonomia."""
    assert not report.dead_modes, [str(m) for m in report.dead_modes]


def test_cada_sonda_cumpre_o_que_prometeu(tasks: TaskSet) -> None:
    """A promessa de `runner.PROBES` foi escrita antes da execução e é conferida aqui.

    Uma sonda que não cumpre não é uma sonda ruim: é evidência de que o grader não vê aquele
    modo pelo caminho que ela usa.
    """
    from model_atlas.instrument import probe_expectations

    quebradas = [r for r in probe_expectations(tasks) if not r["cumpriu"]]
    assert not quebradas, quebradas
