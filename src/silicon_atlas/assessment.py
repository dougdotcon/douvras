"""Silicon Readiness Assessment — o produto de entrada do Metodo 17.1.

Orquestra o pipeline inteiro e emite o relatorio. A emissao e um portao, nao uma formatacao:
`render()` recusa produzir o documento se faltar qualquer secao obrigatoria do Metodo 3.3, se a
analise de sensibilidade nao tiver sido executada, ou se o texto final contiver vocabulario
proibido pelo Metodo 3.2.

Um assessment que conclui "nao vale a pena fabricar" e uma entrega bem-sucedida.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .economics import (
    DesignPoint,
    EconomicsPriors,
    EconomicsResult,
    build_design_point,
    nre_risk_finding,
    obsolescence_finding,
    perf_per_watt_finding,
    revenue_finding,
    simulate,
)
from .fingerprint import model_fingerprint
from .hardware import Device, get_device
from .invariants import (
    Invariant,
    ModelView,
    StabilityReport,
    block_role_stability,
    discover_invariants,
    family_stability,
)
from .ir import build_graph
from .ir.graph import Graph, Phase, Workload
from .partition import Partition, hardening_ceiling_finding, partition
from .profiler import ServingProfile, concentration_index, serving_profile
from .quantization import PlanEvaluation, QuantPriors, evaluate_plan, quantizable_cost_share, sensitivity_plan
from .readiness import (
    HardeningCandidate,
    ScoreCard,
    SensitivityResult,
    Weights,
    build_candidates,
    build_srs,
    codesign_compatibility_factor,
    data_availability_factor,
    low_precision_factor,
    sensitivity,
)
from .registry import ModelSpec, Registry
from douvras_core.report import EmissionRefused
from douvras_core.status import Finding, FindingSet, Status, lint_text

MANDATORY_SECTIONS = (
    "pergunta_principal",
    "afirmacao_principal",
    "hipoteses",
    "dependencias",
    "criterios_de_falha",
    "resultados",
    "limitacoes",
    "o_que_nao_demonstra",
)


# `EmissionRefused` mora em `douvras_core.report` e e reexportada aqui, porque este e o modulo
# que a levanta. Quem consome um relatorio DOUVRAS captura uma excecao, nao uma por atlas.


@dataclass
class AssessmentInputs:
    model_id: str
    device_key: str = "h100-sxm"
    batch: int = 1
    prompt_len: int = 2048
    gen_len: int = 512
    context_len: int | None = None
    annual_tokens: float = 1e13
    tech_node: str = "6nm"
    target_tokens_per_second: float = 1000.0
    claimed_gain: float = 100.0
    mc_samples: int | None = None
    hardened_only: bool = True

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Assessment:
    """Resultado completo de um ciclo de analise para um modelo."""

    inputs: AssessmentInputs
    spec: ModelSpec
    graph: Graph
    device: Device
    fingerprint: dict[str, Any]
    stability: StabilityReport
    stability_by_block: dict[str, Finding]
    invariants: list[Invariant]
    serving: ServingProfile
    quant: PlanEvaluation
    candidates: list[HardeningCandidate]
    part: Partition
    design: DesignPoint
    economics: EconomicsResult
    srs: ScoreCard
    sens_lhs: SensitivityResult
    findings: FindingSet
    run_id: str
    generated_at: str

    # ---------------------------------------------------------------- construcao ---
    @classmethod
    def build(cls, inputs: AssessmentInputs, corpus_dir: Path | None = None) -> "Assessment":
        reg = Registry.load(corpus_dir)
        spec = reg[inputs.model_id]
        graph = build_graph(spec)
        device = get_device(inputs.device_key)

        corpus_views = [ModelView.of(s) for s in reg]
        family_views = [v for v in corpus_views if v.spec.family == spec.family]
        stability = family_stability(family_views)
        stab_blocks = block_role_stability(family_views, corpus_views)
        invs = discover_invariants(corpus_views, level="exact")

        serving = serving_profile(
            graph,
            device,
            batch=inputs.batch,
            prompt_len=inputs.prompt_len,
            gen_len=inputs.gen_len,
            context_len=inputs.context_len,
            weight_precision=spec.default_dtype,
        )

        priors = QuantPriors.load()
        plan = sensitivity_plan(graph, priors, is_moe=spec.is_moe)
        quant = evaluate_plan(
            graph,
            plan,
            Workload(
                phase=Phase.DECODE,
                batch=inputs.batch,
                context_len=serving.decode.workload.context_len,
            ),
            device,
            baseline_precision=spec.default_dtype,
        )

        weights = Weights.load()
        lifetime = _lifetime_factor(stability)
        candidates = build_candidates(
            graph,
            serving,
            priors,
            weights,
            stability_by_block=stab_blocks,
            lifetime_by_family=lifetime,
            is_moe=spec.is_moe,
        )
        part = partition(candidates, model_id=spec.id, phase_label="serving")

        design = build_design_point(
            graph,
            part,
            serving.decode,
            target_tokens_per_second=inputs.target_tokens_per_second,
            precision_by_role=plan.by_role,
        )
        econ = simulate(
            design,
            serving,
            device,
            annual_tokens=inputs.annual_tokens,
            node=inputs.tech_node,
            priors=EconomicsPriors.load(),
            obsolescence_rate_per_year=stability.change_rate_per_year,
            hardened_only=inputs.hardened_only,
            samples=inputs.mc_samples,
        )

        arch_exact = stability.level_stability.get("exact")
        srs = build_srs(
            weights,
            architectural_stability=(
                Finding(
                    "A.arch_stability",
                    arch_exact,
                    Status.COMPUTATIONAL_EVIDENCE,
                    unit="[0,1]",
                    assumptions=("A-001",),
                    gaps=("G-001",),
                    note=f"familia {spec.family}: {' -> '.join(stability.versions)}",
                )
                if arch_exact is not None
                # Sem transicao temporal observada o fator entra como zero declarado, nunca
                # como 1.0 (R-004). Zero e conservador e honesto: nada foi observado sobreviver.
                else Finding(
                    "A.arch_stability",
                    0.0,
                    Status.OPEN_GAP,
                    unit="[0,1]",
                    gaps=("G-006",),
                    note=(
                        f"familia {spec.family} sem transicao temporal no corpus "
                        f"({len(stability.versions)} versao(oes)): estabilidade nao observada"
                    ),
                )
            ),
            hotspot_concentration=Finding(
                "H.concentration",
                concentration_index(serving.decode),
                Status.CONDITIONAL_RESULT,
                unit="[0,1]",
                assumptions=("A-002",),
                gaps=("G-003",),
                note="indice de Herfindahl das participacoes por papel em decode",
            ),
            annual_tokens=inputs.annual_tokens,
            perf_per_watt_gain=perf_per_watt_finding(econ),
            low_precision_robustness=low_precision_factor(candidates),
            data_availability=data_availability_factor(spec, len(family_views)),
            codesign_compatibility=codesign_compatibility_factor(candidates),
            revenue_potential=revenue_finding(econ, inputs.annual_tokens),
            obsolescence_risk=obsolescence_finding(stability.change_rate_per_year),
            nre_risk=nre_risk_finding(econ),
            case_name=spec.id,
        )
        sens = sensitivity(candidates, weights, srs)

        fs = FindingSet(title=f"Silicon Readiness Assessment — {spec.id}")
        fs.add(spec.param_finding())
        fs.extend(serving.findings())
        fs.extend(serving.decode.findings())
        fs.extend(quant.findings())
        fs.add(quantizable_cost_share(graph, serving.decode, priors, "int4"))
        fs.extend(part.findings())
        fs.add(hardening_ceiling_finding(part, inputs.claimed_gain))
        fs.extend(econ.findings())
        fs.add(srs.finding())
        fs.add(sens.finding())
        fs.add(stability.finding("exact"))

        now = _dt.datetime.now(_dt.UTC)
        return cls(
            inputs=inputs,
            spec=spec,
            graph=graph,
            device=device,
            fingerprint=model_fingerprint(spec, graph),
            stability=stability,
            stability_by_block=stab_blocks,
            invariants=invs,
            serving=serving,
            quant=quant,
            candidates=candidates,
            part=part,
            design=design,
            economics=econ,
            srs=srs,
            sens_lhs=sens,
            findings=fs,
            run_id=now.strftime("%Y%m%dT%H%M%SZ"),
            generated_at=now.isoformat(timespec="seconds"),
        )

    # ------------------------------------------------------------------ decisao ---
    @property
    def weights(self) -> Weights:
        return Weights.load()

    @property
    def recommendation(self) -> str:
        return self.weights.band_for(self.srs.score)

    @property
    def decidable(self) -> bool:
        """Exige as duas condicoes: ranking estavel **e** margem acima do ruido.

        A versao original do falsificador F3 exigia apenas estabilidade de ranking, e por isso
        aprovava casos em que o lider vencia por menos que a incerteza dos pesos. Ver CE-001.
        """
        return self.sens_lhs.decidable and self.sens_lhs.discriminates

    @property
    def verdict(self) -> str:
        """Recomendacao em uma frase, com a ressalva que a evidencia impoe."""
        band = {
            "software": "manter em software; nenhuma especializacao se justifica com a evidencia atual",
            "optimized_kernel": "investir em kernels otimizados antes de qualquer hardware",
            "fpga": "prototipar em FPGA; nao ha base para comprometer mascara",
            "ip_block": "desenvolver bloco de IP parametrizado para o padrao dominante",
            "asic_architecture": "ASIC por arquitetura e defensavel; pesos permanecem carregaveis",
            "weights_partially_fixed": "fixar parcialmente pesos do caminho dominante e manter deltas programaveis",
        }[self.recommendation]
        return band

    @property
    def caveats(self) -> list[str]:
        """Ressalvas que qualificam o veredito, cada uma como afirmacao separada.

        Ficam fora do veredito porque encavalar tres qualificacoes numa frase unica produzia um
        periodo ilegivel — e porque cada uma delas pede uma **acao diferente**.
        """
        from .partition import Blocker

        out: list[str] = []
        por_estabilidade = self.part.blocked_share(Blocker.STABILITY)
        por_irregular = self.part.blocked_share(Blocker.IRREGULAR)

        if self.part.hardened_share <= 0.0 and por_estabilidade >= 0.3:
            out.append(
                f"**{por_estabilidade:.0%} do custo** esta em operadores regulares e quantizaveis, "
                f"barrados *apenas pela estabilidade*. Acao util: prototipar em FPGA para medir o "
                f"ganho real antes de qualquer compromisso de mascara."
            )
        if por_irregular >= 0.3:
            out.append(
                f"**{por_irregular:.0%} do custo** esta em operadores *irregulares* (enderecamento "
                f"dependente de dado). Nenhuma quantidade de observacao de versoes os torna "
                f"endureciveis: exigem reprojeto do operador, nao espera."
            )
        if not self.decidable:
            out.append(
                f"O ranking de candidatos nao sobreviveu a perturbacao de "
                f"{self.sens_lhs.perturbation:.0%} nos pesos (**F3 disparado**). Tratar a ordem "
                f"como indicacao, nao como recomendacao — ver CE-001."
            )
        if self.economics.not_applicable:
            out.append(
                "Sem regiao fixa nao ha projeto: os fatores P, R e N do SRS entram como zero "
                "declarado e **F4 fica nao avaliavel**. Nenhum numero de PPA ou break-even e "
                "emitido."
            )
        return out

    @property
    def cross_family_reach(self) -> float:
        """Maior cobertura de corpus entre os padroes presentes neste modelo.

        Responde a pergunta comercial que a estabilidade de versao nao responde: um bloco de
        IP construido para este modelo serve quantos outros modelos do corpus?
        """
        mine = {fp.exact for k, fp in _layer_fps(self).items()}
        best = 0.0
        for inv in self.invariants:
            if inv.key in mine:
                best = max(best, inv.coverage)
        return best

    @property
    def cross_family_patterns(self) -> list[Invariant]:
        """Padroes deste modelo que aparecem em mais de uma familia do corpus."""
        mine = {fp.exact for fp in _layer_fps(self).values()}
        return [
            i
            for i in self.invariants
            if i.key in mine and len({m.split("-")[0] for m in i.models}) > 1
        ]

    def falsifier_status(self) -> dict[str, dict[str, Any]]:
        """Estado de cada criterio de falha declarado antes do experimento."""
        within_family = self.stability.level_stability.get("exact")
        no_transition = within_family is None
        return {
            "F1": {
                "criterio": "nenhum padrao com cobertura >= 0.80 entre versoes da familia",
                "observado": (
                    f"familia sem transicao temporal no corpus "
                    f"({len(self.stability.versions)} versao(oes)): nao avaliavel"
                    if no_transition
                    else f"estabilidade exata entre versoes = {within_family:.2f}; "
                         f"alcance cross-familia do melhor padrao = {self.cross_family_reach:.2f}"
                ),
                # None, nao False: um falsificador nao avaliavel nao e um falsificador que passou.
                "disparado": None if no_transition else within_family < 0.80,
            },
            "F2": {
                "criterio": "o padrao mais custoso muda de identidade entre versoes",
                "observado": self._top_role_stability_note(),
                "disparado": self._top_role_changed(),
            },
            "F3": {
                "criterio": (
                    "top-1 do ranking troca sob perturbacao de +-20% dos pesos, ou vence por "
                    "margem menor que o ruido (criterio reforcado apos CE-001)"
                ),
                "observado": (
                    f"estabilidade do top-1 = {self.sens_lhs.top1_stability:.3f} "
                    f"(limite {self.sens_lhs.threshold}); margem = {self.sens_lhs.margin:.4f} "
                    f"contra ruido {self.sens_lhs.noise_band:.4f}"
                ),
                "disparado": not self.decidable,
            },
            "F4": self._f4_status(),
            "F5": {
                "criterio": "erro de contagem de parametros acima de 5%",
                "observado": self._param_error_note(),
                "disparado": self._param_error() > 0.05,
            },
        }

    def _f4_status(self) -> dict[str, Any]:
        """F4 so e avaliavel se existir break-even para comparar.

        Antes de R-003, um `inf` fabricado por regiao fixa vazia disparava F4 e sustentava a
        conclusao de governanca "rota ASIC nao financiavel". A conclusao continua valendo — por
        outro motivo, registrado —, mas o falsificador nao pode disparar sobre objeto inexistente.
        """
        criterio = "break-even P50 posterior a vida economica"
        if self.economics.not_applicable:
            return {
                "criterio": criterio,
                "observado": f"nao avaliavel: {self.economics.reason}",
                "disparado": None,
            }
        be = self.economics.pct("breakeven_years")["p50"]
        life = float(self.economics.pct("asic_life_years")["p50"])
        return {
            "criterio": criterio,
            "observado": f"break-even P50 = {_fmt_years(be)}; vida P50 = {life:.2f} anos",
            "disparado": be > life,
        }

    def _param_error(self) -> float:
        if not self.spec.published_params:
            return 0.0
        return abs(self.spec.param_count() - self.spec.published_params) / self.spec.published_params

    def _param_error_note(self) -> str:
        if not self.spec.published_params:
            return "contagem publicada indisponivel"
        return f"erro = {self._param_error():.4%}"

    @property
    def costliest_candidate(self) -> HardeningCandidate | None:
        """Candidato com maior participacao de custo.

        F2 fala do *padrao mais custoso*; usar `candidates[0]` avaliava o primeiro do ranking
        LHS, que e outra coisa. No Mixtral isso apontava para `lm_head` (1,0 % do custo) em vez
        de `expert_gate_proj` (29,0 %), e o falsificador nao disparava. Ver R-002.
        """
        return max(self.candidates, key=lambda c: c.cost_share) if self.candidates else None

    def _top_role_changed(self) -> bool:
        top = self.costliest_candidate
        if top is None:
            return True
        f = self.stability_by_block.get(top.block_role)
        return f is None or f.value is None or float(f.value) < 0.5

    def _top_role_stability_note(self) -> str:
        top = self.costliest_candidate
        if top is None:
            return "sem candidatos"
        f = self.stability_by_block.get(top.block_role)
        val = f"{float(f.value):.2f}" if f is not None and f.value is not None else "n/d"
        return (
            f"bloco mais custoso '{top.block_role}' (papel {top.role}, "
            f"{top.cost_share:.1%} do custo): E = {val}"
        )

    # ------------------------------------------------------------------- saidas ---
    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "inputs": self.inputs.as_dict(),
            "model": self.spec.as_dict(),
            "device": self.device.as_dict(),
            "fingerprint": self.fingerprint,
            "stability": self.stability.as_dict(),
            "serving_profile": self.serving.summary(),
            "decode_profile": self.serving.decode.summary(),
            "prefill_profile": self.serving.prefill.summary(),
            "quantization": self.quant.as_dict(),
            "candidates": [c.as_dict() for c in self.candidates],
            "partition": self.part.as_dict(),
            "economics": self.economics.as_dict(),
            "srs": self.srs.as_dict(),
            "recommendation": self.recommendation,
            "verdict": self.verdict,
            "sensitivity": self.sens_lhs.as_dict(),
            "falsifiers": self.falsifier_status(),
            "findings": self.findings.as_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=False, default=str)

    def render(self, *, allow_lint_failure: bool = False) -> str:
        """Renderiza o relatorio, aplicando o portao de emissao."""
        sections = _render_sections(self)
        missing = [s for s in MANDATORY_SECTIONS if not sections.get(s, "").strip()]
        if missing:
            raise EmissionRefused(
                f"secoes obrigatorias ausentes (Metodo 3.3): {missing}"
            )
        if self.sens_lhs.samples == 0:
            raise EmissionRefused("analise de sensibilidade nao executada; ver ADR-0002 e C-006")

        # Nenhum numero nao-finito sai daqui. Um NaN chegou a afirmacao principal de quatro
        # relatorios antes desta guarda existir (R-003): o portao vigiava o contrato textual e
        # nao a aritmetica do que passava por ele.
        nao_finitos = [
            f.name
            for f in self.findings.items
            if isinstance(f.value, float) and not math.isfinite(f.value)
        ]
        if nao_finitos:
            raise EmissionRefused(
                f"Finding numerico nao-finito: {nao_finitos}. Uma grandeza indefinida deve ser "
                f"declarada como ausencia (value=None, OPEN_GAP), nunca publicada como numero."
            )

        text = _assemble(self, sections)
        problems = lint_text(text)
        if problems and not allow_lint_failure:
            detail = "; ".join(f"linha {p.line_no}: {p.term} ({p.reason})" for p in problems[:5])
            raise EmissionRefused(f"vocabulario proibido no relatorio (Metodo 3.2): {detail}")
        return text


def _layer_fps(a: "Assessment") -> dict[str, Any]:
    """Fingerprints dos blocos de camada do modelo avaliado."""
    from .fingerprint import fingerprint_graph

    fps = fingerprint_graph(a.graph, a.spec)
    return {k: v for k, v in fps.items() if k.startswith("L")}


def _lifetime_factor(stability: StabilityReport, horizon_years: float = 4.0) -> Finding:
    """L — vida util esperada, como probabilidade de sobrevivencia estrutural no horizonte."""
    rate = stability.change_rate_per_year
    if rate is None:
        return Finding(
            "L.lifetime", 0.0, Status.OPEN_GAP, unit="[0,1]", gaps=("G-006",),
            note=(
                f"sem transicao temporal na familia ({stability.transitions} transicao(oes)): "
                f"vida util nao estimavel"
            ),
        )
    import math

    surv = math.exp(-rate * horizon_years)
    return Finding(
        "L.lifetime",
        surv,
        Status.COMPUTATIONAL_EVIDENCE,
        unit="[0,1]",
        assumptions=("A-007",),
        gaps=("G-006",),
        note=(
            f"P(sobrevive {horizon_years:g} anos) com taxa observada {rate:.2f}/ano, "
            f"estimada de apenas {stability.transitions} transicao(oes) de versao: "
            f"estimativa ruidosa, ver G-006"
        ),
    )


# --------------------------------------------------------------------------------------
# Renderizacao
# --------------------------------------------------------------------------------------


def _fmt_money(x: float) -> str:
    if x >= 1e9:
        return f"US$ {x / 1e9:.2f} bi"
    if x >= 1e6:
        return f"US$ {x / 1e6:.1f} M"
    if x >= 1e3:
        return f"US$ {x / 1e3:.1f} mil"
    return f"US$ {x:.2f}"


def _fmt_years(x: float) -> str:
    if x == float("inf"):
        return "nunca"
    if x > 100:
        return f"{x:.0f} anos"
    return f"{x:.2f} anos"


def _pct_or_gap(x: float | None) -> str:
    """Percentual, ou a declaracao da ausencia — nunca `nan%`.

    Um NaN atravessou o pipeline ate a afirmacao principal de quatro relatorios (R-003). Aqui a
    ausencia vira texto que diz o que falta e qual lacuna a cobre.
    """
    if x is None:
        return "nao estimavel: taxa de obsolescencia nao observada (`G-006`)"
    return f"{x:.1%}"


def _render_sections(a: Assessment) -> dict[str, str]:
    # Percentis sao lidos dentro de `_econ_block`, que primeiro verifica `not_applicable`.
    # Le-los aqui, incondicionalmente, era o caminho pelo qual numeros de um projeto inexistente
    # chegavam ao documento (R-002).
    hyp = "\n".join(
        [
            "1. **H1 — Estabilidade parcial**: blocos do caminho dominante permanecem "
            "estruturalmente estaveis entre versoes.",
            "2. **H2 — Valor concentrado**: poucos padroes concentram a maior parte do custo.",
            "3. **H3 — Hibrido domina**: fixar apenas o estavel supera fixar tudo, ajustado ao risco.",
            "4. **H4 — Baixa precisao viabiliza**: tolerancia a INT4/ternario amplia o candidato.",
        ]
    )

    deps = "\n".join(
        f"- `{g}` — {d}"
        for g, d in [
            ("A-001", "a IR e derivada de configuracao, nao tracada do modelo real (ADR-0001)"),
            ("A-002/A-005", "roofline analitico com eficiencia assumida, nao calibrada"),
            ("A-003", "energia por byte e por FLOP em ordem de grandeza"),
            ("A-004", "tolerancia a quantizacao e prior de literatura, nao medicao"),
            ("A-006/A-008", "custos de mascara, wafer e densidade de area sao faixas publicas"),
            ("A-007", "taxa de mudanca futura extrapola o historico curto do corpus"),
        ]
    )
    deps += "\n\nLacunas abertas que limitam o status de tudo acima: " + ", ".join(
        f"`{g}`" for g in a.findings.open_gaps
    )

    fals = "\n".join(
        f"- **{k}** — {v['criterio']}  \n  observado: {v['observado']}  \n  "
        f"**{'DISPARADO' if v['disparado'] else 'nao disparado'}**"
        for k, v in a.falsifier_status().items()
    )

    top = a.candidates[:8]
    cand_table = "\n".join(
        f"| {c.role} | {c.block_role} | {c.cost_share:.1%} | {c.instances_per_token:.0f} | "
        f"{c.precision} | {c.lhs:.3f} |"
        for c in top
    )

    hot = a.serving.hotspots(8)
    hot_table = "\n".join(f"| {r} | {d['share']:.2%} |" for r, d in hot)

    results = f"""
