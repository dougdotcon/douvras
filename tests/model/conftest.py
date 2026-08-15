"""Fixtures do Model Atlas.

A mais importante é `fingerprint_medido`. Sem ela, todo o caminho de interpretação do Atlas —
déficit, candidatos, CSS, sensibilidade, alvo de dataset — nunca é executado sob teste, porque
o corpus real não tem pesos locais e portanto nunca produz capacidade medida.

É exatamente o `G-014` do Silicon Atlas, onde o caminho econômico inteiro atravessou um ciclo
com a suíte verde sem nunca ter rodado: substituir a fórmula do teto de Amdahl por uma errada
mantinha tudo passando. A fixture existe para que isso não se repita neste eixo.
"""

from __future__ import annotations

import pytest

from douvras_core.status import Status
from model_atlas.capability import CapabilityFingerprint
from model_atlas.css import Weights, load_priors
from model_atlas.registry import Registry
from model_atlas.tasks import Capability, TaskSet


@pytest.fixture(scope="session")
def tasks_corpus() -> TaskSet:
    return TaskSet.load()


@pytest.fixture(scope="session")
def registry() -> Registry:
    return Registry.load()


@pytest.fixture(scope="session")
def priors() -> dict:
    return load_priors()


@pytest.fixture(scope="session")
def pesos() -> Weights:
    return Weights.load()


@pytest.fixture
def fingerprint_medido() -> CapabilityFingerprint:
    """Fingerprint **medido** sintético, com déficits deliberadamente distintos.

    Os valores não representam nenhum modelo — representam o formato que uma execução real
    produziria. São escolhidos espalhados de propósito: um conjunto achatado faria os testes de
    discriminação do CSS passarem por falta de sinal em vez de por acerto.
    """
    from douvras_core.status import Finding

    escores = {
        Capability.STRUCTURED_OUTPUT: 0.95,
        Capability.TOOL_SELECTION: 0.83,
        Capability.PT_BR_NUMERACY: 0.79,
        Capability.ARGUMENTS: 0.71,
        Capability.SAFETY_REFUSAL: 0.58,
        Capability.ERROR_RECOVERY: 0.34,
        Capability.PLANNING: 0.29,
        Capability.HALLUCINATION: 0.18,
    }
    fp = CapabilityFingerprint(model_id="modelo-sintetico", measured=True, source="fixture")
    for cap, v in escores.items():
        fp.scores[cap] = Finding(f"capacidade.{cap}", v, Status.OBSERVATION)
    return fp
