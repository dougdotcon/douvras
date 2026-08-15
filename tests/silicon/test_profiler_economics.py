"""Profiler, quantizacao, particao e economia.

Testes de **regime** antes de testes de valor: o roofline nao foi calibrado (G-003), entao
afirmar "decode leva 6 ms" seria falso rigor. Afirmar "decode e memory-bound e prefill nao e"
e uma consequencia estrutural que o modelo pode sustentar, e que quebraria de forma visivel
se a aritmetica estivesse errada.
"""

from __future__ import annotations

import math

import pytest

from silicon_atlas.economics import (
    EconomicsPriors,
    build_design_point,
    gross_dies_per_wafer,
    murphy_yield,
    obsolescence_finding,
    sample_prior,
    simulate,
)
from silicon_atlas.hardware import get_device
from silicon_atlas.ir import build_graph
from silicon_atlas.ir.graph import Phase, Workload
from silicon_atlas.partition import Region, partition
from silicon_atlas.profiler import (
    concentration_index,
    dominant_roles,
    profile,
    serving_profile,
)
from silicon_atlas.quantization import QuantPriors, evaluate_plan, sensitivity_plan, uniform_plan
from silicon_atlas.readiness import Weights, build_candidates, sensitivity
from silicon_atlas.registry import Registry

import numpy as np


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load()


@pytest.fixture(scope="module")
def llama(registry: Registry):
    spec = registry["llama-3.1-8b"]
    return spec, build_graph(spec)


@pytest.fixture(scope="module")
def device():
    return get_device("h100-sxm")


# -------------------------------------------------------------------------- roofline ---


def test_decode_is_memory_bound_and_prefill_is_not(llama, device) -> None:
    """Alegacao C-003. Se isto inverter, estimar ganho por FLOPs deixa de ser erro."""
    spec, g = llama
    sp = serving_profile(g, device, prompt_len=2048, gen_len=512)
    assert sp.decode.memory_bound_share > 0.90
    assert sp.prefill.memory_bound_share < 0.40
    assert sp.decode.mean_intensity < device.ridge_point("bf16", Phase.DECODE)
    assert sp.prefill.mean_intensity > device.ridge_point("bf16", Phase.PREFILL)


def test_decode_weight_traffic_matches_model_size(llama, device) -> None:
    """Em decode, o trafego de pesos deve ser ~ o modelo inteiro por token."""
    spec, g = llama
    p = profile(g, Workload(phase=Phase.DECODE, batch=1, context_len=2048), device, "bf16")
    expected = spec.param_count() * 2  # bf16
    # A tabela de embeddings e lida por gather, nao inteira: descontada do esperado.
    expected -= spec.vocab_size * spec.hidden_size * 2
    assert 0.95 < p.weight_bytes / expected < 1.05, p.weight_bytes / expected


def test_larger_batch_improves_decode_intensity(llama, device) -> None:
    spec, g = llama
    lo = profile(g, Workload(phase=Phase.DECODE, batch=1, context_len=2048), device, "bf16")
    hi = profile(g, Workload(phase=Phase.DECODE, batch=64, context_len=2048), device, "bf16")
    assert hi.mean_intensity > lo.mean_intensity


def test_serving_profile_is_dominated_by_decode(llama, device) -> None:
    spec, g = llama
    sp = serving_profile(g, device, prompt_len=2048, gen_len=512)
    assert sp.decode_time_share > 0.8
    assert sp.generated_tokens == 512


def test_moe_has_low_flops_and_high_footprint(registry, device) -> None:
    """MoE: barata em aritmetica, cara em memoria — o perfil que nao deve ser endurecido."""
    dense = build_graph(registry["mistral-7b-v0.1"])
    moe = build_graph(registry["mixtral-8x7b-v0.1"])
    w = Workload(phase=Phase.DECODE, batch=1, context_len=2048)
    assert moe.total_flops(w) < 3 * dense.total_flops(w)
    assert moe.total_weight_elems() > 6 * dense.total_weight_elems()


def test_concentration_and_pareto(llama, device) -> None:
    spec, g = llama
    p = profile(g, Workload(phase=Phase.DECODE, context_len=4096), device, "bf16")
    roles = dominant_roles(p, threshold=0.80)
    assert sum(s for _, s in roles) >= 0.80
    assert len(roles) <= 8, "o custo deve estar concentrado em poucos papeis (C-002)"
    assert 0 < concentration_index(p) < 1


# ---------------------------------------------------------------------- quantizacao ---


def test_quantization_reduces_weight_bytes(llama, device) -> None:
    spec, g = llama
    plan = uniform_plan(g, "int4")
    ev = evaluate_plan(g, plan, Workload(phase=Phase.DECODE, context_len=2048), device, "bf16")
    assert 0.70 < ev.memory_reduction < 0.80  # bf16 -> int4 nos pesos quantizaveis
    assert ev.speedup > 1.5