### Perfil de execucao — {a.device.name}

Requisicao de referencia: prompt {a.inputs.prompt_len}, geracao {a.inputs.gen_len},
lote {a.inputs.batch}, contexto {a.serving.decode.workload.context_len}, pesos {a.spec.default_dtype}.

| Metrica | Prefill | Decode |
|---|---|---|
| tokens/s | {a.serving.prefill.tokens_per_second:,.0f} | {a.serving.decode.tokens_per_second:,.1f} |
| intensidade aritmetica (FLOP/byte) | {a.serving.prefill.mean_intensity:.1f} | {a.serving.decode.mean_intensity:.2f} |
| ponto de inflexao do dispositivo | {a.device.ridge_point(a.spec.default_dtype, Phase.PREFILL):.0f} | {a.device.ridge_point(a.spec.default_dtype, Phase.DECODE):.0f} |
| tempo limitado por memoria | {a.serving.prefill.memory_bound_share:.1%} | {a.serving.decode.memory_bound_share:.1%} |
| energia por token | {a.serving.prefill.energy_per_token * 1e3:.2f} mJ | {a.serving.decode.energy_per_token * 1e3:.1f} mJ |

O decode consome {a.serving.decode_time_share:.1%} do tempo da requisicao. Toda decisao de
hardening abaixo e ponderada por essa mistura, nao por FLOPs isolados.

