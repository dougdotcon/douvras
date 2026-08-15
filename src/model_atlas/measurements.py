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
from pathlib import Path
from typing import Any

from douvras_core.paths import project_root

from .graders import GradeResult
from .runner import RunResult
from .tasks import Capability, FailureMode

RUNS_DIR = project_root("model-atlas") / "99_RELEASES" / "runs"


class MeasurementError(ValueError):
    """Artefato de medicao malformado ou sem proveniencia suficiente para ser interpretado."""


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
    telemetry: dict[str, Any] = field(default_factory=dict)
    grades: list[GradeResult] = field(default_factory=list)
    note: str = ""

    @property
    def diagnostic(self) -> bool:
        """Execucao em modo diagnostico nao publica capacidade (ver `G-112`)."""
        return self.fewshot

    @classmethod
    def load(cls, model_id: str, directory: Path | None = None) -> "Measurement | None":
        """A medicao publicavel mais recente do modelo, ou `None`.

        Execucoes em modo diagnostico sao ignoradas aqui — elas existem para interpretar o
        escore, nao para virar escore. O filtro le o campo `fewshot` do proprio artefato, e nao
        o nome do arquivo: nome e convencao, campo e declaracao.
        """
        d = Path(directory or RUNS_DIR)
        if not d.is_dir():
            return None
        candidatos = []
        for f in sorted(d.glob("RUN-*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            if doc.get("model_id") == model_id and not doc.get("fewshot"):
                candidatos.append(doc)
        return cls.from_doc(candidatos[-1]) if candidatos else None

    @classmethod
    def load_diagnostic(cls, model_id: str, directory: Path | None = None) -> "Measurement | None":
        """A execucao em modo diagnostico do modelo, se houver.

        Ela nunca vira escore publicado; serve para dizer o que o escore publicado **nao**
        estava medindo. Sem isso, um zero fica indistinguivel de um zero por elicitacao ruim.
        """
        d = Path(directory or RUNS_DIR)
        if not d.is_dir():
            return None
        for f in sorted(d.glob("RUN-*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            if doc.get("model_id") == model_id and doc.get("fewshot"):
                return cls.from_doc(doc)
        return None

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
            "fewshot": self.fewshot,
            "tasks": self.tasks,
            "tool_calls": self.tool_calls,
            "max_steps": self.max_steps,
            "wall_s": self.wall_s,
            "telemetry": self.telemetry,
        }


def available(directory: Path | None = None) -> list[str]:
    """Modelos com medicao publicavel. Le o campo, nao o nome do arquivo."""
    d = Path(directory or RUNS_DIR)
    if not d.is_dir():
        return []
    ids = set()
    for f in d.glob("RUN-*.json"):
        doc = json.loads(f.read_text(encoding="utf-8"))
        if not doc.get("fewshot"):
            ids.add(str(doc.get("model_id", "")))
    return sorted(i for i in ids if i)


__all__ = ["Measurement", "MeasurementError", "RUNS_DIR", "available"]
