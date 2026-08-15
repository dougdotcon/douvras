"""DOUVRAS Silicon Atlas.

Plataforma de descoberta e codesign que determina quais partes de um modelo de IA ja estao
estaveis, dominantes em custo e tolerantes a baixa precisao o bastante para virar silicio.

Construida sob o Metodo DOUVRAS: nenhuma afirmacao sem status, nenhum resultado mais forte
que sua dependencia mais fraca, nenhum experimento sem criterio de falha declarado antes.

Desde o ciclo C-002 o contrato epistemico vive em `douvras_core` e e compartilhado com o
Model Atlas (ADR-0005). O que resta aqui e a fisica do problema de silicio: IR analitica,
roofline, invariantes estruturais, particionamento e economia.
"""

from douvras_core.status import (
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
__cycle__ = "C-001"

__all__ = [
    "Status",
    "StatusViolation",
    "Finding",
    "FindingSet",
    "Claim",
    "ClaimLedger",
    "DECISION_FLOOR",
    "derive",
    "assumed",
    "measured",
    "modeled",
    "lint_text",
    "__version__",
]