### Onde o custo esta

| Papel | Participacao na requisicao |
|---|---|
{hot_table}

### Candidatos a endurecimento (LHS)

| Papel | Bloco | Custo | Instancias/token | Precisao | LHS |
|---|---|---|---|---|---|
{cand_table}

### Particao recomendada

```text
{a.part.as_text()}
```

Nivel de especializacao implicado: **{int(a.part.level)} — {a.part.level.label}**.
Regiao fixa cobre **{a.part.hardened_share:.1%}** do custo da requisicao.

**Teto de Amdahl da particao: {a.part.amdahl_ceiling():.2f}x.**
{_ceiling_sentence(a)}

### Quantizacao

Plano por sensibilidade reduz o **trafego de leitura de pesos por passo** em
**{a.quant.memory_reduction:.1%}** ({a.quant.weight_bytes_before / 1e9:.2f} GB para
{a.quant.weight_bytes_after / 1e9:.2f} GB por passo de decode), com aceleracao estimada de
{a.quant.speedup:.2f}x. O **footprint residente** e grandeza distinta:
{a.serving.decode.resident_weight_bytes / 1e9:.2f} GB, contra
{a.device.memory_capacity / 1e9:.0f} GB de capacidade
({'cabe' if a.serving.decode.fits_in_memory else '**NAO cabe**'},
folga {a.serving.decode.memory_headroom:+.1%}).

