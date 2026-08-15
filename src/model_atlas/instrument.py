"""Avaliacao do instrumento: o benchmark mede o que diz medir?

Esta e a pergunta que o ciclo C-002 responde **sem executar nenhum modelo**, e e a pergunta
que quase todo projeto de benchmark pula. Publicar um leaderboard antes de saber se o grader
aceita o certo e rejeita o errado e publicar ruido com autoridade.

Quatro medidas, todas offline e todas sobre codigo e corpus — portanto `COMPUTATIONAL_EVIDENCE`
legitima, sem lacuna pendurada:

1. **Aceitacao do gabarito** — o grader aprova a trajetoria de referencia de toda tarefa?
   Se nao, o criterio de acerto contradiz o proprio exemplo de acerto (`F2`).
2. **Deteccao de contraexemplo** — o grader reprova cada trajetoria sabidamente errada, *e*
   com o rotulo certo? Reprovar pelo motivo errado manda o usuario construir o dataset errado
   (`F1`).
3. **Discriminacao** — o escore separa o oraculo das sondas degeneradas por margem maior que
   a dispersao entre elas? E o irmao direto do `CE-001` do Silicon Atlas: um escore que nao
   separa nao decide nada, por mais bem-comportado que pareca (`F3`).
4. **Cobertura da taxonomia** — todo modo de falha declarado no corpus e efetivamente
   disparado por alguma sonda? Um modo que ninguem consegue provocar e celula morta: o
   benchmark alega medir algo que nunca foi visto acontecer (`F6`).

Nada aqui autoriza uma frase sobre um modelo. Ver `capability.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from douvras_core.status import Finding, FindingSet, Status, derive

from .graders import UnknownRule, grade, validate_rules
from .runner import PROBES, RunResult, counterexample_trajectory, run_suite
from .tasks import Capability, EvalTask, FailureMode, TaskSet

#: Cobertura minima por capacidade para o corpus poder alegar que a mede (`F5`).
MIN_TASKS_PER_CAPABILITY = 8

#: Margem minima entre o oraculo e a melhor sonda degenerada para o escore ser considerado
#: discriminante. Nao tem base empirica — e decisao de projeto, registrada como `G-105`, e a
#: primeira coisa que um revisor externo deveria atacar.
MIN_DISCRIMINATION_MARGIN = 0.20


@dataclass
class CounterexampleCheck:
    task_id: str
    label: str
    expected: FailureMode
    rejected: bool
    labeled: bool
    observed: tuple[FailureMode, ...]


@dataclass
class InstrumentReport:
    """O que se sabe sobre o instrumento, e com que forca epistemica."""

    tasks: int
    coverage: dict[str, int]
    gold_accepted: int
    gold_total: int
    counterexamples: list[CounterexampleCheck] = field(default_factory=list)
    probe_runs: list[RunResult] = field(default_factory=list)
    declared_modes: set[FailureMode] = field(default_factory=set)
    observed_modes: set[FailureMode] = field(default_factory=set)
    deterministic: bool = True
    ungradable: list[str] = field(default_factory=list)
    #: Modos de falha declarados por tarefa — usado para saber onde cada sonda ataca.
    task_modes: dict[str, tuple[FailureMode, ...]] = field(default_factory=dict)

    # -- metricas -------------------------------------------------------------------
    @property
    def gold_acceptance(self) -> float:
        return self.gold_accepted / self.gold_total if self.gold_total else 0.0

    @property
    def counterexample_rejection(self) -> float:
        if not self.counterexamples:
            return 0.0
        return sum(1 for c in self.counterexamples if c.rejected) / len(self.counterexamples)

    @property
    def label_precision(self) -> float:
        if not self.counterexamples:
            return 0.0
        return sum(1 for c in self.counterexamples if c.labeled) / len(self.counterexamples)

    @property
    def oracle_score(self) -> float:
        for r in self.probe_runs:
            if r.respondent_id == "oraculo":
                return r.score
        return 0.0

    @property
    def degenerate_scores(self) -> dict[str, float]:
        return {r.respondent_id: r.score for r in self.probe_runs if r.respondent_id != "oraculo"}

    @property
    def discrimination_margin(self) -> float:
        outros = self.degenerate_scores
        return self.oracle_score - max(outros.values()) if outros else 0.0

    @property
    def discriminates(self) -> bool:
        return self.discrimination_margin >= MIN_DISCRIMINATION_MARGIN

    def probe_sensitivity(self) -> list[dict[str, Any]]:
        """Quanto o escore cai **no subconjunto onde a falha foi injetada**.

        Diagnostico, nao criterio. O falsificador `F3` foi declarado sobre a margem agregada
        antes da execucao e permanece exatamente como estava — trocar a metrica depois de ver o
        resultado seria ajustar o instrumento ao resultado, a manobra que o `D-008` do Silicon
        Atlas existe para proibir. O que esta medida faz e **explicar** o valor agregado.

        Duas tentativas anteriores de decompor a margem falharam pelo mesmo motivo, e vale
        registrar: comparar o oraculo com a *melhor* sonda dentro de uma capacidade da sempre
        zero, porque para toda capacidade existe alguma sonda que nao a ataca. A comparacao que
        informa e a de cada sonda contra o oraculo **no alvo que ela mesma declarou atacar**.

        Se esta decomposicao virar criterio, sera declarada antes do ciclo C-003, com limiar
        proprio e sem olhar o resultado antes.
        """
        alvos = {p.id: modos for p, modos in PROBES}
        por_tarefa = {
            g.task_id: set(self.task_modes.get(g.task_id, ()))
            for r in self.probe_runs
            for g in r.grades
        }
        oraculo = next((r for r in self.probe_runs if r.respondent_id == "oraculo"), None)
        out: list[dict[str, Any]] = []
        for r in self.probe_runs:
            modos = alvos.get(r.respondent_id, ())
            if not modos or oraculo is None:
                continue
            alvo_ids = {t for t, ms in por_tarefa.items() if ms & set(modos)}
            if not alvo_ids:
                continue
            sel = [g for g in r.grades if g.task_id in alvo_ids]
            ref = [g for g in oraculo.grades if g.task_id in alvo_ids]
            escore = sum(1 for g in sel if g.passed) / len(sel)
            escore_ref = sum(1 for g in ref if g.passed) / len(ref)
            out.append(
                {
                    "sonda": r.respondent_id,
                    "alvo": [str(m) for m in modos],
                    "tarefas_no_alvo": len(alvo_ids),
                    "fracao_do_corpus": round(len(alvo_ids) / self.tasks, 4) if self.tasks else 0.0,
                    "queda_no_alvo": round(escore_ref - escore, 4),
                    "queda_agregada": round(self.oracle_score - r.score, 4),
                }
            )
        return sorted(out, key=lambda d: -d["queda_no_alvo"])

    @property
    def dead_modes(self) -> list[FailureMode]:
        return sorted(self.declared_modes - self.observed_modes, key=str)

    @property
    def thin_capabilities(self) -> list[str]:
        return sorted(c for c, n in self.coverage.items() if n < MIN_TASKS_PER_CAPABILITY)

    # -- falsificadores -------------------------------------------------------------
    def falsifiers(self) -> dict[str, dict[str, Any]]:
        """Criterios de falha do ciclo C-002, declarados na PROBLEM_CHARTER antes da execucao."""
        return {
            "F1": {
                "criterio": "o grader aceita alguma trajetoria declarada como errada",
                "disparado": self.counterexample_rejection < 1.0,
                "medido": round(self.counterexample_rejection, 4),
            },
            "F2": {
                "criterio": "o grader rejeita a trajetoria de referencia de alguma tarefa",
                "disparado": self.gold_acceptance < 1.0,
                "medido": round(self.gold_acceptance, 4),
            },
            "F3": {
                "criterio": (
                    f"o escore separa o oraculo da melhor sonda degenerada por menos de "
                    f"{MIN_DISCRIMINATION_MARGIN:.2f}"
                ),
                "disparado": not self.discriminates,
                "medido": round(self.discrimination_margin, 4),
            },
            "F4": {
                "criterio": "duas execucoes da mesma suite produzem resultados diferentes",
                "disparado": not self.deterministic,
                "medido": self.deterministic,
            },
            "F5": {
                "criterio": (
                    f"alguma tarefa nao e avaliavel, ou alguma capacidade tem menos de "
                    f"{MIN_TASKS_PER_CAPABILITY} tarefas"
                ),
                "disparado": bool(self.ungradable) or bool(self.thin_capabilities),
                "medido": {
                    "sem_grader": self.ungradable,
                    "cobertura_fina": self.thin_capabilities,
                },
            },
            "F6": {
                "criterio": "algum modo de falha declarado nunca e disparado por nenhuma sonda",
                "disparado": bool(self.dead_modes),
                "medido": [str(m) for m in self.dead_modes],
            },
        }

    # -- findings -------------------------------------------------------------------
    def findings(self) -> FindingSet:
        """Resultados sobre o instrumento.

        Sao `COMPUTATIONAL_EVIDENCE` sem lacuna: nao dependem de premissa sobre o mundo, so de
        codigo e corpus que estao no repositorio e reexecutam identicos. E o unico lugar deste
        ciclo onde isso e verdade — tudo que fala de modelo carrega `G-101`.
        """
        fs = FindingSet("instrumento BR-Agent-Bench")
        fs.add(Finding("tarefas_no_corpus", self.tasks, Status.OBSERVATION, unit="tarefas"))
        fs.add(
            Finding(
                "aceitacao_do_gabarito",
                round(self.gold_acceptance, 4),
                Status.COMPUTATIONAL_EVIDENCE,
                note=f"{self.gold_accepted}/{self.gold_total} trajetorias de referencia aprovadas",
            )
        )
        fs.add(
            Finding(
                "rejeicao_de_contraexemplo",
                round(self.counterexample_rejection, 4),
                Status.COMPUTATIONAL_EVIDENCE,
                note=f"{len(self.counterexamples)} contraexemplos declarados no corpus",
            )
        )
        fs.add(
            Finding(
                "precisao_do_rotulo",
                round(self.label_precision, 4),
                Status.COMPUTATIONAL_EVIDENCE,
                note="fracao dos contraexemplos rejeitados com o modo de falha correto",
            )
        )
        margem = Finding(
            "margem_de_discriminacao",
            round(self.discrimination_margin, 4),
            Status.COMPUTATIONAL_EVIDENCE,
            note=(
                f"oraculo {self.oracle_score:.3f} contra melhor sonda degenerada "
                f"{max(self.degenerate_scores.values(), default=0.0):.3f}"
            ),
        )
        fs.add(margem)
        fs.add(
            derive(
                "instrumento_discrimina",
                self.discriminates,
                [margem],
                note=f"limiar {MIN_DISCRIMINATION_MARGIN} sem base empirica (G-105)",
                extra_gaps=("G-105",),
            )
        )
        sens = self.probe_sensitivity()
        fs.add(
            Finding(
                "queda_no_alvo_minima",
                round(min((d["queda_no_alvo"] for d in sens), default=0.0), 4),
                Status.COMPUTATIONAL_EVIDENCE,
                note=(
                    "menor queda de escore no subconjunto que a sonda declarou atacar; "
                    "diagnostico de CE-101, nao criterio — F3 segue declarado sobre a margem "
                    "agregada"
                ),
            )
        )
        fs.add(
            Finding(
                "modos_de_falha_sem_sonda",
                [str(m) for m in self.dead_modes],
                Status.COMPUTATIONAL_EVIDENCE,
                note="modo declarado no corpus que nenhuma sonda consegue provocar",
            )
        )
        return fs


# --------------------------------------------------------------------------------------


def evaluate_instrument(tasks: TaskSet, *, check_determinism: bool = True) -> InstrumentReport:
    """Roda a bateria completa de verificacao do instrumento."""
    ungradable: list[str] = []
    for t in tasks:
        try:
            validate_rules(t)
        except UnknownRule as exc:
            ungradable.append(f"{t.id}: {exc}")

    rep = InstrumentReport(
        tasks=len(tasks),
        coverage=tasks.coverage(),
        gold_accepted=0,
        gold_total=len(tasks),
        declared_modes=tasks.declared_failure_modes(),
        ungradable=ungradable,
        task_modes={t.id: t.failure_modes for t in tasks},
    )

    # 1 — o gabarito passa no proprio criterio
    from .runner import OracleRespondent, run_task

    oraculo = OracleRespondent()
    for t in tasks:
        if grade(t, run_task(t, oraculo)).passed:
            rep.gold_accepted += 1

    # 2 — cada contraexemplo e rejeitado, e pelo motivo declarado
    for t in tasks:
        for ce in t.counterexamples:
            esperado = FailureMode(ce["expect_failure"])
            g = grade(t, counterexample_trajectory(ce))
            rep.counterexamples.append(
                CounterexampleCheck(
                    task_id=t.id,
                    label=str(ce.get("label", "")),
                    expected=esperado,
                    rejected=not g.passed,
                    labeled=esperado in g.failures,
                    observed=g.failures,
                )
            )

    # 3 — sondas: escore e cobertura da taxonomia
    for probe, _ in PROBES:
        r = run_suite(tasks, probe)
        rep.probe_runs.append(r)
        rep.observed_modes |= r.observed_modes()

    # 4 — determinismo: a mesma suite duas vezes
    if check_determinism:
        for probe, _ in PROBES:
            a = run_suite(tasks, probe)
            b = run_suite(tasks, probe)
            if [g.as_dict() for g in a.grades] != [g.as_dict() for g in b.grades]:
                rep.deterministic = False
                break

    return rep


def probe_expectations(tasks: TaskSet) -> list[dict[str, Any]]:
    """Confronta cada sonda com o modo de falha que ela **prometeu** disparar.

    A promessa esta em `runner.PROBES` e foi escrita antes da execucao. Uma sonda que nao
    cumpre a promessa nao e uma sonda ruim: e a evidencia de que o grader nao ve aquele modo.
    """
    out = []
    for probe, esperados in PROBES:
        r = run_suite(tasks, probe)
        vistos = r.observed_modes()
        out.append(
            {
                "sonda": probe.id,
                "escore": round(r.score, 4),
                "prometido": [str(m) for m in esperados],
                "cumpriu": all(m in vistos for m in esperados),
                "observado": sorted(str(m) for m in vistos),
            }
        )
    return out


__all__ = [
    "InstrumentReport",
    "CounterexampleCheck",
    "evaluate_instrument",
    "probe_expectations",
    "MIN_TASKS_PER_CAPABILITY",
    "MIN_DISCRIMINATION_MARGIN",
]
