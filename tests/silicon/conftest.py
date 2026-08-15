"""Fixtures compartilhadas.

A mais importante e `nondegenerate_partition`: sem ela, todo o caminho economico do Atlas ficava
sem teste. Como o corpus real nunca produz regiao fixa nao-vazia sob a politica vigente, os
testes de particao e economia rodavam sobre `hardened_share = 0` e passavam com qualquer formula
— inclusive com o teto de Amdahl invertido. Ver retratacao R-002.
"""

from __future__ import annotations

import pytest

from silicon_atlas.hardware import get_device
from silicon_atlas.ir import build_graph
from silicon_atlas.ir.graph import OpKind
from silicon_atlas.profiler import serving_profile
from silicon_atlas.readiness import HardeningCandidate, ScoreCard, Weights
from silicon_atlas.registry import Registry
from douvras_core.status import Finding, Status


@pytest.fixture(scope="session")
def registry() -> Registry:
    return Registry.load()


@pytest.fixture(scope="session")
def device():
    return get_device("h100-sxm")


def make_candidate(
    role: str,
    *,
    cost_share: float,
    E: float = 0.9,
    F: float | None = None,
    R: float = 1.0,
    Q: float = 0.9,
    V: float = 0.7,
    M: float = 1.0,
    L: float = 0.8,
    precision: str = "int8",
    weight_elems: int = 0,
    kind: str = "linear",
    block_role: str = "mlp",
) -> HardeningCandidate:
    """Candidato sintetico com fatores escolhidos, para exercitar o ramo nao-degenerado."""
    factors = {
        k: Finding(f"{k}.{role}", v, Status.COMPUTATIONAL_EVIDENCE, unit="[0,1]")
        for k, v in (
            ("E", E), ("F", cost_share if F is None else F), ("R", R),
            ("Q", Q), ("V", V), ("M", M), ("L", L),
        )
    }
    return HardeningCandidate(
        role=role,
        block_role=block_role,
        instances_per_token=32,
        cost_share=cost_share,
        scorecard=ScoreCard(name=role, kind="LHS", factors=factors, weights=Weights.load().lhs),
        precision=precision,
        weight_elems=weight_elems,
        kind=kind,
    )


@pytest.fixture
def nondegenerate_partition(registry: Registry, device):
    """Particao com 70 % do custo endurecido, construida a partir de pesos reais do grafo.

    Os pesos vem do modelo real para que `build_design_point` produza `hardened_weight_bits > 0`
    e o simulador percorra o caminho completo.
    """
    from silicon_atlas.partition import partition

    spec = registry["llama-3.1-8b"]
    graph = build_graph(spec)
    elems = {}
    for n in graph:
        if n.kind is OpKind.LINEAR:
            elems[n.role] = elems.get(n.role, 0) + n.weight_elems

    cands = [
        make_candidate("gate_proj", cost_share=0.30, weight_elems=elems.get("gate_proj", 0)),
        make_candidate("up_proj", cost_share=0.25, weight_elems=elems.get("up_proj", 0)),
        make_candidate("down_proj", cost_share=0.15, weight_elems=elems.get("down_proj", 0)),
        # Irregular por enderecamento dependente de dado, e nao esta na lista de papeis
        # programaveis da politica: cai em logica reconfiguravel.
        make_candidate("operador_emergente", cost_share=0.20, R=0.5, M=0.4, Q=0.7, E=0.7,
                       block_role="mlp"),
        # Papel de politica de runtime: sempre programavel, por regra explicita.
        make_candidate("sampling", cost_share=0.10, R=0.0, M=1.0, Q=0.0, E=0.1,
                       block_role="head", kind="sampling"),
    ]
    part = partition(cands, model_id=spec.id, phase_label="teste")
    sp = serving_profile(graph, device, prompt_len=2048, gen_len=512)
    return spec, graph, part, sp, cands