A perda de qualidade correspondente **nao foi medida** (`G-002`).

### PPA e economia — distribuicoes, nao pontos

{_econ_block(a)}

### Silicon Readiness Score

**SRS = {a.srs.score:.3f}** ({a.srs.finding().status.name}) -> banda **{a.recommendation}**

{_srs_table(a)}

### Efeito do escopo de comparacao

{_scope_block(a)}

### Alcance cross-familia

{_reach_block(a)}

### Estabilidade do proprio score

Perturbando os pesos em +-{a.sens_lhs.perturbation:.0%} ({a.sens_lhs.samples:,} amostras):
top-1 estavel em **{a.sens_lhs.top1_stability:.1%}** das amostras, top-3 em
{a.sens_lhs.top3_stability:.1%}, banda de decisao do SRS estavel em
{(a.sens_lhs.band_stability or 0):.1%}. Fator dominante: `{a.sens_lhs.dominant_factor}`.

Dispersao dos scores: {a.sens_lhs.score_spread:.4f}. Largura do ruido induzido pelos pesos:
{a.sens_lhs.noise_band:.4f}. **Diagnostico: {a.sens_lhs.diagnosis}.**

{_discrimination_note(a)}
"""

    limits = f"""
- A IR nao foi confrontada com um tracado real do modelo (`G-001`). Operadores fundidos,
  kernels reais e reordenacoes de grafo nao aparecem aqui.
