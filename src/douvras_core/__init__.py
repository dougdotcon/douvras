"""DOUVRAS Core — o contrato epistemico compartilhado pelos atlas.

Nao contem conhecimento de dominio. Contem a regra de que nenhum valor trafega sem status,
de que nenhuma conclusao e mais forte que sua dependencia mais fraca, de que um portao
verifica conteudo e nao caminho, e de que um relatorio fora do contrato nao e emitido.

Quem constroi um atlas novo sobre este core herda a disciplina inteira e escreve so a
fisica do seu proprio problema:

    from douvras_core import Finding, Status, derive
    from douvras_core.gates import Gate, summarize
    from douvras_core.paths import project_root
    from douvras_core.report import EmissionRefused, check_finite
"""

from .paths import PHASES, PROJECTS, REPO_ROOT, project_root
from .report import EmissionRefused
from .status import (
    DECISION_FLOOR,
    Claim,
    ClaimLedger,
    Finding,
    FindingSet,
    Status,
    StatusViolation,
    assumed,
    derive,
    lint_text,
    measured,
    modeled,
)

__version__ = "0.1.0"
__method__ = "DOUVRAS 2.0"

__all__ = [
    "Status",
    "StatusViolation",
    "Finding",
    "FindingSet",
    "Claim",
    "ClaimLedger",
    "DECISION_FLOOR",
    "EmissionRefused",
    "derive",
    "assumed",
    "measured",
    "modeled",
    "lint_text",
    "project_root",
    "REPO_ROOT",
    "PROJECTS",
    "PHASES",
    "__version__",
]
