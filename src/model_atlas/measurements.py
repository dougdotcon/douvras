"""Medicoes de execucao real, como evidencia versionada.

Executar um modelo e caro, externo e depende de maquina: exige pesos, runtime e uma hora de
CPU. Reexecutar isso a cada ciclo violaria o `ADR-0006` — o caminho principal roda sem GPU, sem
pesos e sem rede.

A saida disso e este modulo. A **execucao** acontece uma vez, fora do ciclo; o **resultado**
entra no repositorio como artefato declarado, com a proveniencia que o torna interpretavel:
qual arquivo de pesos, qual hash, qual quantizacao, qual versao de prompt, quanto tempo, quantos
tokens. Dai em diante o ciclo reemite o assessment offline, e qualquer pessoa reproduz o
relatorio sem baixar 1,5 GB.

Uma medicao sem `prompt_version` nao e comparavel com outra: sao instrumentos diferentes. Por
isso o campo e obrigatorio na leitura, nao opcional.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from douvras_core.paths import project_root

from .graders import GradeResult
from .runner import RunResult
from .tasks import Capability, FailureMode

RUNS_DIR = project_root("model-atlas") / "99_RELEASES" / "runs"


class MeasurementError(ValueError):
    """Artefato de medicao malformado ou sem proveniencia suficiente para ser interpretado."""


class MeasurementRole(str, Enum):
    """Para que serve esta execucao. Campo separado de `fewshot` **de proposito**.

    `fewshot` descreve o prompt: houve exemplo demonstrado ou nao. `role` declara a funcao:
    virar escore publicado ou limitar a leitura do escore publicado. Os dois coincidiram na
    primeira execucao diagnostica e a coincidencia virou atalho — uma execucao `/think`, que e
    diagnostica e zero-shot, chegou a ser gravada com `fewshot: true` so para nao virar escore.
    Rotulo errado em proveniencia e pior que artefato ausente, e o artefato foi removido; o
    conserto de verdade e este campo.
    """

    #: Vira capacidade publicada. Precisa cobrir o corpus inteiro.
    PRIMARY = "primary"
    #: Nunca vira capacidade. Existe para dizer o que o escore publicado **nao** mede.
    DIAGNOSTIC = "diagnostic"


@dataclass
class Measurement:
    """Uma execucao real, com o que e preciso para saber o que ela mede."""

    model_id: str
    prompt_version: str
    model_file: str
    quantization: str
    max_steps: int
    fewshot: bool
    tasks: int
    tool_calls: int
    wall_s: float
    #: Envelope de conversa usado (ver `backends.ConversationFormat`). Dois modelos so sao
    #: comparaveis com o envelope declarado: cada um so entende o formato que aprendeu.
    conversation_format: str = ""
    #: Mensagem de sistema efetiva. Em modelo de raciocinio hibrido isto decide se ele pensa
    #: antes de responder, e portanto decide boa parte do escore.
    system_mode: str = ""
    #: Publicavel ou diagnostica. Ver `MeasurementRole`.
    role: MeasurementRole = MeasurementRole.PRIMARY
    telemetry: dict[str, Any] = field(default_factory=dict)
    grades: list[GradeResult] = field(default_factory=list)
    note: str = ""

    @property
    def diagnostic(self) -> bool:
        return self.role is MeasurementRole.DIAGNOSTIC

    @staticmethod
    def _docs(model_id: str, directory: Path | None = None) -> list[dict[str, Any]]:
        d = Path(directory or RUNS_DIR)
        if not d.is_dir():
            return []
        achados = []
        for f in sorted(d.glob("RUN-*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            if doc.get("model_id") == model_id:
                achados.append(doc)
        return achados

    @classmethod
    def load(cls, model_id: str, directory: Path | None = None) -> "Measurement | None":
        """A medicao **publicavel** mais recente do modelo, ou `None`.

        O filtro le o campo do proprio artefato, nao o nome do arquivo: nome e convencao,
        campo e declaracao.
        """
        docs = [d for d in cls._docs(model_id, directory) if _papel(d) is MeasurementRole.PRIMARY]
        return cls.from_doc(docs[-1]) if docs else None

    @classmethod
    def diagnostics(cls, model_id: str, directory: Path | None = None) -> list["Measurement"]:
        """Execucoes diagnosticas do modelo, em ordem estavel.

        Nenhuma vira escore. Existem para dizer o que o escore publicado **nao** mede: sem
        elas, um zero fica indistinguivel de um zero por elicitacao ruim, e um numero colhido
        em modo reduzido fica indistinguivel do comportamento padrao do modelo.
        """
        return [
            cls.from_doc(d)
            for d in cls._docs(model_id, directory)
            if _papel(d) is MeasurementRole.DIAGNOSTIC
        ]

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "Measurement":
        for campo in ("model_id", "prompt_version", "model_file", "grades"):
            if campo not in doc:
                raise MeasurementError(f"medicao sem `{campo}`: nao e interpretavel")
        notas = [
            GradeResult(
                task_id=g["task"],
                capability=Capability(g["capability"]),
                passed=bool(g["passed"]),
                failures=tuple(FailureMode(f) for f in g.get("failures", ())),
                details=tuple(g.get("details", ())),
            )
            for g in doc["grades"]
        ]
        return cls(
            model_id=str(doc["model_id"]),
            prompt_version=str(doc["prompt_version"]),
            model_file=str(doc["model_file"]),
            quantization=str(doc.get("quantization", "")),
            max_steps=int(doc.get("max_steps", 0)),
            fewshot=bool(doc.get("fewshot", False)),
            tasks=int(doc.get("tasks", len(notas))),
            tool_calls=int(doc.get("tool_calls", 0)),
            wall_s=float(doc.get("wall_s", 0.0)),
            conversation_format=str(doc.get("conversation_format", "")),
            system_mode=str(doc.get("system_mode", "")),
            role=_papel(doc),
            telemetry=dict(doc.get("telemetry") or {}),
            grades=notas,
            note=str(doc.get("note", "")),
        )

    def to_run_result(self) -> RunResult:
        """Adapta para o mesmo tipo que as sondas produzem — `synthetic=False`.

        E este `False` que autoriza `CapabilityFingerprint` a emitir capacidade medida.
        """
        r = RunResult(respondent_id=self.model_id, synthetic=False)
        r.grades = list(self.grades)
        return r

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "model_file": self.model_file,
            "quantization": self.quantization,
            "conversation_format": self.conversation_format,
            "system_mode": self.system_mode,
            "role": str(self.role.value),
            "fewshot": self.fewshot,
            "tasks": self.tasks,
            "tool_calls": self.tool_calls,
            "max_steps": self.max_steps,
            "wall_s": self.wall_s,
            "telemetry": self.telemetry,
        }


def _papel(doc: dict[str, Any]) -> MeasurementRole:
    """Papel do artefato, com compatibilidade para os gravados antes do campo existir.

    Antes de `role`, `fewshot` fazia os dois trabalhos. Artefato sem `role` e lido pela regra
    antiga — o que preserva a leitura correta dos que ja estavam no repositorio.
    """
    bruto = doc.get("role")
    if bruto:
        return MeasurementRole(str(bruto))
    return MeasurementRole.DIAGNOSTIC if doc.get("fewshot") else MeasurementRole.PRIMARY


def available(directory: Path | None = None) -> list[str]:
    """Modelos com medicao publicavel. Le o campo, nao o nome do arquivo."""
    d = Path(directory or RUNS_DIR)
    if not d.is_dir():
        return []
    ids = set()
    for f in d.glob("RUN-*.json"):
        doc = json.loads(f.read_text(encoding="utf-8"))
        if _papel(doc) is MeasurementRole.PRIMARY:
            ids.add(str(doc.get("model_id", "")))
    return sorted(i for i in ids if i)


__all__ = [
    "Measurement",
    "MeasurementError",
    "MeasurementRole",
    "RUNS_DIR",
    "available",
]