- O roofline nao foi calibrado contra latencia medida (`G-003`). Ele acerta o **regime**
  (compute-bound vs memory-bound) com mais confianca do que acerta o valor absoluto.
- A tolerancia a quantizacao e prior de literatura (`G-002`). Nenhuma perplexidade foi medida.
- Energia de GPU vem de TDP e overhead assumidos; energia do alvo especializado vem de um
  modelo analitico (`G-004`). Comparar os dois favorece estruturalmente o alvo — o numero de
  ganho de energia deve ser lido como teto otimista, nao como previsao.
- Custos de mascara, wafer, densidade e empacotamento sao faixas publicas, nao cotacoes
  (`G-005`, `G-007`).
- A taxa de obsolescencia extrapola {len(a.stability.versions)} versao(oes) de uma familia
  (`G-006`). Uma ruptura arquitetural invalida a extrapolacao inteira.
- Nao houve revisao adversarial externa (`G-010`): autor e auditor sao o mesmo agente.
- Pesos do LHS e do SRS estao **{a.weights.calibration_status}**.
"""

    not_demonstrated = f"""
Este relatorio **nao** demonstra:

1. Que o modelo mantem qualidade sob a quantizacao proposta. Nenhuma acuracia foi medida.
2. Que o acelerador descrito e fabricavel. Nao houve sintese, floorplan, timing closure nem
   analise de potencia fisica.