def test_quality_delta_is_always_declared_unmeasured(llama, device) -> None:
    """G-002 aberta: o plano pode ser testado, nunca recomendado."""
    spec, g = llama
    plan = sensitivity_plan(g, QuantPriors.load())
    ev = evaluate_plan(g, plan, Workload(phase=Phase.DECODE, context_len=2048), device, "bf16")
    quality = [f for f in ev.findings() if f.name.endswith("quality_delta")][0]
    assert quality.value is None
    assert quality.status.name == "OPEN_GAP"
    assert "G-002" in quality.gaps


def test_measured_evidence_overrides_prior() -> None:
    priors = QuantPriors.load()
    prior = priors.tolerance("gate_proj", "int4")
    assert prior.status.name == "ASSUMPTION"
    measured = priors.with_evidence({"gate_proj": {"int4": 0.31}}).tolerance("gate_proj", "int4")
    assert measured.value == 0.31
    assert measured.status.name == "EXPERIMENTAL_EVIDENCE"
    assert measured.gaps == ()


def test_norms_and_router_resist_aggressive_quantization() -> None:
    priors = QuantPriors.load()
    assert priors.tolerance("input_layernorm", "int4").value < 0.2
    assert priors.tolerance("router", "int8").value < 0.5
    assert priors.tolerance("gate_proj", "int8").value > 0.8


def test_edge_layers_get_a_penalty() -> None:
    priors = QuantPriors.load()
    mid = priors.tolerance("gate_proj", "int4", layer=16, num_layers=32).value
    edge = priors.tolerance("gate_proj", "int4", layer=0, num_layers=32).value
    assert edge < mid


# ------------------------------------------------------------------------- particao ---


def _candidates(spec, graph, device):
    sp = serving_profile(graph, device, prompt_len=2048, gen_len=512)
    from silicon_atlas.invariants import ModelView, block_role_stability

    views = [ModelView.of(s) for s in Registry.load()]
    fam = [v for v in views if v.spec.family == spec.family]
    return build_candidates(
        graph, sp, QuantPriors.load(), Weights.load(),
        stability_by_block=block_role_stability(fam, views),
        is_moe=spec.is_moe,
    )


def test_amdahl_ceiling_bounds_any_claimed_gain(llama, device) -> None:
    """O teto e aritmetica, nao opiniao: nenhuma quantidade de silicio o contorna."""
    spec, g = llama
    part = partition(_candidates(spec, g, device), model_id=spec.id)
    f = part.hardened_share
    assert part.amdahl_ceiling() == pytest.approx(1.0 / (1.0 - f) if f < 1 else math.inf)
    if f < 0.99:
        assert part.required_speedup_for(100.0) is None or part.required_speedup_for(100.0) > 1


def test_partition_regions_are_exhaustive(llama, device) -> None:
    spec, g = llama
    cands = _candidates(spec, g, device)
    part = partition(cands, model_id=spec.id)
    assigned = sum(a.cost_share for a in part.assignments)
    assert assigned == pytest.approx(sum(c.cost_share for c in cands))
    assert sum(part.share(r) for r in Region) == pytest.approx(assigned)


def test_router_never_lands_in_the_fixed_region(registry, device) -> None:
    """Roteamento por token e o exemplo canonico do que nao deve virar circuito fixo."""
    spec = registry["mixtral-8x7b-v0.1"]
    g = build_graph(spec)
    part = partition(_candidates(spec, g, device), model_id=spec.id)
    for a in part.assignments:
        if a.candidate.role in ("router", "expert_combine"):
            assert a.region is not Region.FIXED


# --------------------------------------------------------------------- sensibilidade ---


@pytest.mark.falsifier
def test_rank_stability_is_computed_and_reported(llama, device) -> None:
    """F3 / C-006. O teste nao exige que o ranking seja estavel — exige que seja *medido*."""
    spec, g = llama
    cands = _candidates(spec, g, device)
    res = sensitivity(cands, Weights.load())
    assert res.samples >= 1000
    assert 0.0 <= res.top1_stability <= 1.0
    assert res.decidable == (res.top1_stability >= res.threshold)
    assert res.dominant_factor in ("E", "F", "R", "Q", "V", "M", "L")


def test_sensitivity_separates_discrimination_from_stability(llama, device) -> None:
    """Regressao de CE-001.

    `top1_stability` sozinha nao distingue "candidatos equivalentes" de "score cego". O
    diagnostico de discriminacao existe justamente para separar os dois — e a medicao no corpus
    mostra que boa parte do peso do LHS e inerte na comparacao intra-modelo.
    """
    spec, g = llama
    res = sensitivity(_candidates(spec, g, device), Weights.load())
    assert res.score_spread >= 0 and res.noise_band > 0
    assert 0.0 <= res.inert_weight <= 1.0
    assert res.varying_factors, "algum fator precisa variar, senao nao ha ranking"
    assert res.diagnosis
    # F (custo) e Q (quantizacao) sao os unicos fatores que distinguem papeis do mesmo modelo.
    assert "F" in res.varying_factors and "Q" in res.varying_factors
    # R, M e L sao propriedades do modelo, nao do papel: constantes por construcao.
    assert res.inert_weight >= 0.30, (
        "CE-001: R, M e L (0.35 do peso) sao identicos entre todos os candidatos. Se isto "
        "mudar, a calibracao de G-011 avancou e o contraexemplo deve ser revisado."
    )
    # Entre os candidatos que disputam a lideranca, a inercia e ainda maior.
    assert len(res.contenders) >= 1
    if len(res.contenders) > 1:
        assert res.contender_inert_weight >= res.inert_weight


