"""Vocabulario do BR-Agent-Bench: capacidade, modo de falha, tarefa, ambiente, trajetoria.

Uma tarefa de avaliacao de agente nao e um par pergunta/resposta. Ela e:

    ambiente deterministico + objetivo + ferramentas + regra de acerto + modos de falha

O ambiente e **executado**, nao descrito. Isso importa mais do que parece: se as observacoes
fossem escritas junto com a trajetoria, um respondente que inventa o saldo e um que consulta o
saldo produziriam o mesmo registro, e a alucinacao — o modo de falha mais caro em agentes —
seria invisivel para o grader. Aqui o ambiente responde, e qualquer numero que apareca na
resposta sem ter saido dele e alucinacao detectavel.

O ambiente e puro: mesma tarefa, mesma sequencia de chamadas, mesmas observacoes, sempre.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from douvras_core.paths import project_root


class Capability(StrEnum):
    """As capacidades que o benchmark separa.

    Separadas porque **falham separadamente**: um modelo pode escolher a ferramenta certa e
    errar o argumento, ou acertar os dois e nao se recuperar de um HTTP 500. Media unica sobre
    tudo isso e o numero que esconde a informacao acionavel.
    """

    TOOL_SELECTION = "tool_selection"
    ARGUMENTS = "arguments"
    STRUCTURED_OUTPUT = "structured_output"
    PLANNING = "planning"
    ERROR_RECOVERY = "error_recovery"
    HALLUCINATION = "hallucination"
    PT_BR_NUMERACY = "pt_br_numeracy"
    SAFETY_REFUSAL = "safety_refusal"


class FailureMode(StrEnum):
    """Taxonomia de falhas (Documento 1, Semana 2).

    Cada modo precisa ser **detectavel por alguem**: um modo que nenhum respondente do corpus
    consegue disparar e celula morta na taxonomia, e o falsificador F6 do ciclo C-002 existe
    exatamente para acusar isso.
    """

    FAIL_TOOL_SELECTION = "FAIL_TOOL_SELECTION"
    FAIL_ARGUMENT = "FAIL_ARGUMENT"
    FAIL_FORMAT = "FAIL_FORMAT"
    FAIL_PLANNING = "FAIL_PLANNING"
    FAIL_RECOVERY = "FAIL_RECOVERY"
    FAIL_HALLUCINATION = "FAIL_HALLUCINATION"
    FAIL_SAFETY = "FAIL_SAFETY"
    FAIL_NO_ANSWER = "FAIL_NO_ANSWER"


# --------------------------------------------------------------------------------------
# Trajetoria
# --------------------------------------------------------------------------------------


class StepKind(StrEnum):
    CALL = "call"
    ANSWER = "answer"
    ASK = "ask"
    GIVE_UP = "give_up"


@dataclass(frozen=True)
class Step:
    """Um passo da trajetoria. `observation` e preenchida pelo ambiente, nunca pelo respondente."""

    kind: StepKind
    tool: str = ""
    args: Mapping[str, Any] = field(default_factory=dict)
    text: str = ""
    observation: Any = None
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": str(self.kind)}
        if self.tool:
            out["tool"] = self.tool
        if self.args:
            out["args"] = dict(self.args)
        if self.text:
            out["text"] = self.text
        if self.observation is not None:
            out["observation"] = self.observation
        if self.error:
            out["error"] = self.error
        return out


Trajectory = tuple[Step, ...]


# --------------------------------------------------------------------------------------
# Ambiente deterministico
# --------------------------------------------------------------------------------------


class EnvironmentError_(RuntimeError):
    """Chamada malformada contra o ambiente. Nao e falha do agente: e falha da tarefa."""


@dataclass
class Environment:
    """Interpretador puro do ambiente declarado na tarefa.

    Tipos de ferramenta suportados — deliberadamente poucos, porque cada tipo novo e uma
    forma nova de a tarefa mentir sobre o que testa:

    ``read``    devolve um campo do estado
    ``lookup``  devolve um valor de uma tabela indexada por um argumento
    ``debit``   subtrai um argumento de um campo do estado; recusa se ficar negativo
    ``write``   grava um argumento em um campo do estado
    ``ack``     confirma sem efeito observavel
    ``error``   falha com o erro declarado; `recover_after` N chamadas passa a funcionar
    """

    state: dict[str, Any]
    tools: dict[str, dict[str, Any]]
    calls: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_spec(cls, spec: Mapping[str, Any]) -> "Environment":
        return cls(
            state=dict(spec.get("state") or {}),
            tools={k: dict(v) for k, v in (spec.get("tools") or {}).items()},
        )

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(self.tools)

    def observed_values(self) -> list[float]:
        """Todo numero que o ambiente ja devolveu nesta execucao.

        E o conjunto contra o qual a alucinacao numerica e verificada.
        """
        return list(self._observed)

    def __post_init__(self) -> None:
        self._observed: list[float] = []

    def _record(self, value: Any) -> Any:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self._observed.append(float(value))
        elif isinstance(value, Mapping):
            for v in value.values():
                self._record(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                self._record(v)
        return value

    def call(self, tool: str, args: Mapping[str, Any]) -> tuple[Any, str]:
        """Executa uma chamada. Devolve ``(observacao, erro)``; erro vazio significa sucesso.

        Chamar ferramenta inexistente **nao** e erro de ambiente: e o comportamento que a
        tarefa quer flagrar. Devolve erro declarado para que o grader o classifique.
        """
        if tool not in self.tools:
            return None, f"ferramenta inexistente: {tool}"
        spec = self.tools[tool]
        self.calls[tool] = self.calls.get(tool, 0) + 1
        kind = spec.get("kind", "ack")

        if kind == "error":
            # `recover_after: N` falha nas N primeiras chamadas e funciona da N+1 em diante —
            # e o que torna "tentar de novo" uma estrategia distinguivel de "insistir sempre".
            # Ausente ou zero: falha sempre, e a unica saida correta e desistir explicitamente.
            recover_after = int(spec.get("recover_after", 0) or 0)
            if recover_after == 0 or self.calls[tool] <= recover_after:
                return None, str(spec.get("error", "erro nao especificado"))
            kind = str(spec.get("then", "ack"))

        if kind == "read":
            return self._record(self.state.get(spec["field"])), ""
        if kind == "lookup":
            table = spec.get("table") or {}
            key = str(args.get(spec.get("arg", "key"), ""))
            if key not in table:
                return None, f"chave nao encontrada: {key}"
            return self._record(table[key]), ""
        if kind == "debit":
            field_name = spec["field"]
            arg_name = spec.get("arg", "valor")
            try:
                valor = float(args[arg_name])
            except (KeyError, TypeError, ValueError):
                return None, f"argumento ausente ou invalido: {arg_name}"
            saldo = float(self.state.get(field_name, 0.0))
            if spec.get("refuse_if_insufficient", True) and valor > saldo + 1e-9:
                return None, "saldo insuficiente"
            self.state[field_name] = round(saldo - valor, 2)
            return self._record({"ok": True, field_name: self.state[field_name]}), ""
        if kind == "write":
            self.state[spec["field"]] = args.get(spec.get("arg", "value"))
            return {"ok": True}, ""
        if kind == "ack":
            return {"ok": True}, ""
        raise EnvironmentError_(f"tipo de ferramenta desconhecido: {kind!r}")


# --------------------------------------------------------------------------------------
# Tarefa
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalTask:
    """Uma tarefa registrada do BR-Agent-Bench.

    `rules` e o contrato de acerto avaliado por `graders.grade`. `counterexamples` sao
    trajetorias *sabidamente erradas*, cada uma rotulada com o modo de falha que exibe: sao
    elas que permitem medir se o grader mede o que diz medir, sem executar nenhum modelo.
    """

    id: str
    capability: Capability
    difficulty: int
    language: str
    prompt: str
    tools: tuple[str, ...]
    environment: Mapping[str, Any]
    rules: Mapping[str, Any]
    failure_modes: tuple[FailureMode, ...]
    gold: tuple[Mapping[str, Any], ...]
    counterexamples: tuple[Mapping[str, Any], ...] = ()
    note: str = ""

    def env(self) -> Environment:
        return Environment.from_spec(self.environment)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "capability": str(self.capability),
            "difficulty": self.difficulty,
            "language": self.language,
            "tools": list(self.tools),
            "failure_modes": [str(f) for f in self.failure_modes],
            "counterexamples": len(self.counterexamples),
        }


class TaskCorpusError(ValueError):
    """Tarefa malformada. O corpus e entrada: um erro aqui e erro de autoria, nao de execucao."""


def _parse_task(doc: Mapping[str, Any], source: Path) -> EvalTask:
    try:
        cap = Capability(doc["capability"])
    except (KeyError, ValueError) as exc:
        raise TaskCorpusError(f"{source.name}: capacidade invalida ({exc})") from exc
    try:
        modes = tuple(FailureMode(m) for m in doc.get("failure_modes", ()))
    except ValueError as exc:
        raise TaskCorpusError(f"{source.name}: modo de falha invalido ({exc})") from exc
    if not doc.get("gold"):
        raise TaskCorpusError(f"{source.name}: tarefa sem trajetoria de referencia")
    if not doc.get("rules"):
        raise TaskCorpusError(f"{source.name}: tarefa sem regra de acerto — nao e avaliavel")
    return EvalTask(
        id=str(doc["id"]),
        capability=cap,
        difficulty=int(doc.get("difficulty", 1)),
        language=str(doc.get("language", "pt-BR")),
        prompt=str(doc.get("prompt", "")),
        tools=tuple(doc.get("tools", ())),
        environment=doc.get("environment", {}),
        rules=doc["rules"],
        failure_modes=modes,
        gold=tuple(doc["gold"]),
        counterexamples=tuple(doc.get("counterexamples", ())),
        note=str(doc.get("note", "")),
    )


TASKS_DIR = project_root("model-atlas") / "corpus" / "tasks"


class TaskSet:
    """O corpus de tarefas carregado, com as consultas que o ciclo precisa."""

    def __init__(self, tasks: Sequence[EvalTask]):
        self.tasks = list(tasks)

    @classmethod
    def load(cls, directory: Path | None = None) -> "TaskSet":
        d = Path(directory or TASKS_DIR)
        out: list[EvalTask] = []
        for f in sorted(d.glob("*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            items = doc if isinstance(doc, list) else [doc]
            out.extend(_parse_task(t, f) for t in items)
        ids = [t.id for t in out]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise TaskCorpusError(f"ids duplicados no corpus: {sorted(dup)}")
        return cls(out)

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self) -> Iterator[EvalTask]:
        return iter(self.tasks)

    def __getitem__(self, task_id: str) -> EvalTask:
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise KeyError(task_id)

    def by_capability(self) -> dict[Capability, list[EvalTask]]:
        out: dict[Capability, list[EvalTask]] = {}
        for t in self.tasks:
            out.setdefault(t.capability, []).append(t)
        return dict(sorted(out.items(), key=lambda kv: str(kv[0])))

    def coverage(self) -> dict[str, int]:
        return {str(k): len(v) for k, v in self.by_capability().items()}

    def declared_failure_modes(self) -> set[FailureMode]:
        return {m for t in self.tasks for m in t.failure_modes}


__all__ = [
    "Capability",
    "FailureMode",
    "StepKind",
    "Step",
    "Trajectory",
    "Environment",
    "EvalTask",
    "TaskSet",
    "TaskCorpusError",
    "TASKS_DIR",
]
