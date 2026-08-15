"""PPA & Economics Simulator (Metodo 12.8) com incerteza propagada (ADR-0004).

Nao emite ponto: emite distribuicao. A pergunta que o modulo responde nao e "qual o
break-even?" e sim **"qual a probabilidade de o break-even chegar antes de o chip ficar
obsoleto?"** — a unica formulacao que corresponde a decisao real de quem vai gastar dinheiro
em mascara.

Segundo produto do modulo: a decomposicao de sensibilidade. O parametro que domina a variancia
do resultado vira o proximo item do GAP_REGISTER, com prioridade justificada por numero em vez
de por preferencia.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .hardware import CONFIG_DIR, DEFAULT_ENERGY, Device, EnergyModel
from .ir.graph import Graph, Phase, Workload, precision
from .partition import Partition, Region
from .profiler import PhaseProfile, ServingProfile
from douvras_core.status import Finding, Status

SECONDS_PER_YEAR = 365.25 * 24 * 3600
Z90 = 1.2815515655446004  # quantil 90% da normal padrao


class NotApplicable(RuntimeError):
    """Grandeza economica pedida quando nao existe ponto de projeto.

    Levantar excecao e deliberado: devolver zero, infinito ou NaN faria o numero atravessar o
    pipeline e ser publicado. Ver retratacao R-002 — foi exatamente assim que um acelerador
    inexistente produziu o fator de decisao de oito relatorios.
    """


# --------------------------------------------------------------------------------------
# Amostragem de priors
# --------------------------------------------------------------------------------------


def sample_prior(spec: Mapping[str, Any], n: int, rng: np.random.Generator) -> np.ndarray:
    """Amostra uma distribuicao declarada. Lognormal e parametrizada por p10/p90."""
    dist = spec.get("dist", "point")
    if dist == "point":
        return np.full(n, float(spec["value"]))
    if dist == "uniform":
        return rng.uniform(float(spec["lo"]), float(spec["hi"]), n)
    if dist == "lognormal":
        p10, p90 = float(spec["p10"]), float(spec["p90"])
        mu = (math.log(p10) + math.log(p90)) / 2.0
        sigma = (math.log(p90) - math.log(p10)) / (2.0 * Z90)
        return rng.lognormal(mu, sigma, n)
    if dist == "triangular":
        return rng.triangular(float(spec["lo"]), float(spec["mode"]), float(spec["hi"]), n)
    raise ValueError(f"distribuicao desconhecida: {dist!r}")


@dataclass
class EconomicsPriors:
    tech_nodes: dict[str, dict[str, Any]]
    manufacturing: dict[str, Any]
    operations: dict[str, Any]
    monte_carlo: dict[str, Any]
    version: str = "1.0"

    @classmethod
    def load(cls, path: Path | None = None) -> "EconomicsPriors":
        doc = json.loads(
            (path or CONFIG_DIR / "economics_priors.v1.json").read_text(encoding="utf-8")
        )
        return cls(
            tech_nodes=doc["tech_nodes"],
            manufacturing=doc["manufacturing"],
            operations=doc["operations"],
            monte_carlo=doc["monte_carlo"],
            version=doc["_meta"]["version"],
        )

    def node(self, name: str) -> dict[str, Any]:
        if name not in self.tech_nodes:
            raise KeyError(f"no tecnologico {name!r} sem priors; disponiveis: {sorted(self.tech_nodes)}")
        return self.tech_nodes[name]


# --------------------------------------------------------------------------------------
# Ponto de projeto derivado da particao
# --------------------------------------------------------------------------------------


@dataclass
class DesignPoint:
    """O que a particao implica em silicio, antes de qualquer custo.

    Tudo aqui e aritmetica sobre a IR: quantos bits de peso precisam residir on-chip, quantos
    FLOPs por token a regiao fixa executa, quanto de KV cache precisa caber.
    """

    model_id: str
    hardened_roles: list[str]
    hardened_weight_bits: float
    hardened_flops_per_token: float
    total_flops_per_token: float
    kv_bytes_at_context: float
    activation_working_bytes: float
    hardened_cost_share: float
    target_tokens_per_second: float
    batch: int = 1
    hardened_precision: str = "int8"

    @property
    def hardened_gbit(self) -> float:
        return self.hardened_weight_bits / 1e9

    @property
    def is_empty(self) -> bool:
        return self.hardened_weight_bits <= 0.0 or self.hardened_flops_per_token <= 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "hardened_roles": self.hardened_roles,
            "hardened_weight_gbit": round(self.hardened_gbit, 3),
            "hardened_precision": self.hardened_precision,
            "hardened_flops_per_token": self.hardened_flops_per_token,
            "total_flops_per_token": self.total_flops_per_token,
            "hardened_cost_share": round(self.hardened_cost_share, 4),
            "kv_bytes_at_context_gb": self.kv_bytes_at_context / 1e9,
            "batch": self.batch,
            "target_tokens_per_second": self.target_tokens_per_second,
            "is_empty": self.is_empty,
        }


def build_design_point(
    graph: Graph,
    part: Partition,
    decode: PhaseProfile,
    *,
    target_tokens_per_second: float,
    precision_by_role: Mapping[str, str] | None = None,
) -> DesignPoint:
    """Traduz a particao em requisitos fisicos, usando a fase de decode como referencia."""
    fixed_roles = [a.candidate.role for a in part.by_region(Region.FIXED)]
    prec_map = dict(precision_by_role or {})
    for a in part.by_region(Region.FIXED):
        prec_map.setdefault(a.candidate.role, a.candidate.precision)

    bits = 0.0
    hardened_flops = 0.0
    bits_by_prec: dict[str, float] = {}
    w = decode.workload
    batch = max(w.batch, 1)
    for n in graph:
        if n.role in fixed_roles:
            p = prec_map.get(n.role, "int8")
            b = n.weight_elems * precision(p).bits
            bits += b
            bits_by_prec[p] = bits_by_prec.get(p, 0.0) + b
            hardened_flops += n.flops(w)

    total_flops = sum(n.flops(w) for n in graph)
    kv = sum(c.state_bytes for c in decode.costs)
    # Buffer de trabalho: ativacoes da camada mais larga, com folga para double buffering.
    widest = max((n.attrs.get("width", 0) or n.attrs.get("out_features", 0)) for n in graph)
    act = widest * batch * 4 * precision(w.activation_precision).bytes_per_elem

    # Precisao dominante em bits de peso: e ela que define a energia por FLOP do datapath.
    dominant = max(bits_by_prec, key=lambda k: bits_by_prec[k]) if bits_by_prec else "int8"

    return DesignPoint(
        model_id=graph.model_id,
        hardened_roles=sorted(fixed_roles),
        hardened_weight_bits=bits,
        # Por token, nao por passo: com lote B o passo processa B tokens. Sem normalizar, o die
        # seria dimensionado B vezes maior contra uma GPU medida em tokens agregados.
        hardened_flops_per_token=hardened_flops / batch,
        total_flops_per_token=total_flops / batch,
        kv_bytes_at_context=kv,
        activation_working_bytes=act,
        hardened_cost_share=part.hardened_share,
        target_tokens_per_second=target_tokens_per_second,
        batch=batch,
        hardened_precision=dominant,
    )


# --------------------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------------------


def gross_dies_per_wafer(area_mm2: np.ndarray, diameter_mm: float = 300.0) -> np.ndarray:
    """Aproximacao classica de dies brutos por wafer, com perda de borda."""
    r = diameter_mm / 2.0
    return np.maximum(
        (math.pi * r * r) / area_mm2 - (math.pi * diameter_mm) / np.sqrt(2.0 * area_mm2), 1.0
    )


def murphy_yield(area_mm2: np.ndarray, defect_density_cm2: np.ndarray) -> np.ndarray:
    """Modelo de Murphy. AD = area (cm2) x densidade de defeitos."""
    ad = (area_mm2 / 100.0) * defect_density_cm2
    ad = np.maximum(ad, 1e-9)
    return ((1.0 - np.exp(-ad)) / ad) ** 2


@dataclass
class EconomicsResult:
    """Distribuicao de resultados, nunca um ponto (ADR-0004)."""

    samples: int
    node: str
    design: DesignPoint
    annual_tokens: float
    obsolescence_rate_per_year: float | None
    arrays: dict[str, np.ndarray] = field(repr=False, default_factory=dict)
    not_applicable: bool = False
    reason: str = ""

    # -- percentis ------------------------------------------------------------------
    def pct(self, key: str, q: Sequence[float] = (10, 50, 90)) -> dict[str, float]:
        if self.not_applicable:
            raise NotApplicable(
                f"{key}: {self.reason}. Sem ponto de projeto nao existe grandeza a percentilar."
            )
        arr = self.arrays[key]
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            return {f"p{int(x)}": float("inf") for x in q}
        return {f"p{int(x)}": float(np.percentile(finite, x)) for x in q}

    @property
    def prob_asic_cheaper(self) -> float | None:
        if self.not_applicable:
            return None
        return float(np.mean(self.arrays["cost_delta_per_token"] > 0))

    @property
    def prob_breakeven_within_life(self) -> float | None:
        """Probabilidade de amortizar o NRE dentro da vida util do chip."""
        if self.not_applicable:
            return None
        return float(np.mean(self.arrays["breakeven_years"] <= self.arrays["asic_life_years"]))

    @property
    def prob_breakeven_before_obsolescence(self) -> float | None:
        """Idem, mas exigindo tambem que a estrutura do modelo sobreviva ate la.

        E a metrica que decide o investimento. Devolve ``None`` — nunca NaN — quando a taxa de
        obsolescencia nao foi observada ou quando nao ha projeto: um NaN atravessou o pipeline
        ate a afirmacao principal de quatro relatorios antes de ser detectado (R-003).
        """
        if self.not_applicable or self.obsolescence_rate_per_year is None:
            return None
        be = self.arrays["breakeven_years"]
        survival = np.exp(-self.obsolescence_rate_per_year * np.clip(be, 0, 50))
        within = (be <= self.arrays["asic_life_years"]).astype(float)
        return float(np.mean(within * survival))

    @property
    def prob_exceeds_reticle(self) -> float | None:
        if self.not_applicable:
            return None
        return float(np.mean(self.arrays["exceeds_reticle"]))

    # -- sensibilidade ---------------------------------------------------------------
    def sensitivity(self, target: str = "breakeven_years", top: int = 8) -> list[tuple[str, float]]:
        """Correlacao de postos entre cada entrada e o resultado.

        Converte incerteza em plano de pesquisa: o parametro no topo desta lista e o que
        mais paga para ser medido.
        """
        if self.not_applicable:
            return []
        y = self.arrays[target]
        mask = np.isfinite(y)
        if mask.sum() < 32:
            return []
        yr = _rank(y[mask])
        out = []
        for k, v in self.arrays.items():
            if k == target or v.dtype == bool or not np.isfinite(v).all():
                continue
            if np.allclose(v, v[0]):
                continue
            c = float(np.corrcoef(_rank(v[mask]), yr)[0, 1])
            if not math.isnan(c):
                out.append((k, c))
        return sorted(out, key=lambda kv: -abs(kv[1]))[:top]

    # -- saidas ----------------------------------------------------------------------
    def findings(self) -> list[Finding]:
        if self.not_applicable:
            # Ausencia declarada, nao numero. `value=None` impede que qualquer consumidor
            # formate um valor que nao existe.
            return [
                Finding(
                    name=n,
                    value=None,
                    unit=u,
                    status=Status.OPEN_GAP,
                    gaps=("G-001",),
                    note=self.reason,
                )
                for n, u in (
                    ("economics.breakeven_years.p50", "anos"),
                    ("economics.p_breakeven_before_obsolescence", "probabilidade"),
                    ("economics.die_area_mm2.p50", "mm2"),
                )
            ]

        common = dict(
            status=Status.CONDITIONAL_RESULT,
            assumptions=("A-003", "A-006", "A-008"),
            gaps=("G-004", "G-005", "G-007"),
        )
        be = self.pct("breakeven_years")
        prob = self.prob_breakeven_before_obsolescence
        return [
            Finding(name="economics.breakeven_years.p50", value=be["p50"], unit="anos", **common),
            Finding(name="economics.breakeven_years.p90", value=be["p90"], unit="anos", **common),
            Finding(
                name="economics.p_breakeven_before_obsolescence",
                value=prob,
                unit="probabilidade",
                status=Status.CONDITIONAL_RESULT if prob is not None else Status.OPEN_GAP,
                assumptions=("A-003", "A-006", "A-007", "A-008") if prob is not None else (),
                gaps=("G-004", "G-005", "G-006", "G-007") if prob is not None else ("G-006",),
                note=(
                    "metrica de decisao; combina amortizacao e sobrevivencia estrutural"
                    if prob is not None
                    else "nao estimavel: taxa de obsolescencia nao observada (G-006)"
                ),
            ),
            Finding(
                name="economics.die_area_mm2.p50",
                value=self.pct("die_area_mm2")["p50"],
                unit="mm2",
                **common,
            ),
        ]

    def as_dict(self) -> dict[str, Any]:
        base = {
            "samples": self.samples,
            "tech_node": self.node,
            "design_point": self.design.as_dict(),
            "annual_tokens": self.annual_tokens,
            "obsolescence_rate_per_year": self.obsolescence_rate_per_year,
            "not_applicable": self.not_applicable,
        }
        if self.not_applicable:
            # O JSON precisa negar o que o Markdown nega. Publicar percentis aqui foi o defeito
            # R-003: o consumidor de maquina recebia PPA que o documento humano desmentia.
            return {
                **base,
                "reason": self.reason,
                "percentiles": None,
                "prob_asic_cheaper_per_token": None,
                "prob_breakeven_within_life": None,
                "prob_breakeven_before_obsolescence": None,
                "prob_exceeds_reticle": None,
                "sensitivity_breakeven": [],
            }

        keys = ("die_area_mm2", "die_cost_usd", "nre_usd", "asic_tokens_per_second",
                "gpu_cost_per_token", "asic_cost_per_token", "breakeven_tokens",
                "breakeven_years", "asic_energy_per_token_j", "energy_gain")
        prob = self.prob_breakeven_before_obsolescence
        return {
            **base,
            "percentiles": {k: {q: _r(v) for q, v in self.pct(k).items()} for k in keys},
            "prob_asic_cheaper_per_token": round(self.prob_asic_cheaper, 4),
            "prob_breakeven_within_life": round(self.prob_breakeven_within_life, 4),
            "prob_breakeven_before_obsolescence": round(prob, 4) if prob is not None else None,
            "prob_exceeds_reticle": round(self.prob_exceeds_reticle, 4),
            "sensitivity_breakeven": [
                {"parameter": k, "rank_correlation": round(c, 3)} for k, c in self.sensitivity()
            ],
        }


def _rank(a: np.ndarray) -> np.ndarray:
    order = a.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(a), dtype=float)
    return ranks


def _r(x: float) -> float:
    if not math.isfinite(x):
        return float("inf")
    return round(x, 6) if abs(x) < 1e3 else round(x, 1)


def simulate(
    design: DesignPoint,
    gpu_profile: ServingProfile,
    device: Device,
    *,
    annual_tokens: float,
    node: str = "6nm",
    priors: EconomicsPriors | None = None,
    energy: EnergyModel | None = None,
    obsolescence_rate_per_year: float | None = None,
    hardened_only: bool = True,
    samples: int | None = None,
) -> EconomicsResult:
    """Simula PPA e economia do ponto de projeto contra o baseline de GPU.

    ``hardened_only=True`` modela a arquitetura **hibrida** recomendada pela particao: o
    acelerador executa a regiao fixa e o host continua executando o resto. O ganho de sistema
    fica limitado por Amdahl. ``hardened_only=False`` modela o chip que absorve o caminho
    inteiro — mais rapido no limite, e com todo o risco de obsolescencia concentrado.
    """
    pr = priors or EconomicsPriors.load()
    em = energy or DEFAULT_ENERGY
    n = int(samples or pr.monte_carlo.get("samples", 20000))
    rng = np.random.default_rng(int(pr.monte_carlo.get("seed", 0)))
    nd = pr.node(node)
    mf, op = pr.manufacturing, pr.operations

    # Guarda de degeneracao (R-002). Sem FLOPs endurecidos ou sem pesos a fixar nao existe
    # acelerador — e um simulador que responde mesmo assim inventa o objeto que deveria avaliar.
    if hardened_only and (
        design.hardened_flops_per_token <= 0.0 or design.hardened_weight_bits <= 0.0
    ):
        falta = []
        if design.hardened_flops_per_token <= 0.0:
            falta.append("nenhum FLOP endurecido")
        if design.hardened_weight_bits <= 0.0:
            falta.append("nenhum peso a fixar")
        return EconomicsResult(
            samples=0,
            node=node,
            design=design,
            annual_tokens=annual_tokens,
            obsolescence_rate_per_year=obsolescence_rate_per_year,
            arrays={},
            not_applicable=True,
            reason=f"regiao fixa vazia ({' e '.join(falta)}): nao ha ponto de projeto a simular",
        )

    S = lambda spec: sample_prior(spec, n, rng)  # noqa: E731

    # --- amostras de entrada ---
    mask = S(nd["mask_set_usd"])
    design_cost = S(nd["design_verification_usd"])
    wafer = S(nd["wafer_usd"])
    d0 = S(nd["defect_density_per_cm2"])
    mm2_mac = S(nd["mm2_per_mac_int8"])
    mm2_sram = S(nd["mm2_per_sram_bit"])
    mm2_rom = S(nd["mm2_per_rom_bit"])
    clock = S(nd["clock_ghz"]) * 1e9

    pkg = S(mf["packaging_test_usd_per_die"])
    respin_cost = S(mf["bringup_respin_usd"])
    respin_p = S(mf["respin_probability"])
    reticle = float(mf["max_reticle_mm2"])

    kwh = S(op["electricity_usd_per_kwh"])
    gpu_capex = S(op["gpu_capex_usd"])
    gpu_life = S(op["gpu_life_years"])
    asic_life = S(op["asic_life_years"])
    util = S(op["utilization"])
    sys_overhead = S(op["asic_system_overhead"])

    # --- dimensionamento do acelerador ---
    # `DesignPoint` ja normaliza FLOPs por token; aqui so falta amortizar memoria pelo lote.
    batch = max(design.batch, 1)
    flops_tok = design.hardened_flops_per_token if hardened_only else design.total_flops_per_token
    macs_needed = (flops_tok * design.target_tokens_per_second) / (2.0 * clock * 0.7)

    logic_mm2 = macs_needed * mm2_mac
    rom_mm2 = design.hardened_weight_bits * mm2_rom
    sram_bits = (design.kv_bytes_at_context + design.activation_working_bytes) * 8.0
    sram_mm2 = sram_bits * mm2_sram
    core_mm2 = logic_mm2 + rom_mm2 + sram_mm2
    die_mm2 = core_mm2 * 1.25  # I/O, PLLs, controle, roteamento

    exceeds = die_mm2 > reticle
    # Acima do reticulo: particiona em chiplets, com custo de integracao.
    dies_per_unit = np.ceil(die_mm2 / reticle)
    die_area_each = die_mm2 / dies_per_unit

    gdw = gross_dies_per_wafer(die_area_each, float(mf["wafer_diameter_mm"]))
    y = murphy_yield(die_area_each, d0)
    cost_per_good_die = wafer / np.maximum(gdw * y, 1e-6)
    unit_cost = cost_per_good_die * dies_per_unit + pkg * dies_per_unit

    nre = mask + design_cost + respin_p * respin_cost

    # --- desempenho e energia ---
    asic_tps = (2.0 * macs_needed * clock * 0.7) / flops_tok

    # A precisao do plano de quantizacao entra na energia de computo: int4 custa metade de int8
    # por FLOP no modelo de energia, e descartar isso enviesava o resultado em ~2x nesse termo.
    e_compute = em.flop_energy(flops_tok, design.hardened_precision)
    rom_bytes_per_token = design.hardened_weight_bits / 8.0 / batch
    e_rom = em.byte_energy(rom_bytes_per_token, "rom")
    e_sram = em.byte_energy(design.kv_bytes_at_context / batch, "sram")
    asic_e_tok = (e_compute + e_rom + e_sram) * sys_overhead

    gpu_e_tok = gpu_profile.energy_per_generated_token
    gpu_tps = gpu_profile.generated_tokens_per_second

    # --- custo por token ---
    gpu_capex_per_token = gpu_capex / np.maximum(gpu_life * SECONDS_PER_YEAR * util * gpu_tps, 1e-9)
    gpu_energy_per_token = gpu_e_tok * kwh / 3.6e6
    gpu_cpt = gpu_capex_per_token + gpu_energy_per_token

    asic_capex_per_token = unit_cost / np.maximum(asic_life * SECONDS_PER_YEAR * util * asic_tps, 1e-9)
    asic_energy_per_token = asic_e_tok * kwh / 3.6e6

    if hardened_only:
        # Hibrido: o host continua pagando a fracao nao endurecida — de custo E de energia.
        # Omitir o residuo na energia produzia ganho acima do teto de Amdahl da propria
        # particao, e anti-monotonico na fracao endurecida (R-002, grupo B da revisao).
        residual = 1.0 - design.hardened_cost_share
        asic_cpt = asic_capex_per_token + asic_energy_per_token + residual * gpu_cpt
        asic_e_tok_system = asic_e_tok + residual * gpu_e_tok
    else:
        asic_cpt = asic_capex_per_token + asic_energy_per_token
        asic_e_tok_system = asic_e_tok

    delta = gpu_cpt - asic_cpt
    with np.errstate(divide="ignore", invalid="ignore"):
        be_tokens = np.where(delta > 0, nre / delta, np.inf)
        be_years = np.where(annual_tokens > 0, be_tokens / annual_tokens, np.inf)

    arrays = {
        "die_area_mm2": die_mm2,
        "die_cost_usd": unit_cost,
        "nre_usd": nre,
        "yield": y,
        "asic_tokens_per_second": asic_tps,
        "macs": macs_needed,
        "rom_area_mm2": rom_mm2,
        "logic_area_mm2": logic_mm2,
        "sram_area_mm2": sram_mm2,
        "gpu_cost_per_token": gpu_cpt,
        "asic_cost_per_token": asic_cpt,
        "cost_delta_per_token": delta,
        "breakeven_tokens": be_tokens,
        "breakeven_years": be_years,
        "asic_energy_per_token_j": np.full(n, asic_e_tok) if np.isscalar(asic_e_tok) else asic_e_tok,
        "energy_gain": gpu_e_tok / np.maximum(asic_e_tok_system, 1e-18),
        "asic_life_years": asic_life,
        "wafer_usd": wafer,
        "mask_set_usd": mask,
        "design_verification_usd": design_cost,
        "electricity_usd_per_kwh": kwh,
        "utilization": util,
        "clock_hz": clock,
        "mm2_per_rom_bit": mm2_rom,
        "mm2_per_mac_int8": mm2_mac,
        "defect_density": d0,
        "exceeds_reticle": exceeds,
    }
    return EconomicsResult(
        samples=n,
        node=node,
        design=design,
        annual_tokens=annual_tokens,
        obsolescence_rate_per_year=obsolescence_rate_per_year,
        arrays=arrays,
    )


def obsolescence_finding(rate_per_year: float | None, horizon_years: float = 4.0) -> Finding:
    """Risco de obsolescencia como sobrevivencia estrutural, nao como desconto arbitrario."""
    if rate_per_year is None:
        return Finding(
            "O.obsolescence_risk", 1.0, Status.OPEN_GAP, unit="[0,1]", gaps=("G-006",),
            note="taxa de mudanca estrutural nao estimada: risco tratado como maximo",
        )
    survival = math.exp(-rate_per_year * horizon_years)
    return Finding(
        "O.obsolescence_risk",
        1.0 - survival,
        Status.CONDITIONAL_RESULT,
        unit="[0,1]",
        assumptions=("A-007",),
        gaps=("G-006",),
        note=(
            f"taxa observada {rate_per_year:.2f} mudancas/ano no corpus; "
            f"P(estrutura sobrevive {horizon_years:g} anos) = {survival:.2f}"
        ),
    )


#: Nota comum aos fatores que so existem se houver projeto. Sem projeto o valor correto e zero —
#: nao ha ganho, nao ha receita e nao ha NRE — e nao um numero derivado de um objeto inventado.
_NO_DESIGN = "regiao fixa vazia: sem ponto de projeto nao ha ganho, receita nem NRE"


def _absent_factor(name: str, note: str = _NO_DESIGN) -> Finding:
    return Finding(name, 0.0, Status.CONDITIONAL_RESULT, unit="[0,1]", gaps=("G-001",), note=note)


def nre_risk_finding(res: EconomicsResult) -> Finding:
    """N — risco de NRE e fabricacao, normalizado por area e por probabilidade de reticulo."""
    if res.not_applicable:
        return _absent_factor("N.nre_risk")
    p50_nre = res.pct("nre_usd")["p50"]
    scale = min(1.0, math.log10(max(p50_nre, 1e6) / 1e6) / math.log10(300.0))
    penalty = min(1.0, scale + 0.4 * res.prob_exceeds_reticle)
    return Finding(
        "N.nre_risk",
        penalty,
        Status.CONDITIONAL_RESULT,
        unit="[0,1]",
        assumptions=("A-006", "A-008"),
        gaps=("G-005", "G-007"),
        note=(
            f"NRE P50 = US$ {p50_nre / 1e6:.1f} M; "
            f"P(area acima do reticulo) = {res.prob_exceeds_reticle:.0%}"
        ),
    )


def perf_per_watt_finding(res: EconomicsResult) -> Finding:
    """P — ganho de performance por watt, normalizado em escala log ate 100x.

    O teto de saturacao em 100x nao tem base empirica: qualquer projeto minimamente agressivo
    satura o fator. Ver lacuna G-013 — calibrar exige casos reais de perf/W ASIC contra GPU.
    """
    if res.not_applicable:
        return _absent_factor("P.perf_per_watt")
    gain = res.pct("energy_gain")["p50"]
    val = min(1.0, max(0.0, math.log10(max(gain, 1.0)) / 2.0))
    return Finding(
        "P.perf_per_watt",
        val,
        Status.CONDITIONAL_RESULT,
        unit="[0,1]",
        assumptions=("A-003",),
        gaps=("G-004",),
        note=f"ganho de energia por token P50 = {gain:.1f}x (modelo analitico vs GPU medida por TDP)",
    )


def revenue_finding(res: EconomicsResult, annual_tokens: float) -> Finding:
    """R — economia anual potencial, normalizada em escala log entre US$ 100 mil e US$ 1 bi."""
    if res.not_applicable:
        return _absent_factor("R.revenue_potential")
    delta = res.pct("cost_delta_per_token")["p50"]
    annual = max(delta * annual_tokens, 0.0)
    val = 0.0 if annual <= 1e5 else min(1.0, math.log10(annual / 1e5) / 4.0)
    return Finding(
        "R.revenue_potential",
        val,
        Status.CONDITIONAL_RESULT,
        unit="[0,1]",
        assumptions=("A-006",),
        gaps=("G-005",),
        note=f"economia anual P50 estimada: US$ {annual / 1e6:.2f} M",
    )


__all__ = [
    "EconomicsPriors",
    "DesignPoint",
    "EconomicsResult",
    "build_design_point",
    "simulate",
    "sample_prior",
    "gross_dies_per_wafer",
    "murphy_yield",
    "obsolescence_finding",
    "nre_risk_finding",
    "perf_per_watt_finding",
    "revenue_finding",
    "SECONDS_PER_YEAR",
]
