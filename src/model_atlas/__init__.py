"""DOUVRAS Model Atlas.

Descobre quais **capacidades** de um modelo pequeno estao presentes, sao mensuraveis e valem
ser especializadas por dados — e diz "ainda nao da para saber" quando nao ha medicao.

O eixo irmao do Silicon Atlas. Aquele pergunta que parte do modelo esta madura para virar
hardware; este pergunta o que o modelo sabe fazer antes de alguem gastar mascara ou GPU
descobrindo. Os dois compartilham `douvras_core`: a mesma escala de status, os mesmos portoes,
o mesmo portao de emissao.

Ordem de trabalho (Documento 1, secao 9): problema -> benchmark -> baseline -> analise de
falha -> dataset -> treino -> benchmark -> ablacao. O ciclo C-002 cobre do problema ao
instrumento verificado; do baseline em diante depende de pesos locais (`G-101`).
"""

from douvras_core.status import (
    Finding,
    FindingSet,
    Status,
    StatusViolation,
    derive,
)

__version__ = "0.1.0"
__method__ = "DOUVRAS 2.0"
__cycle__ = "C-002"

__all__ = [
    "Status",
    "StatusViolation",
    "Finding",
    "FindingSet",
    "derive",
    "__version__",
    "__cycle__",
]
