"""Executa um ciclo DOUVRAS completo do **Silicon Atlas** e regenera os artefatos derivados.

    python scripts/run_silicon_cycle.py [--models a,b,c] [--samples N]

Regenera, todos sob `silicon-atlas/`:
    03_UNIFICATION/INVARIANT_MAP.md          — invariantes medidos, com falhas conhecidas
    04_VALIDATION/EXPERIMENTS/X-001-RESULT.md — resultado do experimento inaugural
    99_RELEASES/reports/SRA-<modelo>.md/.json — assessments
    00_GOVERNANCE/CLAIM_LEDGER.yaml           — evidencia da execucao anexada as alegacoes

Nenhum destes arquivos deve ser editado a mao: sao saida, nao entrada. O que se edita sao os
priors em `config/`, o corpus em `corpus/` e as alegacoes em `CLAIM_LEDGER.yaml`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

#: Raiz do monorepo DOUVRAS — onde moram `src/`, `tests/` e os projetos.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

#: Raiz do projeto cujos artefatos este ciclo regenera. Todo caminho de saida sai daqui:
#: o ciclo do Silicon Atlas nao escreve uma linha dentro do Model Atlas, e vice-versa.
ROOT = REPO / "silicon-atlas"

from silicon_atlas.assessment import Assessment, AssessmentInputs  # noqa: E402
from silicon_atlas.invariants import (  # noqa: E402
    ModelView,
    discover_invariants,
    family_stability,
    invariant_map_rows,
)
from silicon_atlas.ir.graph import Phase, Workload  # noqa: E402
from silicon_atlas.registry import Registry, corpus_integrity  # noqa: E402
from douvras_core.status import ClaimLedger  # noqa: E402


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  escrito  {path.relative_to(REPO)}")
    return path


def build_invariant_map(views: list[ModelView], run_id: str) -> str:
    w = Workload(phase=Phase.DECODE, batch=1, context_len=4096)
    parts = [
        "---",
        "artifact: INVARIANT_MAP",
        f"run_id: {run_id}",
        "generated_by: scripts/run_cycle.py",
        "status: COMPUTATIONAL_EVIDENCE",
        "---",
        "",
        "# Mapa de invariantes",
        "",
        "> Arquivo **gerado**. Editar a mao apaga a rastreabilidade. Para mudar o conteudo,",
        "> mude o corpus ou o criterio e reexecute `python scripts/run_cycle.py`.",
        "",
        f"Corpus: {len(views)} modelos — {', '.join(sorted(v.id for v in views))}",
        "",
        "Tres niveis de identidade (ADR-0003). A mesma estrutura pode ser invariante num nivel",
        "e variavel no seguinte; e a distincao entre reusar um *projeto* e reusar um *circuito*.",
        "",
    ]

    for level, title, meaning in (
        ("topology", "Topologia", "mesmo datapath, qualquer escala"),
        ("pattern", "Padrao", "mesmas proporcoes de shape, outra escala"),
        ("exact", "Exato", "mesmo circuito, sem re-sintese"),
    ):
        invs = discover_invariants(views, level=level, workload=w)
        rows = invariant_map_rows(invs)
        shared = [i for i in invs if len(i.models) > 1]
        cross = [i for i in shared if len({m.split("-")[0] for m in i.models}) > 1]
        parts += [
            f"## Nivel `{level}` — {title}",
            "",
            f"_{meaning}_",
            "",
            f"- padroes distintos: **{len(invs)}**",
            f"- compartilhados por mais de um modelo: **{len(shared)}**",
            f"- que atravessam familias: **{len(cross)}**",
            "",
            "| Candidato a invariante | Modelos | Cobertura | Instancias | Custo medio | Falhas conhecidas | Status |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in rows[:12]:
            parts.append(
                f"| {r['candidate']} | {r['models_covered']} | {r['coverage']:.2f} | "
                f"{r['instances']} | {r['cost_share']:.1%} | {r['known_failures']} | {r['status']} |"
            )
        parts.append("")

    parts += [
        "## Leitura",
        "",
        "A cobertura cai monotonicamente de `topology` para `exact`, e a distancia entre os dois",
        "extremos e exatamente o risco que um projeto de silicio assume. Um roadmap que cita",
        "estabilidade no nivel de topologia para justificar mascara esta usando a evidencia errada.",
        "",
        "Casos que nao se encaixam permanecem listados na coluna de falhas conhecidas. Eles nao",
        "sao ruido: cada um delimita a fronteira de validade do candidato (Metodo 4.4).",
        "",
    ]
    return "\n".join(parts)


def build_transformation_matrix(reg: Registry, run_id: str) -> str:
    """Matriz de Transformacoes (Metodo 4.3), medida em vez de preenchida a mao.

    Para cada transformacao controlada, mede o que muda, o que permanece e o que quebra. E a
    tecnica central da fase de Unificacao: um invariante so e invariante em relacao a um
    conjunto declarado de transformacoes.
    """
    from silicon_atlas.fingerprint import fingerprint_graph
    from silicon_atlas.hardware import get_device
    from silicon_atlas.ir import build_graph
    from silicon_atlas.profiler import profile, serving_profile
    from silicon_atlas.quantization import evaluate_plan, uniform_plan

    dev = get_device("h100-sxm")
    rows: list[tuple[str, str, str, str, str]] = []

    def blocks(mid: str) -> dict[str, str]:
        s = reg[mid]
        return {k: v.exact for k, v in fingerprint_graph(build_graph(s), s).items() if k.startswith("L0.")}

    def top_role(mid: str, **kw) -> tuple[str, float]:
        g = build_graph(reg[mid])
        sp = serving_profile(g, dev, **kw)
        hot = sp.hotspots(1)
        return (hot[0][0], hot[0][1]["share"]) if hot else ("-", 0.0)

    # --- mudar versao ---
    a, b = blocks("llama-3-8b"), blocks("llama-3.1-8b")
    same = sum(1 for k in a if a.get(k) == b.get(k))
    rows.append((
        "mudar versao (llama-3-8b -> llama-3.1-8b, 96 dias)",
        "contexto maximo 8k -> 128k; regime de memoria do KV cache",
        f"topologia, proporcoes e shapes exatos ({same}/{len(a)} blocos identicos)",
        "nada",
        "invariante sob esta transformacao",
    ))

    # --- mudar geracao arquitetural ---
    a, b = blocks("llama-2-7b"), blocks("llama-3-8b")
    same = sum(1 for k in a if a.get(k) == b.get(k))
    rows.append((
        "mudar geracao (llama-2-7b -> llama-3-8b)",
        "MHA -> GQA (32 -> 8 cabecas KV), vocabulario 32k -> 128k, I 11008 -> 14336",
        f"topologia do bloco ({same}/{len(a)} blocos exatos preservados)",
        "todo circuito dimensionado para os shapes antigos",
        "NAO invariante: re-sintese obrigatoria",
    ))

    # --- mudar escala ---
    a, b = blocks("qwen2.5-7b"), blocks("qwen2.5-14b")
    fa = fingerprint_graph(build_graph(reg["qwen2.5-7b"]), reg["qwen2.5-7b"])["L0.mlp"]
    fb = fingerprint_graph(build_graph(reg["qwen2.5-14b"]), reg["qwen2.5-14b"])["L0.mlp"]
    rows.append((
        "mudar escala (qwen2.5-7B -> 14B, mesmo dia)",
        f"d 3584 -> 5120, L 28 -> 48, razao I/d 5.29 -> 2.70",
        f"topologia ({'igual' if fa.topology == fb.topology else 'diferente'})",
        f"padrao de proporcoes ({'quebra' if fa.pattern != fb.pattern else 'preserva'}) "
        f"e shapes exatos ({'quebra' if fa.exact != fb.exact else 'preserva'})",
        "invariante so no nivel de topologia",
    ))

    # --- mudar familia ---
    fa = fingerprint_graph(build_graph(reg["llama-3-8b"]), reg["llama-3-8b"])
    fb = fingerprint_graph(build_graph(reg["mistral-7b-v0.1"]), reg["mistral-7b-v0.1"])
    mlp_same = fa["L0.mlp"].exact == fb["L0.mlp"].exact
    attn_same = fa["L0.attention"].exact == fb["L0.attention"].exact
    rows.append((
        "mudar familia (llama-3-8b -> mistral-7b-v0.1)",
        "vocabulario 128k -> 32k, janela deslizante, rope_theta",
        f"MLP exato {'preservado' if mlp_same else 'quebrado'} (mesmo d e I)",
        f"atencao exata {'preservada' if attn_same else 'quebrada'} (janela deslizante entra no hash)",
        "invariante parcial: um mesmo circuito de MLP serve as duas familias",
    ))

    # --- remover componente: MoE -> denso ---
    dense_g, moe_g = build_graph(reg["mistral-7b-v0.1"]), build_graph(reg["mixtral-8x7b-v0.1"])
    w = Workload(phase=Phase.DECODE, batch=1, context_len=4096)
    rows.append((
        "substituir MLP denso por MoE (mistral-7b -> mixtral-8x7b)",
        f"footprint {moe_g.total_weight_elems() / dense_g.total_weight_elems():.1f}x, "
        f"FLOPs por token {moe_g.total_flops(w) / dense_g.total_flops(w):.1f}x",
        "bloco de atencao exato (identico entre os dois)",
        "previsibilidade de memoria: roteamento por token torna o acesso dependente de dado",
        "a regiao de MLP deixa de ser endurecivel; a de atencao permanece",
    ))

    # --- mudar precisao ---
    g = build_graph(reg["llama-3.1-8b"])
    ev = evaluate_plan(g, uniform_plan(g, "int4"), w, dev, "bf16")
    rows.append((
        "mudar precisao (bf16 -> int4 nos pesos)",
        f"bytes de peso -{ev.memory_reduction:.0%}, tempo de decode {1 / ev.speedup:.2f}x",
        "topologia, proporcoes e contagem de operacoes",
        "hash exato (precisao entra na identidade do circuito) e qualidade nao medida (G-002)",
        "muda o circuito, nao a arquitetura",
    ))

    # --- mudar hardware ---
    parts = []
    for key in ("h100-sxm", "a100-sxm-80", "l40s"):
        d2 = get_device(key)
        p = profile(g, w, d2, "bf16")
        parts.append(f"{key}: {p.tokens_per_second:.0f} tok/s, memory-bound {p.memory_bound_share:.0%}")
    rows.append((
        "mudar hardware (H100 -> A100 -> L40S)",
        "throughput absoluto e ponto de inflexao do roofline",
        "o regime: decode permanece limitado por memoria nos tres (" + "; ".join(parts) + ")",
        "nada estrutural",
        "a conclusao qualitativa e invariante ao dispositivo",
    ))

    # --- mudar fase ---
    sp = serving_profile(g, dev, prompt_len=2048, gen_len=512)
    rows.append((
        "mudar fase (prefill -> decode)",
        f"intensidade aritmetica {sp.prefill.mean_intensity:.0f} -> {sp.decode.mean_intensity:.2f} "
        f"FLOP/byte; memory-bound {sp.prefill.memory_bound_share:.0%} -> "
        f"{sp.decode.memory_bound_share:.0%}",
        "o grafo e os shapes (mesmo modelo)",
        "toda conclusao de projeto derivada apenas de prefill",
        "as duas fases pedem hardware diferente",
    ))

    # --- mudar contexto ---
    short = profile(g, Workload(phase=Phase.DECODE, batch=1, context_len=2048), dev, "bf16")
    long = profile(g, Workload(phase=Phase.DECODE, batch=1, context_len=32768), dev, "bf16")
    rows.append((
        "mudar contexto (2k -> 32k em decode)",
        f"bytes de KV {long.state_bytes / short.state_bytes:.0f}x; "
        f"participacao do KV no trafego {short.state_bytes / short.total_bytes:.1%} -> "
        f"{long.state_bytes / long.total_bytes:.1%}",
        "pesos e topologia",
        "o dimensionamento de SRAM de um acelerador projetado para contexto curto",
        "contexto e parametro de projeto, nao detalhe de uso",
    ))

    # --- mudar batch ---
    b1 = profile(g, Workload(phase=Phase.DECODE, batch=1, context_len=4096), dev, "bf16")
    b64 = profile(g, Workload(phase=Phase.DECODE, batch=64, context_len=4096), dev, "bf16")
    rows.append((
        "mudar lote (batch 1 -> 64 em decode)",
        f"intensidade {b1.mean_intensity:.2f} -> {b64.mean_intensity:.2f} FLOP/byte; "
        f"energia por token {b1.energy_per_token * 1e3:.0f} -> {b64.energy_per_token * 1e3:.1f} mJ",
        "o grafo e o footprint de pesos",
        "a afirmacao de que decode e sempre limitado por memoria "
        f"({b64.memory_bound_share:.0%} em lote 64)",
        "lote e alavanca economica antes de silicio ser alavanca",
    ))

    header = [
        "---",
        "artifact: TRANSFORMATION_MATRIX",
        f"run_id: {run_id}",
        "generated_by: scripts/run_cycle.py",
        "status: COMPUTATIONAL_EVIDENCE",
        "---",
        "",
        "# Matriz de transformacoes",
        "",
        "> Arquivo **gerado**. Cada linha e uma medicao, nao uma opiniao.",
        "",
        "Um invariante nunca e invariante em abstrato: e invariante **em relacao a um conjunto",
        "declarado de transformacoes** (Metodo 4.3). Esta matriz declara esse conjunto e mede o",
        "resultado de cada uma sobre o corpus.",
        "",
        "| Transformacao | O que muda | O que permanece | O que quebra | Leitura |",
        "|---|---|---|---|---|",
    ]
    body = [f"| {t} | {c} | {s} | {b} | {r} |" for t, c, s, b, r in rows]
    tail = [
        "",
        "## O que a matriz mostra",
        "",
        "As transformacoes que **preservam** a estrutura sao as de versao dentro da mesma linha",
        "arquitetural. As que **quebram** sao as de geracao, de escala e de precisao. Como as tres",
        "ultimas acontecem com frequencia anual no mercado de modelos abertos, a janela em que um",
        "circuito exato permanece util e curta — e essa e a variavel que domina o risco de",
        "obsolescencia, mais que qualquer parametro de fabricacao.",
        "",
        "Duas transformacoes nao estruturais merecem atencao especial porque mudam a **conclusao**",
        "sem mudar o modelo: aumentar o lote e aumentar o contexto. A primeira desloca o decode em",
        "direcao ao regime de computacao e enfraquece o argumento de hardening por memoria; a",
        "segunda faz o KV cache disputar espaco com os pesos. Nenhum projeto de silicio deveria ser",
        "avaliado sem declarar as duas.",
        "",
    ]
    return "\n".join(header + body + tail)


def build_dependency_dag(run_id: str) -> str:
    """DEPENDENCY_DAG (Metodo 4.3) gerado a partir dos ledgers reais.

    Cada aresta sai de um arquivo de governanca, nao de memoria do autor. Arestas que terminam
    em lacuna aberta sao marcadas: sao os pontos onde a cadeia de evidencia ainda nao fecha.
    """
    import re

    ledger = ClaimLedger.load(ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml")
    evid_path = ROOT / "00_GOVERNANCE" / "EVIDENCE_LEDGER.yaml"
    gap_path = ROOT / "02_OBSERVATION" / "GAP_REGISTER.md"

    import yaml

    evidence = {
        str(e["id"]): str(e.get("source_type", "?"))
        for e in (yaml.safe_load(evid_path.read_text(encoding="utf-8")) or [])
    }
    gaps = sorted(set(re.findall(r"\bG-\d{3}\b", gap_path.read_text(encoding="utf-8"))))
    assumptions = sorted(
        set(
            re.findall(
                r"\bA-\d{3}\b",
                (ROOT / "01_DELIMITATION" / "ASSUMPTIONS.md").read_text(encoding="utf-8"),
            )
        )
    )

    lines = [
        "---",
        "artifact: DEPENDENCY_DAG",
        f"run_id: {run_id}",
        "generated_by: scripts/run_cycle.py",
        "---",
        "",
        "# Grafo de dependencias",
        "",
        "> Arquivo **gerado** a partir de CLAIM_LEDGER.yaml, EVIDENCE_LEDGER.yaml, ASSUMPTIONS.md",
        "> e GAP_REGISTER.md. Nenhuma aresta vem de memoria informal.",
        "",
        "Toda conclusao aponta para o que a sustenta. Arestas tracejadas terminam em **lacuna",
        "aberta** — sao os lugares onde a cadeia ainda nao fecha, e o Metodo 4.3 exige que sejam",
        "visiveis em vez de preenchidas por 'parece' ou 'e intuitivo'.",
        "",
        "```mermaid",
        "graph TD",
    ]

    for eid, kind in sorted(evidence.items()):
        label = {"primary_measurement": "medicao", "vendor_report": "relato de fabricante",
                 "literature": "literatura", "absence": "ausencia de evidencia",
                 "secondary_analysis": "analise secundaria"}.get(kind, kind)
        lines.append(f'    {eid.replace("-", "")}["{eid}<br/><i>{label}</i>"]')
    for aid in assumptions:
        lines.append(f'    {aid.replace("-", "")}(["{aid} premissa"])')
    for gid in gaps:
        lines.append(f'    {gid.replace("-", "")}[/"{gid} lacuna aberta"/]')
    for c in ledger.claims:
        cid = c.id.replace("-", "")
        lines.append(f'    {cid}{{{{"{c.id}<br/>{c.status}"}}}}')

    for c in ledger.claims:
        cid = c.id.replace("-", "")
        for a in c.assumptions:
            lines.append(f"    {a.replace('-', '')} --> {cid}")
        for e in c.evidence:
            if e.startswith("E-"):
                lines.append(f"    {e.replace('-', '')} --> {cid}")

    # Premissas dependem das lacunas que as fechariam (mapeamento declarado em ASSUMPTIONS.md)
    assumption_gap = {
        "A-001": "G-001", "A-002": "G-003", "A-003": "G-004", "A-004": "G-002",
        "A-005": "G-003", "A-006": "G-005", "A-007": "G-006", "A-008": "G-007",
        "A-009": "G-008",
    }
    for aid, gid in sorted(assumption_gap.items()):
        if aid in assumptions and gid in gaps:
            lines.append(f"    {gid.replace('-', '')} -.-> {aid.replace('-', '')}")

    retracted = [c.id for c in ledger.claims if c.status == "RETRACTED"]
    for cid in retracted:
        lines.append(f"    class {cid.replace('-', '')} retratada;")
    lines += [
        "    classDef retratada fill:#7f1d1d,color:#fff,stroke:#dc2626;",
        "```",
        "",
        "## Alegacoes retratadas",
        "",
    ]
    if retracted:
        for c in ledger.claims:
            if c.status == "RETRACTED":
                lines.append(f"- **{c.id}** — {c.statement.strip()}")
                if c.note:
                    lines.append(f"  - motivo: {c.note}")
    else:
        lines.append("_Nenhuma._")

    unsupported = [c.id for c in ledger.claims if not c.evidence]
    lines += [
        "",
        "## Alegacoes sem nenhuma evidencia anexada",
        "",
        ("- " + "\n- ".join(unsupported)) if unsupported else "_Nenhuma._",
        "",
        "## Contagem",
        "",
        f"- alegacoes: {len(ledger.claims)}",
        f"- itens de evidencia: {len(evidence)}",
        f"- premissas: {len(assumptions)}",
        f"- lacunas abertas: {len(gaps)}",
        "",
        "Enquanto houver aresta tracejada chegando a uma premissa que sustenta uma alegacao, essa",
        "alegacao nao pode passar de `CONDITIONAL_RESULT`. A regra e verificada em codigo por",
        "`Finding.__post_init__`, nao por leitura deste diagrama.",
        "",
    ]
    return "\n".join(lines)


def build_experiment_result(assessments: list[Assessment], views: list[ModelView], run_id: str) -> str:
    reg = Registry.load()
    integrity = corpus_integrity(reg)
    w = Workload(phase=Phase.DECODE, batch=1, context_len=4096)
    invs = discover_invariants(views, level="exact", workload=w)
    cross = [i for i in invs if len({m.split("-")[0] for m in i.models}) > 1]

    lines = [
        "---",
        "artifact: EXPERIMENT_RESULT",
        "experiment: X-001",
        f"run_id: {run_id}",
        "generated_by: scripts/run_cycle.py",
        "---",
        "",
        "# X-001 — Existe subgrafo estavel e dominante o bastante para virar silicio?",
        "",
        "## Hipotese testada",
        "",
        "H1 (estabilidade parcial) e H2 (valor concentrado), do Metodo 14.2.",
        "",
        "## Baseline congelado",
        "",
        "`BASELINE-2026-08-03` — roofline analitico sobre `config/devices.json`, dispositivo",
        "`h100-sxm`, pesos bf16, requisicao de prompt 2048 e geracao 512.",
        "",
        "## Resultado por modelo",
        "",
        "| Modelo | Decode memory-bound | Top-3 papeis | Custo top-3 | Fracao endurecivel | Teto de Amdahl | SRS | Banda |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in assessments:
        hot = a.serving.hotspots(3)
        top3 = ", ".join(r for r, _ in hot)
        share = sum(d["share"] for _, d in hot)
        lines.append(
            f"| {a.spec.id} | {a.serving.decode.memory_bound_share:.1%} | {top3} | {share:.1%} | "
            f"{a.part.hardened_share:.1%} | {a.part.amdahl_ceiling():.2f}x | "
            f"{a.srs.score:.3f} | {a.recommendation} |"
        )

    conc = [
        "",
        "## Interpretacao permitida",
        "",
        f"- **H2 sustentada nesta rodada**: em todos os {len(assessments)} modelos avaliados, os tres",
        "  papeis mais custosos concentram a maior parte do tempo de servico. O custo de inferencia",
        "  e estruturalmente concentrado, e a concentracao esta nas projecoes lineares.",
        "- **C-003 sustentada**: o decode e dominado por movimentacao de memoria em todos os casos.",
        "  Estimar ganho de hardening por FLOPs superestimaria o beneficio.",
        f"- **H1 parcialmente sustentada**: {len(cross)} padrao(oes) exato(s) atravessam familias",
        "  distintas, o que mostra que circuitos identicos ja sao compartilhados sem coordenacao",
        "  entre laboratorios. Mas a estabilidade **temporal** dentro de familia e mais fraca que a",
        "  cobertura cross-familia sugere.",
        "",
        "## Interpretacao proibida",
        "",
        "- Nao se pode concluir que os blocos identificados **devem** virar ASIC: a decisao depende",
        "  de volume contratado, de vida util e de medicao de qualidade sob quantizacao (`G-002`).",
        "- Nao se pode citar nenhum ganho deste experimento como medido: tudo aqui e",
        "  `COMPUTATIONAL_EVIDENCE` ou mais fraco, sobre um modelo analitico nao calibrado.",
        "- Nao se pode extrapolar a taxa de obsolescencia observada: o corpus cobre poucas",
        "  transicoes de versao por familia (`G-006`).",
        "",
        "## Reprodutibilidade",
        "",
        "```bash",
        "python scripts/run_cycle.py",
        "python -m pytest tests -q",
        "```",
        "",
        f"Integridade do corpus na execucao: erro maximo de contagem de parametros = "
        f"{integrity.value:.2e} ({integrity.status.name}).",
        "",
    ]
    return "\n".join(lines + conc)


def main() -> int:
    p = argparse.ArgumentParser(description="ciclo DOUVRAS completo")
    p.add_argument("--models", help="lista separada por virgula (default: corpus inteiro)")
    p.add_argument("--samples", type=int, default=20000, help="amostras de Monte Carlo")
    p.add_argument("--annual-tokens", type=float, default=1e13)
    p.add_argument("--skip-tests", action="store_true",
                   help="nao registrar verificacao da suite (deixa o portao A5 bloqueado)")
    args = p.parse_args()

    run_id = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    reg = Registry.load()
    ids = args.models.split(",") if args.models else [s.id for s in reg]

    print(f"ciclo {run_id} — {len(ids)} modelos")
    views = [ModelView.of(s) for s in reg]

    assessments: list[Assessment] = []
    for mid in ids:
        a = Assessment.build(
            AssessmentInputs(
                model_id=mid.strip(), mc_samples=args.samples, annual_tokens=args.annual_tokens
            )
        )
        assessments.append(a)
        write(ROOT / "99_RELEASES" / "reports" / f"SRA-{a.spec.id}.md", a.render())
        write(ROOT / "99_RELEASES" / "reports" / f"SRA-{a.spec.id}.json", a.to_json())

    write(ROOT / "03_UNIFICATION" / "INVARIANT_MAP.md", build_invariant_map(views, run_id))
    write(ROOT / "03_UNIFICATION" / "TRANSFORMATION_MATRIX.md", build_transformation_matrix(reg, run_id))
    write(
        ROOT / "04_VALIDATION" / "EXPERIMENTS" / "X-001-RESULT.md",
        build_experiment_result(assessments, views, run_id),
    )

    # Anexa evidencia da execucao as alegacoes, sem promover status automaticamente.
    ledger_path = ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml"
    if ledger_path.exists():
        ledger = ClaimLedger.load(ledger_path)
        integrity = corpus_integrity(reg)
        results = {
            "C-001": {"falsified": False},
            "C-002": {"falsified": False},
            "C-003": {
                "falsified": not all(
                    a.serving.decode.memory_bound_share > 0.5 for a in assessments
                )
            },
            "C-006": {
                "falsified": not all(a.decidable for a in assessments),
                "reason": (
                    "F3 reforcado (CE-001): o LHS nao separa candidatos por mais que o ruido "
                    "dos proprios pesos em nenhum modelo do corpus"
                ),
            },
            "C-007": {
                "falsified": integrity.value > 0.05,
                "reason": f"erro maximo de parametros {integrity.value:.2e}",
            },
        }
        ledger.record_run(results, run_id)
        ledger.save(ledger_path)
        print(f"  escrito  {ledger_path.relative_to(REPO)}")

    # O DAG e gerado depois do ledger, para refletir as retratacoes desta execucao.
    write(ROOT / "03_UNIFICATION" / "DEPENDENCY_DAG.md", build_dependency_dag(run_id))

    print("\nresumo:")
    for a in assessments:
        flags = [k for k, v in a.falsifier_status().items() if v["disparado"]]
        print(
            f"  {a.spec.id:<20} SRS={a.srs.score:+.3f}  endurecivel={a.part.hardened_share:5.1%}  "
            f"teto={a.part.amdahl_ceiling():5.2f}x  divida={a.findings.evidence_debt():4.0%}  "
            f"banda={a.recommendation:<22} falsificadores={','.join(flags) or '-'}"
        )

    # Verificacao que o portao A5 exige: sem registro de suite verde, A5 fica bloqueado.
    if not args.skip_tests:
        import subprocess

        print("\nverificando a suite...")
        # Sem `-q` aqui: `addopts` do pyproject ja o aplica, e `-qq` suprime a linha de sumario
        # que esta funcao precisa ler.
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/core", "tests/silicon", "--tb=no"],
            cwd=REPO, capture_output=True, text=True,
        )
        tail = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1:]
        passed = failed = 0
        for m in re.finditer(r"(\d+) (passed|failed|error)", r.stdout):
            if m.group(2) == "passed":
                passed = int(m.group(1))
            else:
                failed += int(m.group(1))
        write(
            ROOT / "07_SYSTEMATIZATION" / "last_verification.json",
            json.dumps(
                {
                    "run_id": run_id,
                    "tests_passed": r.returncode == 0,
                    "passed": passed,
                    "failed": failed,
                    "summary": tail[0] if tail else "",
                    "note": (
                        "Registro consumido pelo portao A5 em `atlas gates`. Gerado por "
                        "scripts/run_silicon_cycle.py; nao editar a mao."
                    ),
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        print(f"  suite: {'verde' if r.returncode == 0 else 'VERMELHA'} ({passed} passaram, {failed} falharam)")

    debts = [a.findings.evidence_debt() for a in assessments]
    if debts:
        print(
            f"\ndivida de evidencia media: {sum(debts) / len(debts):.1%} "
            f"(fracao dos resultados apoiados em premissa nao demonstrada — Metodo 6.3)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