3. Que os ganhos de energia se realizam. Eles saem de constantes de ordem de grandeza
   comparadas com um TDP de GPU — assimetria declarada em `A-003`.
4. Que a estrutura do modelo sobrevive ao horizonte assumido. A taxa de mudanca e extrapolacao.
5. Que {a.inputs.claimed_gain:g}x e alcancavel. {_ceiling_sentence(a)}
6. Que os numeros do unico demonstrador publico comparavel (`E-002`) sao reproduziveis: sao
   declarados pelo fabricante e nao foram verificados de forma independente.
7. Que o SRS mede prontidao real. Os pesos nunca foram calibrados contra um tape-out concluido;
   ate que sejam, o score ordena candidatos, nao prediz sucesso.
"""

    return {
        "pergunta_principal": (
            "Quais subgrafos de inferencia de "
            f"**{a.spec.id}** sao simultaneamente estaveis, dominantes em custo e tolerantes a "
            "baixa precisao o suficiente para justificar especializacao em hardware — e a partir "
            "de qual volume isso se paga?"
        ),
        "afirmacao_principal": _main_claim(a),
        "hipoteses": hyp,
        "dependencias": deps,
        "criterios_de_falha": fals,
        "resultados": results.strip(),
        "limitacoes": limits.strip(),
        "o_que_nao_demonstra": not_demonstrated.strip(),
    }


def _main_claim(a: Assessment) -> str:
    econ = a.economics
    st = a.findings.weakest
    if econ.not_applicable:
        economia = (
            f"Nao existe break-even a reportar: {econ.reason}, de modo que nenhum acelerador foi "
            f"dimensionado para {a.inputs.annual_tokens:.3g} tokens/ano."
        )
    else:
        economia = (
            f"A probabilidade de amortizar o NRE antes da obsolescencia estrutural e de "
            f"**{_pct_or_gap(econ.prob_breakeven_before_obsolescence)}** para "
            f"{a.inputs.annual_tokens:.3g} tokens/ano."
        )
    ressalvas = (
        "\n\n**Ressalvas que qualificam esta recomendacao:**\n\n"
        + "\n".join(f"{i + 1}. {c}" for i, c in enumerate(a.caveats))
        if a.caveats
        else ""
    )
    return (
        f"Sob as condicoes declaradas, a regiao endurecivel de **{a.spec.id}** cobre "
        f"**{a.part.hardened_share:.1%}** do custo de servico, o que limita o ganho de sistema a "
        f"**{a.part.amdahl_ceiling():.2f}x** numa arquitetura hibrida. {economia}\n\n"
        f"**Recomendacao: {a.verdict}.**\n\n"
        f"Status da afirmacao: `{st.name}` (elo mais fraco da cadeia de evidencia)."
        f"{ressalvas}"
    )


def _ceiling_sentence(a: Assessment) -> str:
    needed = a.part.required_speedup_for(a.inputs.claimed_gain)
    if needed is None:
        return (
            f"Um ganho de {a.inputs.claimed_gain:g}x e inalcancavel nesta particao mesmo com "
            f"aceleracao infinita na regiao fixa: exigiria mover tambem a regiao programavel "
            f"({1 - a.part.hardened_share:.1%} do custo) para o mesmo silicio."
        )
    return (
        f"Alcancar {a.inputs.claimed_gain:g}x exigiria acelerar a regiao fixa em {needed:.0f}x "
        f"mantendo o resto no host."
    )


def _discrimination_note(a: Assessment) -> str:
    """Explica *por que* o score discrimina ou nao — o achado CE-001 do ciclo."""
    s = a.sens_lhs
    if s.discriminates and s.decidable:
        return (
            f"Os fatores que efetivamente separam os candidatos neste caso sao "
            f"`{'`, `'.join(s.varying_factors)}`; os demais {s.inert_weight:.0%} do peso sao "
            f"constantes entre eles e nao contribuem para a ordem."
        )
    contenders = ", ".join(f"`{c}`" for c in s.contenders[:6])
    return (
        f"Disputam a primeira posicao, dentro do ruido: {contenders}. Entre eles, "
        f"**{s.contender_inert_weight:.0%} do peso do LHS esta em fatores identicos** — "
        f"estabilidade, regularidade, previsibilidade de memoria, volume e vida util sao os mesmos "
        f"para toda projecao linear do mesmo modelo. Sobre o conjunto completo de candidatos o "
        f"peso inerte e {s.inert_weight:.0%}.\n\n"
        f"A ordem acaba decidida apenas por `{'`, `'.join(s.varying_factors)}`, que se cancelam "
        f"parcialmente: o papel com mais custo tende a ter tolerancia a quantizacao menor.\n\n"
        f"Consequencia pratica: o LHS, com os pesos do Metodo, ordena candidatos **dentro de um "
        f"modelo** com margem menor que o proprio ruido dos pesos. Ele continua util para comparar "
        f"casos entre si (onde E, V e L de fato variam), mas nao para escolher qual projecao "
        f"endurecer primeiro. Registrado como contraexemplo CE-001; a correcao exige calibracao "
        f"dos pesos contra casos reais, nao ajuste ad hoc."
    )


def _econ_block(a: Assessment) -> str:
    econ = a.economics
    if econ.not_applicable:
        top = a.costliest_candidate
        e_top = (
            f"{float(a.stability_by_block[top.block_role].value):.2f}"
            if top and a.stability_by_block.get(top.block_role) is not None
            and a.stability_by_block[top.block_role].value is not None
            else "n/d"
        )
        return (
            f"A regiao fixa ficou **vazia** sob a politica de particionamento vigente: "
            f"{econ.reason}. Nenhum acelerador foi dimensionado, nenhum NRE foi estimado, e nao "
            f"existe break-even — nem finito, nem infinito: nao ha objeto a amortizar.\n\n"
            f"Consequencia registrada: os fatores **P** (ganho por watt), **R** (receita) e "
            f"**N** (risco de NRE) do SRS entram como **zero declarado**, e o falsificador **F4** "
            f"fica *nao avaliavel*. Publicar percentis de area, NRE ou break-even aqui seria "
            f"descrever um objeto inexistente — foi exatamente o defeito retratado em `R-002`.\n\n"
            f"Isto **e** o resultado: para {a.spec.id}, o bloco que domina o custo "
            f"({top.block_role if top else 'n/d'}, {top.cost_share:.1%} do tempo) tem "
            f"estabilidade estrutural E = {e_top}, abaixo do limite da politica. O gasto em "
            f"mascara nao tem o que financiar. A decisao economica so passa a existir se essa "
            f"estabilidade subir — por escopo declarado mais estreito, por observacao de mais "
            f"versoes, ou por calibracao da politica contra casos reais (`G-011`)."
        )

    be = econ.pct("breakeven_years")
    area = econ.pct("die_area_mm2")
    nre = econ.pct("nre_usd")
    egain = econ.pct("energy_gain")
    return f"""
