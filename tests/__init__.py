"""Suites do monorepo DOUVRAS.

Pacotes de verdade (com `__init__.py`) porque os tres eixos tem arquivos de mesmo nome —
`test_assessment_gate.py` existe em `silicon` e em `model`, e os dois testam a mesma ideia
sobre motores diferentes. Sem pacote, o pytest colide na importacao.
"""
