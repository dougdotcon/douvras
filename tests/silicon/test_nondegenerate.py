"""O caminho nao-degenerado: particao com regiao fixa nao-vazia.

Estes testes existem por causa da retratacao R-002. Como o corpus real nunca produz regiao fixa
sob a politica vigente, todo o ramo economico do Atlas — dimensionamento, area, NRE, break-even,
teto de Amdahl com f > 0 — passou o ciclo C-001 **sem nunca ter sido executado sob teste**.

As asseveracoes usam constantes literais calculadas a mao, nunca re-derivadas da implementacao:
um teste que recalcula a formula que testa nao testa nada.
"""

from __future__ import annotations

import math

import pytest

from silicon_atlas.economics import (
    EconomicsPriors,
    NotApplicable,
    build_design_point,
    simulate,
)
from silicon_atlas.partition import Level, Region
from douvras_core.status import Status


# ---------------------------------------------------------------------- particao ---


def test_partition_has_a_real_fixed_region(nondegenerate_partition) -> None:
    _, _, part, _, _ = nondegenerate_partition
    assert part.hardened_share == pytest.approx(0.70)
    roles = {a.candidate.role for a in part.by_region(Region.FIXED)}
    assert roles == {"gate_proj", "up_proj", "down_proj"}
    assert "operador_emergente" in {a.candidate.role for a in part.by_region(Region.RECONFIGURABLE)}
    assert "sampling" in {a.candidate.role for a in part.by_region(Region.PROGRAMMABLE)}
    assert part.share(Region.RECONFIGURABLE) == pytest.approx(0.20)
    assert part.share(Region.PROGRAMMABLE) == pytest.approx(0.10)


def test_amdahl_ceiling_literal_value(nondegenerate_partition) -> None:
    """1/(1-0.70) = 3.3333. Constante literal: nao re-derivar da implementacao."""
    _, _, part, _, _ = nondegenerate_partition
    assert part.amdahl_ceiling() == pytest.approx(3.3333333, abs=1e-6)
    # Com aceleracao finita: 1/((1-0.7) + 0.7/10) = 1/0.37 = 2.7027
    assert part.amdahl_ceiling(10.0) == pytest.approx(2.7027027, abs=1e-6)


def test_required_speedup_is_finite_below_ceiling_and_none_above(nondegenerate_partition) -> None:
    _, _, part, _, _ = nondegenerate_partition
    # alvo 3.0 < teto 3.333: exige 0.7/(1/3 - 0.3) = 0.7/0.033333 = 21.0
    needed = part.required_speedup_for(3.0)
    assert needed is not None and needed == pytest.approx(21.0, rel=1e-6)
    assert part.required_speedup_for(3.3333333) is None or part.required_speedup_for(4.0) is None
    assert part.required_speedup_for(100.0) is None


def test_level_reflects_hardened_share(nondegenerate_partition) -> None:
    _, _, part, _, _ = nondegenerate_partition
    assert part.level is Level.MODEL_FAMILY_ACCELERATOR  # 0.55 <= 0.70 < 0.75


def test_partition_text_renders_all_regions(nondegenerate_partition) -> None:
    _, _, part, _, _ = nondegenerate_partition
    text = part.as_text()
    for target in ("ASIC/IP fixo", "FPGA/eFPGA", "CPU/GPU"):
        assert target in text
    assert "gate_proj" in text and "operador_emergente" in text


# ---------------------------------------------------------------------- economia ---


@pytest.fixture
def econ(nondegenerate_partition):
    _, graph, part, sp, _ = nondegenerate_partition
    design = build_design_point(graph, part, sp.decode, target_tokens_per_second=1000)
    res = simulate(
        design, sp, sp.device, annual_tokens=1e13, node="6nm",
        priors=EconomicsPriors.load(), obsolescence_rate_per_year=0.5, samples=4000,
    )
    return design, res, part


def test_design_point_is_not_empty(econ) -> None:
    design, res, _ = econ
    assert not design.is_empty
    assert design.hardened_weight_bits > 0
    assert design.hardened_flops_per_token > 0
    assert set(design.hardened_roles) == {"gate_proj", "up_proj", "down_proj"}
    assert not res.not_applicable


@pytest.mark.falsifier
def test_energy_gain_never_exceeds_the_amdahl_ceiling(econ) -> None:
    """Invariante que `partition.py` e `hardware.py` afirmam prevenir (alegacao C-004).

    Antes da correcao B, o ganho de energia dividia a energia da GPU inteira pela energia apenas
    da regiao endurecida — e chegava a 6,7x acima do teto fisico da propria particao.
    """
    _, res, part = econ
    ceiling = part.amdahl_ceiling()
    for q in ("p10", "p50", "p90"):
        assert res.pct("energy_gain")[q] <= ceiling * 1.001, (
            f"ganho de energia {q} = {res.pct('energy_gain')[q]:.2f}x excede o teto "
            f"de Amdahl {ceiling:.2f}x da propria particao"
        )