Simulacao de Monte Carlo com {econ.samples:,} amostras, no {econ.node}, para
{a.inputs.annual_tokens:.3g} tokens/ano e alvo de {a.design.target_tokens_per_second:,.0f} tokens/s.
Regiao fixa: {a.design.hardened_gbit:.2f} Gbit de peso, {', '.join(a.design.hardened_roles)}.

| Grandeza | P10 | P50 | P90 |
|---|---|---|---|
| area de die | {area['p10']:.0f} mm2 | {area['p50']:.0f} mm2 | {area['p90']:.0f} mm2 |
| NRE | {_fmt_money(nre['p10'])} | {_fmt_money(nre['p50'])} | {_fmt_money(nre['p90'])} |
| ganho de energia por token | {egain['p10']:.1f}x | {egain['p50']:.1f}x | {egain['p90']:.1f}x |
| break-even | {_fmt_years(be['p10'])} | {_fmt_years(be['p50'])} | {_fmt_years(be['p90'])} |

- P(custo por token menor que GPU) = **{econ.prob_asic_cheaper:.1%}**
- P(amortizar dentro da vida util) = **{econ.prob_breakeven_within_life:.1%}**
- P(amortizar **antes da obsolescencia estrutural**) = **{_pct_or_gap(econ.prob_breakeven_before_obsolescence)}**
- P(area acima do limite de reticulo) = {econ.prob_exceeds_reticle:.1%}

Parametros que mais movem o break-even (correlacao de postos):

{_sens_list(econ)}

O primeiro item desta lista e o proximo item de pesquisa a financiar: e onde medir reduz mais
incerteza por dolar gasto.
""".strip()


def _stab(a: Assessment, level: str) -> str:
    v = a.stability.level_stability.get(level)
    return f"{v:.3f}" if v is not None else "nao observada (`G-006`)"


def _scope_block(a: Assessment) -> str:
    st = a.stability
    recent = st.recent_exact_stability
    mean = st.level_stability.get("exact")
    if recent is None or mean is None:
        return (
            f"_Familia sem transicao temporal no corpus ({len(st.versions)} versao(oes)): o "
            f"efeito de escopo nao pode ser medido, e a estabilidade estrutural entra como "
            f"lacuna aberta (`G-006`), nao como valor otimista._"
        )
    spread = st.scope_spread or 0.0
    last = st.diffs[-1]
    verdict = (
        "O escopo **muda a decisao**: os dois numeros ficam em lados opostos do limite de "
        "estabilidade da politica de particionamento."
        if (mean < 0.6 <= recent) or (recent < 0.6 <= mean)
        else "O escopo desloca o numero, mas nao atravessa o limite da politica."
    )
    return f"""
A estabilidade estrutural depende de quais versoes entram na comparacao — e essa escolha e do
analista, nao do dado.

| Escopo | Estabilidade exata |
|---|---|
| media sobre {st.transitions} transicao(oes) da familia `{st.family}` | {mean:.2f} |
| apenas a transicao mais recente ({last.older} -> {last.newer}) | {recent:.2f} |

Diferenca: {spread:+.2f}. {verdict}

Os scores deste relatorio usam a **media da familia** — a leitura conservadora. Um cliente cujo
compromisso e apenas com a linha mais recente deve reexecutar declarando esse escopo, e o
relatorio resultante sera outro documento, com outra recomendacao.
""".strip()


def _reach_block(a: Assessment) -> str:
    pats = a.cross_family_patterns
    if not pats:
        return (
            f"Nenhum bloco exato deste modelo reaparece em outra familia do corpus "
            f"(alcance maximo {a.cross_family_reach:.2f}). Um bloco de IP construido a partir "
            f"dele atende, hoje, um unico modelo."
        )
    rows = "\n".join(
        f"| {p.role} | {p.coverage:.2f} | {', '.join(p.models)} |"
        for p in sorted(pats, key=lambda x: -x.coverage)
    )
    corpus_size = len({m for i in a.invariants for m in i.models})
    return f"""
Blocos deste modelo cujo circuito **exato** ja serve outra familia — o que define o mercado
enderecavel de um bloco de IP, e nao se confunde com estabilidade temporal:

| Bloco | Cobertura do corpus | Modelos atendidos |
|---|---|---|
{rows}