@pytest.mark.falsifier
def test_ties_are_not_mistaken_for_indecision(llama, device) -> None:
    """`gate_proj` e `up_proj` tem fatores identicos: ordena-los nao significa nada.

    A margem e medida contra o primeiro concorrente **distinto**, senao um empate exato seria
    lido como score cego — e o diagnostico apontaria para o defeito errado.
    """
    spec, g = llama
    cands = _candidates(spec, g, device)
    by_role = {c.role: c for c in cands}
    gate, up = by_role["gate_proj"], by_role["up_proj"]
    assert gate.lhs == up.lhs, "premissa do teste: os dois papeis sao equivalentes"
    res = sensitivity(cands, Weights.load())
    assert res.margin > 0, "a margem nao pode ser zero so porque dois candidatos empatam"


def test_sensitivity_is_deterministic(llama, device) -> None:
    """Semente fixa: dois analistas com os mesmos dados obtem o mesmo numero."""
    spec, g = llama
    cands = _candidates(spec, g, device)
    a = sensitivity(cands, Weights.load())
    b = sensitivity(cands, Weights.load())
    assert a.top1_stability == b.top1_stability


# ------------------------------------------------------------------------- economia ---


def test_lognormal_prior_respects_declared_percentiles() -> None:
    rng = np.random.default_rng(7)
    s = sample_prior({"dist": "lognormal", "p10": 1000.0, "p90": 9000.0}, 200000, rng)
    assert np.percentile(s, 10) == pytest.approx(1000.0, rel=0.05)
    assert np.percentile(s, 90) == pytest.approx(9000.0, rel=0.05)


def test_yield_falls_with_area() -> None:
    d = np.array([0.1, 0.1])
    y = murphy_yield(np.array([50.0, 800.0]), d)
    assert y[0] > y[1]
    assert 0 < y[1] < y[0] <= 1


def test_dies_per_wafer_falls_with_area() -> None:
    n = gross_dies_per_wafer(np.array([25.0, 400.0]))
    assert n[0] > n[1] >= 1


def test_obsolescence_without_rate_is_maximum_risk() -> None:
    f = obsolescence_finding(None)
    assert f.value == 1.0
    assert f.status.name == "OPEN_GAP"
    assert "G-006" in f.gaps


def test_obsolescence_decays_with_rate() -> None:
    slow = obsolescence_finding(0.1, horizon_years=4)
    fast = obsolescence_finding(1.0, horizon_years=4)
    assert slow.value < fast.value < 1.0


def test_corpus_partition_is_degenerate_and_says_so(llama, device) -> None:
    """No corpus real a regiao fixa e vazia — e o sistema precisa **declarar** isso.

    A distribuicao completa e exercitada em `tests/test_nondegenerate.py`, sobre uma particao
    construida para ter regiao fixa. Aqui o contrato e o oposto: nao inventar numeros.
    """
    spec, g = llama
    cands = _candidates(spec, g, device)
    part = partition(cands, model_id=spec.id)
    assert part.hardened_share == 0.0, (
        "se isto mudar, a politica foi afrouxada ou a estabilidade subiu — verificar git diff "
        "de config/partition_policy.v1.json antes de comemorar"
    )
    sp = serving_profile(g, device, prompt_len=2048, gen_len=512)
    design = build_design_point(g, part, sp.decode, target_tokens_per_second=1000)
    assert design.is_empty
    res = simulate(
        design, sp, device, annual_tokens=1e13, node="6nm",
        priors=EconomicsPriors.load(), obsolescence_rate_per_year=0.5, samples=4000,
    )
    assert res.not_applicable
    d = res.as_dict()
    assert d["percentiles"] is None and d["sensitivity_breakeven"] == []


def test_economics_findings_never_claim_experimental_status(llama, device) -> None:
    spec, g = llama
    part = partition(_candidates(spec, g, device), model_id=spec.id)
    sp = serving_profile(g, device, prompt_len=2048, gen_len=512)
    design = build_design_point(g, part, sp.decode, target_tokens_per_second=1000)
    res = simulate(design, sp, device, annual_tokens=1e13, samples=2000,
                   obsolescence_rate_per_year=0.5)
    for f in res.findings():
        assert not f.status.supports_tapeout, f"{f.name} nao pode sustentar tape-out"