def test_energy_gain_is_monotonic_in_hardened_share(nondegenerate_partition) -> None:
    """Endurecer mais nao pode pontuar pior. Antes da correcao B, f=0 vencia f=0.995."""
    from silicon_atlas.partition import partition

    _, graph, _, sp, _ = nondegenerate_partition
    from tests.silicon.conftest import make_candidate  # noqa: PLC0415

    gains = []
    for share in (0.30, 0.60, 0.90):
        cands = [
            make_candidate("gate_proj", cost_share=share,
                           weight_elems=sum(n.weight_elems for n in graph if n.role == "gate_proj")),
            make_candidate("sampling", cost_share=1.0 - share, R=0.0, Q=0.0, E=0.1,
                           block_role="head", kind="sampling"),
        ]
        part = partition(cands, model_id="teste")
        assert part.hardened_share == pytest.approx(share)
        design = build_design_point(graph, part, sp.decode, target_tokens_per_second=1000)
        res = simulate(design, sp, sp.device, annual_tokens=1e13, samples=1500,
                       obsolescence_rate_per_year=0.5)
        gains.append(res.pct("energy_gain")["p50"])
    assert gains[0] < gains[1] < gains[2], f"ganho nao-monotonico na fracao endurecida: {gains}"


def test_economics_emits_full_distribution(econ) -> None:
    _, res, _ = econ
    for key in ("die_area_mm2", "nre_usd", "breakeven_years", "asic_tokens_per_second"):
        p = res.pct(key)
        assert p["p10"] <= p["p50"] <= p["p90"], key
    assert 0.0 <= res.prob_breakeven_within_life <= 1.0
    assert res.prob_breakeven_before_obsolescence <= res.prob_breakeven_within_life + 1e-9
    d = res.as_dict()
    assert d["not_applicable"] is False
    assert d["percentiles"] is not None
    assert d["sensitivity_breakeven"], "a decomposicao de sensibilidade precisa existir"


def test_asic_throughput_matches_the_target(econ) -> None:
    """O acelerador e dimensionado *para* o alvo: throughput deve reproduzi-lo."""
    design, res, _ = econ
    assert res.pct("asic_tokens_per_second")["p50"] == pytest.approx(
        design.target_tokens_per_second, rel=0.02
    )


def test_die_area_is_physically_plausible(econ) -> None:
    _, res, _ = econ
    p50 = res.pct("die_area_mm2")["p50"]
    assert 0.1 < p50 < 5000, f"area de die implausivel: {p50} mm2"
    assert res.pct("yield")["p50"] > 0.0


def test_breakeven_improves_with_volume(nondegenerate_partition) -> None:
    _, graph, part, sp, _ = nondegenerate_partition
    design = build_design_point(graph, part, sp.decode, target_tokens_per_second=1000)
    anos = []
    for vol in (1e12, 1e14):
        res = simulate(design, sp, sp.device, annual_tokens=vol, samples=1500,
                       obsolescence_rate_per_year=0.5)
        be = res.pct("breakeven_years")["p50"]
        anos.append(be)
    assert anos[1] < anos[0], f"mais volume deveria amortizar mais rapido: {anos}"


# ------------------------------------------------------------------ degeneracao ---


def test_empty_region_refuses_to_produce_numbers(registry, device) -> None:
    """A guarda de R-002: sem projeto, o simulador levanta em vez de inventar."""
    from silicon_atlas.ir import build_graph
    from silicon_atlas.partition import Partition
    from silicon_atlas.profiler import serving_profile

    graph = build_graph(registry["llama-3.1-8b"])
    sp = serving_profile(graph, device, prompt_len=512, gen_len=64)
    part = Partition(model_id=graph.model_id, phase_label="vazia")
    design = build_design_point(graph, part, sp.decode, target_tokens_per_second=1000)
    res = simulate(design, sp, device, annual_tokens=1e13, samples=500,
                   obsolescence_rate_per_year=0.5)

    assert res.not_applicable and res.reason
    with pytest.raises(NotApplicable):
        res.pct("die_area_mm2")
    assert res.prob_asic_cheaper is None
    assert res.prob_breakeven_within_life is None
    assert res.as_dict()["percentiles"] is None
    for f in res.findings():
        assert f.value is None and f.status is Status.OPEN_GAP


def test_absent_factors_are_zero_not_maximum(registry, device) -> None:
    """P, R e N valem zero sem projeto — antes, P valia 1,0 e decidia a banda (R-002)."""
    from silicon_atlas.assessment import Assessment, AssessmentInputs

    a = Assessment.build(AssessmentInputs(model_id="llama-3.1-8b", mc_samples=500))
    assert a.economics.not_applicable
    for k in ("P", "R", "N"):
        assert float(a.srs.factors[k].value) == 0.0, k
        assert "G-001" in a.srs.factors[k].gaps