Alcance maximo: **{a.cross_family_reach:.0%}** de um corpus de {corpus_size} modelos. Um bloco
estavel no tempo e util a um cliente; um bloco com alcance cross-familia e util a um mercado.
As duas propriedades sao independentes e ambas precisam ser verdadeiras para justificar IP.
""".strip()


def _sens_list(econ: EconomicsResult) -> str:
    rows = econ.sensitivity(top=5)
    if not rows:
        return "_sem variancia suficiente para decompor._"
    return "\n".join(f"{i + 1}. `{k}` (rho = {c:+.2f})" for i, (k, c) in enumerate(rows))


def _srs_table(a: Assessment) -> str:
    head = "| Fator | Valor | Peso | Contribuicao | Status |\n|---|---|---|---|---|"
    rows = [
        f"| {k} — {f.name.split('.', 1)[-1]} | {float(f.value):.3f} | "
        f"{a.srs.weights.get(k, 0):+.2f} | {a.srs.contributions[k]:+.4f} | `{f.status.name}` |"
        for k, f in a.srs.factors.items()
    ]
    return head + "\n" + "\n".join(rows)


def _assemble(a: Assessment, s: dict[str, str]) -> str:
    return f"""---
artifact: SILICON_READINESS_ASSESSMENT
model: {a.spec.id}
run_id: {a.run_id}
generated_at: {a.generated_at}
method: DOUVRAS 2.0
cycle: C-001
weakest_status: {a.findings.weakest.name}
recommendation: {a.recommendation}
decidable: {a.decidable}
---

# Silicon Readiness Assessment — {a.spec.id}

> Emitido pelo DOUVRAS Silicon Atlas. Todo numero deste documento carrega status epistemico.
> Nenhum resultado e mais forte que sua dependencia mais fraca: **{a.findings.weakest.name}**.

## 1. Pergunta principal

{s['pergunta_principal']}

## 2. Afirmacao principal

{s['afirmacao_principal']}

## 3. Hipoteses

{s['hipoteses']}

## 4. Dependencias

{s['dependencias']}

## 5. Criterios de falha (declarados antes da execucao)

{s['criterios_de_falha']}

## 6. Resultados

{s['resultados']}

## 7. Limitacoes

{s['limitacoes']}

## 8. O que este resultado NAO demonstra

{s['o_que_nao_demonstra']}

---

## Anexo A — Fingerprint arquitetural

```json
{json.dumps({k: v for k, v in a.fingerprint.items() if k != 'blocks'}, indent=2, ensure_ascii=False)}
```

## Anexo B — Estabilidade da familia `{a.spec.family}`

Versoes comparadas: {' -> '.join(a.stability.versions)}

Transicoes temporais observadas: **{a.stability.transitions}**{
    f" · pares de escala (mesma data, tamanhos diferentes) ignorados: "
    f"{', '.join(f'{x} vs {y}' for x, y in a.stability.scale_pairs)}"
    if a.stability.scale_pairs else ""
}

| Nivel de identidade | Estabilidade media |
|---|---|
| topologia | {_stab(a, 'topology')} |
| padrao (proporcoes) | {_stab(a, 'pattern')} |
| exato (mesmo circuito) | {_stab(a, 'exact')} |

Taxa de mudanca estrutural observada: {
    f"{a.stability.change_rate_per_year:.2f} por ano"
    if a.stability.change_rate_per_year is not None
    else "nao estimavel: sem transicao temporal no corpus (`G-006`)"
}

{_diff_block(a)}

## Anexo C — Proveniencia

- Modelo: `{a.spec.id}`, familia `{a.spec.family}`, licenca `{a.spec.license}`
- Fonte da configuracao: {a.spec.provenance.source_url or 'n/d'}
- Status de proveniencia: `{a.spec.provenance.provenance}`{' (lacuna G-008 aberta)' if not a.spec.provenance.verified else ''}
- Parametros derivados da IR: {a.spec.param_count():,} | publicados: {f"{a.spec.published_params:,}" if a.spec.published_params else "nao publicados (F5 nao verificavel para este modelo)"}
- Baseline de hardware: `{a.device.key}` — {a.device.source}
- Pesos de score: v{a.weights.version} ({a.weights.calibration_status})
- Priors de quantizacao: v{a.quant.plan.priors_version}

## Anexo D — Todas as afirmacoes emitidas

| Afirmacao | Valor | Status | Lacunas |
|---|---|---|---|
{chr(10).join(_finding_row(f) for f in a.findings.items)}

---

_DOUVRAS Labs — Muitas formas. Uma estrutura._
"""


def _finding_row(f: Finding) -> str:
    v = f.value
    if isinstance(v, float):
        v = f"{v:,.4g}"
    elif v is None:
        v = "—"
    gaps = ", ".join(f.gaps) or "—"
    return f"| `{f.name}` | {v} {f.unit} | `{f.status.name}` | {gaps} |"


def _diff_block(a: Assessment) -> str:
    if not a.stability.diffs:
        return "_Sem transicoes de versao no corpus para esta familia._"
    out = []
    for d in a.stability.diffs:
        changes = (
            "\n".join(f"  - `{k}`: {v[0]} -> {v[1]}" for k, v in d.changed_config.items())
            or "  - nenhuma mudanca nos campos rastreados"
        )
        out.append(
            f"**{d.older} -> {d.newer}** ({d.days_between} dias) — "
            f"estabilidade exata {d.stability['exact']:.2f}, "
            f"padrao {d.stability['pattern']:.2f}, topologia {d.stability['topology']:.2f}\n{changes}"
        )
    return "\n\n".join(out)


__all__ = [
    "Assessment",
    "AssessmentInputs",
    "EmissionRefused",
    "MANDATORY_SECTIONS",
]
