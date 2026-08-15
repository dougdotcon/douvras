"""Execucao de uma suite: respondentes, ambiente e o registro do que aconteceu.

O respondente propoe um passo; o **ambiente** decide o que ele observa. Essa separacao e o
que impede o benchmark de medir eloquencia: nenhum respondente escreve a propria observacao.

## Respondentes sinteticos nao sao modelos

Os respondentes deste modulo sao *sondas de calibracao do instrumento*. Cada um encarna um
modo de falha arquetipico e existe para responder a uma pergunta que nao precisa de GPU:

> o grader detecta esta falha quando ela acontece, e so quando ela acontece?

Um numero produzido por eles e evidencia sobre **o instrumento**, jamais sobre um modelo. O
tipo carrega isso: `Respondent.synthetic` e verdadeiro, e `capability.py` recusa emitir
capacidade medida a partir de execucao sintetica — devolve ausencia declarada e a lacuna
`G-101`. Confundir as duas coisas seria publicar um leaderboard de ficcao, que e exatamente o
que o Metodo existe para tornar impossivel.

O backend real vive em `backends.py` e exige o extra `[run]`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable

from .graders import GradeResult, grade, parse_br_numbers
from .tasks import Capability, EvalTask, FailureMode, Step, StepKind, TaskSet, Trajectory

#: Teto de passos por tarefa. Um agente que nao converge em 16 passos falhou de outra forma.
MAX_STEPS = 16


@runtime_checkable
class Respondent(Protocol):
    """Politica que propoe o proximo passo dado o historico ja observado."""

    id: str
    synthetic: bool

    def act(self, task: EvalTask, history: Sequence[Step]) -> Step: ...


# --------------------------------------------------------------------------------------
# Execucao
# --------------------------------------------------------------------------------------


def run_task(task: EvalTask, respondent: Respondent, max_steps: int = MAX_STEPS) -> Trajectory:
    """Executa uma tarefa. O ambiente preenche `observation` e `error` de cada chamada."""
    env = task.env()
    hist: list[Step] = []
    for _ in range(max_steps):
        step = respondent.act(task, hist)
        if step.kind is StepKind.CALL:
            obs, err = env.call(step.tool, step.args)
            step = replace(step, observation=obs, error=err)
        hist.append(step)
        if step.kind in (StepKind.ANSWER, StepKind.GIVE_UP):
            break
    return tuple(hist)


@dataclass
class RunResult:
    """Resultado de uma suite inteira contra um respondente."""

    respondent_id: str
    synthetic: bool
    grades: list[GradeResult] = field(default_factory=list)
    trajectories: dict[str, Trajectory] = field(default_factory=dict)

    @property
    def score(self) -> float:
        return sum(1 for g in self.grades if g.passed) / len(self.grades) if self.grades else 0.0

    def score_by_capability(self) -> dict[Capability, float]:
        buckets: dict[Capability, list[bool]] = {}
        for g in self.grades:
            buckets.setdefault(g.capability, []).append(g.passed)
        return {
            c: sum(v) / len(v)
            for c, v in sorted(buckets.items(), key=lambda kv: str(kv[0]))
        }

    def failure_counts(self) -> dict[FailureMode, int]:
        out: dict[FailureMode, int] = {}
        for g in self.grades:
            for f in g.failures:
                out[f] = out.get(f, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def observed_modes(self) -> set[FailureMode]:
        return {f for g in self.grades for f in g.failures}

    def as_dict(self) -> dict[str, Any]:
        return {
            "respondent": self.respondent_id,
            "synthetic": self.synthetic,
            "tasks": len(self.grades),
            "score": round(self.score, 4),
            "by_capability": {str(k): round(v, 4) for k, v in self.score_by_capability().items()},
            "failures": {str(k): v for k, v in self.failure_counts().items()},
        }


def run_suite(tasks: TaskSet | Iterable[EvalTask], respondent: Respondent) -> RunResult:
    res = RunResult(respondent_id=respondent.id, synthetic=respondent.synthetic)
    for t in tasks:
        traj = run_task(t, respondent)
        res.trajectories[t.id] = traj
        res.grades.append(grade(t, traj))
    return res


# --------------------------------------------------------------------------------------
# Sondas sinteticas
# --------------------------------------------------------------------------------------


def _gold_steps(task: EvalTask) -> list[Step]:
    out: list[Step] = []
    for raw in task.gold:
        out.append(
            Step(
                kind=StepKind(raw.get("kind", "call")),
                tool=str(raw.get("tool", "")),
                args=dict(raw.get("args") or {}),
                text=str(raw.get("text", "")),
            )
        )
    return out


def _invented_number(task: EvalTask) -> float:
    """Numero deterministico que nao aparece no enunciado nem sai do ambiente.

    Deslocamento fixo sobre o maior numero do enunciado: reprodutivel entre execucoes e
    distante o bastante da tolerancia do grader para nunca colidir por acidente.
    """
    base = max(parse_br_numbers(task.prompt), default=0.0)
    return round(base + 137.77, 2)


@dataclass
class _Replay:
    """Base das sondas: reproduz a trajetoria de referencia, com uma deformacao declarada."""

    id: str
    synthetic: bool = True

    def plan(self, task: EvalTask) -> list[Step]:  # pragma: no cover - sobrescrito
        return _gold_steps(task)

    def act(self, task: EvalTask, history: Sequence[Step]) -> Step:
        passos = self.plan(task)
        i = len(history)
        if i < len(passos):
            return passos[i]
        return Step(kind=StepKind.ANSWER, text="pronto")


class OracleRespondent(_Replay):
    """Executa exatamente a trajetoria de referencia. Serve de teto do instrumento."""

    def __init__(self) -> None:
        super().__init__(id="oraculo")


class DirectAnswerRespondent(_Replay):
    """Nunca usa ferramenta: responde de cabeca, com um numero inventado."""

    def __init__(self) -> None:
        super().__init__(id="resposta-direta")

    def plan(self, task: EvalTask) -> list[Step]:
        return [
            Step(
                kind=StepKind.ANSWER,
                text=f"O valor e R$ {_invented_number(task):.2f}.".replace(".", ","),
            )
        ]


class WrongToolRespondent(_Replay):
    """Escolhe outra ferramenta disponivel no lugar da correta."""

    def __init__(self) -> None:
        super().__init__(id="ferramenta-errada")

    def plan(self, task: EvalTask) -> list[Step]:
        alternativas = list(task.tools)
        out: list[Step] = []
        for s in _gold_steps(task):
            if s.kind is StepKind.CALL and len(alternativas) > 1:
                outra = next(t for t in alternativas if t != s.tool)
                out.append(replace(s, tool=outra))
            else:
                out.append(s)
        return out


class WrongArgumentRespondent(_Replay):
    """Ferramenta certa, argumento numerico deslocado."""

    def __init__(self) -> None:
        super().__init__(id="argumento-errado")

    def plan(self, task: EvalTask) -> list[Step]:
        out: list[Step] = []
        deformou = False
        for s in _gold_steps(task):
            if s.kind is StepKind.CALL and not deformou:
                novos = dict(s.args)
                for k, v in novos.items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        novos[k] = round(float(v) + 100.0, 2)
                        deformou = True
                        break
                out.append(replace(s, args=novos))
            else:
                out.append(s)
        return out


class BrokenJSONRespondent(_Replay):
    """Faz tudo certo e entrega a resposta final em JSON quebrado."""

    def __init__(self) -> None:
        super().__init__(id="json-quebrado")

    def plan(self, task: EvalTask) -> list[Step]:
        out = _gold_steps(task)
        if out and out[-1].kind is StepKind.ANSWER:
            out[-1] = replace(out[-1], text="{'chave': valor,,}")
        return out


class GivesUpOnErrorRespondent(_Replay):
    """Para na primeira observacao de erro e responde como se tivesse funcionado."""

    def __init__(self) -> None:
        super().__init__(id="desiste-no-erro")

    def act(self, task: EvalTask, history: Sequence[Step]) -> Step:
        if any(s.error for s in history):
            return Step(kind=StepKind.ANSWER, text="Concluido com sucesso.")
        return super().act(task, history)


class ImpulsiveRespondent(_Replay):
    """Nunca pergunta e nunca recusa: age sempre, com o que tem."""

    def __init__(self) -> None:
        super().__init__(id="impulsivo")

    def plan(self, task: EvalTask) -> list[Step]:
        passos = [s for s in _gold_steps(task) if s.kind is not StepKind.ASK]
        acoes = [s for s in passos if s.kind is StepKind.CALL]
        if not acoes and task.tools:
            acoes = [Step(kind=StepKind.CALL, tool=task.tools[0], args={})]
        return acoes + [Step(kind=StepKind.ANSWER, text="Feito.")]


class ShuffledPlanRespondent(_Replay):
    """Executa as chamadas certas na ordem errada."""

    def __init__(self) -> None:
        super().__init__(id="plano-invertido")

    def plan(self, task: EvalTask) -> list[Step]:
        passos = _gold_steps(task)
        chamadas = [s for s in passos if s.kind is StepKind.CALL]
        resto = [s for s in passos if s.kind is not StepKind.CALL]
        return list(reversed(chamadas)) + resto


#: As sondas do ciclo C-002, com o modo de falha que cada uma existe para provocar.
#: Este mapa e a **predicao declarada antes da execucao** (Metodo 6.1): se uma sonda nao
#: dispara o modo que promete, o instrumento nao detecta aquele modo — e o falsificador F6
#: dispara. E deliberado que nenhuma sonda prometa `FAIL_SAFETY` sozinha: a recusa depende de
#: a tarefa declarar `must_refuse`, e o impulsivo cobre esse caso quando ela declara.
PROBES: tuple[tuple[Respondent, tuple[FailureMode, ...]], ...] = (
    (OracleRespondent(), ()),
    (DirectAnswerRespondent(), (FailureMode.FAIL_TOOL_SELECTION,)),
    (WrongToolRespondent(), (FailureMode.FAIL_TOOL_SELECTION,)),
    (WrongArgumentRespondent(), (FailureMode.FAIL_ARGUMENT,)),
    (BrokenJSONRespondent(), (FailureMode.FAIL_FORMAT,)),
    (GivesUpOnErrorRespondent(), (FailureMode.FAIL_RECOVERY,)),
    (ImpulsiveRespondent(), (FailureMode.FAIL_PLANNING,)),
    (ShuffledPlanRespondent(), (FailureMode.FAIL_PLANNING,)),
)


def probe_respondents() -> list[Respondent]:
    return [p for p, _ in PROBES]


def counterexample_trajectory(raw: Mapping[str, Any]) -> Trajectory:
    """Converte um contraexemplo declarado no corpus em trajetoria executavel."""
    return tuple(
        Step(
            kind=StepKind(s.get("kind", "call")),
            tool=str(s.get("tool", "")),
            args=dict(s.get("args") or {}),
            text=str(s.get("text", "")),
            observation=s.get("observation"),
            error=str(s.get("error", "")),
        )
        for s in raw.get("steps", ())
    )


__all__ = [
    "Respondent",
    "RunResult",
    "run_task",
    "run_suite",
    "probe_respondents",
    "counterexample_trajectory",
    "PROBES",
    "MAX_STEPS",
    "OracleRespondent",
    "DirectAnswerRespondent",
    "WrongToolRespondent",
    "WrongArgumentRespondent",
    "BrokenJSONRespondent",
    "GivesUpOnErrorRespondent",
    "ImpulsiveRespondent",
    "ShuffledPlanRespondent",
]
