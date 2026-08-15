"""Interface de linha de comando do DOUVRAS Silicon Atlas.

    atlas registry list                 modelos registrados e proveniencia
    atlas fingerprint llama-3.1-8b      fingerprint arquitetural
    atlas diff llama-3-8b llama-3.1-8b  o que mudou entre versoes
    atlas stability llama               estabilidade da familia ao longo do tempo
    atlas invariants --level exact      padroes compartilhados no corpus
    atlas profile llama-3.1-8b          perfil roofline por fase
    atlas quantize llama-3.1-8b         plano de precisao e ganho estimado
    atlas score llama-3.1-8b            LHS por papel + SRS + sensibilidade
    atlas partition llama-3.1-8b        particao fixa/configuravel/programavel
    atlas economics llama-3.1-8b        break-even com incerteza propagada
    atlas assess llama-3.1-8b -o r.md   assessment completo
    atlas gates                         estado dos portoes do ciclo
    atlas lint 99_RELEASES/reports      vocabulario proibido (Metodo 3.2)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from douvras_core.gates import (
    Gate,
    count_gaps,
    external_reviews,
    has_all,
    has_numbered_falsifiers,
    summarize,
    verified_suite,
)
from douvras_core.paths import project_root
from douvras_core.status import ClaimLedger, lint_text

from .assessment import Assessment, AssessmentInputs, EmissionRefused
from .fingerprint import fingerprint_json
from .hardware import get_device, load_devices
from .invariants import (
    ModelView,
    diff_versions,
    discover_invariants,
    family_stability,
    invariant_map_rows,
)
from .ir import build_graph
from .profiler import concentration_index, dominant_roles, serving_profile
from .quantization import QuantPriors, evaluate_plan, sensitivity_plan
from .readiness import Weights, build_candidates, sensitivity
from .registry import Registry, corpus_integrity, record_verification, verify_spec

ROOT = project_root("silicon-atlas")


def _corpus(args) -> Path | None:
    """Diretorio de corpus escolhido, ou None para o padrao.

    Existe porque `--corpus` era honrada por `_reg` e ignorada por `Assessment.build`, o que
    fazia `atlas gates` misturar dois corpora no mesmo quadro de portoes.
    """
    return Path(args.corpus) if getattr(args, "corpus", None) else None


def _reg(args) -> Registry:
    return Registry.load(_corpus(args))


def _views(reg: Registry) -> list[ModelView]:
    return [ModelView.of(s) for s in reg]


# --------------------------------------------------------------------------------------


def cmd_registry(args) -> int:
    reg = _reg(args)
    if args.action == "list":
        print(f"{'id':<20}{'familia':<10}{'versao':<12}{'params':>16}  {'attn':<5}{'lic':<12}prov")
        for s in reg:
            prov = "OK" if s.provenance.verified else "TRANSCRITO (G-008)"
            print(
                f"{s.id:<20}{s.family:<10}{s.version_label:<12}{s.param_count():>16,}  "
                f"{s.attention_type:<5}{(s.license or '-'):<12}{prov}"
            )
        f = corpus_integrity(reg)
        print(f"\n{f}")
        print(f"  {f.note}")
        if reg.errors:
            print(f"\nmodelos rejeitados: {reg.errors}")
    elif args.action == "show":
        if not args.model:
            print("uso: atlas registry show <modelo>", file=sys.stderr)
            return 2
        print(json.dumps(reg[args.model].as_dict(), indent=2, ensure_ascii=False, default=str))
    elif args.action == "verify":
        # Sem modelo nomeado, confere o corpus inteiro: `G-008` fala do corpus, nao de um item.
        alvos = [reg[args.model]] if args.model else list(reg)
        divergiram, falharam, ok = [], [], []
        print(f"{'modelo':<20}{'veredicto':<14}{'params local = upstream':<26}nao transcritos")
        for spec in alvos:
            try:
                r = verify_spec(spec, args.repo if args.model else None)
            except (ValueError, PermissionError) as exc:
                falharam.append((spec.id, str(exc)))
                print(f"{spec.id:<20}{'SEM UPSTREAM':<14}{'—':<26}{exc}")
                continue
            except OSError as exc:
                falharam.append((spec.id, f"rede: {exc}"))
                print(f"{spec.id:<20}{'FALHA DE REDE':<14}{'—':<26}{exc}")
                continue
            p = r["derived_params"]
            print(
                f"{spec.id:<20}{'CONFERE' if r['matches'] else 'DIVERGE':<14}"
                f"{('sim' if p.get('equal') else 'NAO'):<26}{len(r['not_transcribed'])}"
            )
            if r["matches"]:
                ok.append(r)
                if args.write:
                    record_verification(spec.id, r, _corpus(args))
            else:
                divergiram.append(r)

        for r in divergiram:
            print(f"\n{r['model']} — campos que divergem do upstream:")
            print(json.dumps(r["divergences"], indent=2, ensure_ascii=False))

        print(
            f"\n{len(ok)} conferido(s), {len(divergiram)} divergente(s), "
            f"{len(falharam)} sem verificacao"
        )
        if args.write and ok:
            print(f"proveniencia gravada no corpus para {len(ok)} modelo(s) — fecha G-008")
        elif ok and not args.write:
            print("use --write para gravar a proveniencia no corpus e fechar G-008")
        return 1 if (divergiram or falharam) else 0
    return 0


def cmd_fingerprint(args) -> int:
    reg = _reg(args)
    spec = reg[args.model]
    print(fingerprint_json(spec, build_graph(spec)))
    return 0


def cmd_diff(args) -> int:
    reg = _reg(args)
    d = diff_versions(ModelView.of(reg[args.older]), ModelView.of(reg[args.newer]))
    print(f"# {d.older} -> {d.newer}  ({d.days_between} dias)\n")
    print("estabilidade por nivel de identidade:")
    for lvl, v in d.stability.items():
        print(f"  {lvl:<10} {v:.3f}")
    print("\nconfiguracao alterada:")
    for k, (a, b) in d.changed_config.items() or {}.items():
        print(f"  {k}: {a} -> {b}")
    if not d.changed_config:
        print("  (nenhuma)")
    if d.signature_changes:
        print("\nmudancas de assinatura (amostra):")
        for line in d.signature_changes[:20]:
            print(f"  {line}")
    print(
        f"\nestruturalmente identico no nivel exato: "
        f"{'sim' if d.structurally_identical else 'nao'}"
    )
    return 0


def cmd_stability(args) -> int:
    reg = _reg(args)
    views = [ModelView.of(s) for s in reg.family(args.family)]
    if not views:
        print(f"familia {args.family!r} sem modelos; disponiveis: {reg.families()}", file=sys.stderr)
        return 2
    rep = family_stability(views)
    print(json.dumps(rep.as_dict(), indent=2, ensure_ascii=False))
    print(f"\n{rep.finding('exact')}")
    return 0


def cmd_invariants(args) -> int:
    reg = _reg(args)
    invs = discover_invariants(_views(reg), level=args.level)
    rows = invariant_map_rows(invs, min_coverage=args.min_coverage)
    print(f"# Invariantes no nivel `{args.level}` — {len(reg)} modelos no corpus\n")
    print("| Candidato | Modelos | Cobertura | Instancias | Ausente de | Status |")
    print("|---|---|---|---|---|---|")
    for r in rows[: args.top]:
        print(
            f"| {r['candidate']} | {r['models_covered']} | {r['coverage']:.2f} | "
            f"{r['instances']} | {r['known_failures']} | {r['status']} |"
        )
    return 0


def cmd_profile(args) -> int:
    reg = _reg(args)
    spec = reg[args.model]
    g = build_graph(spec)
    dev = get_device(args.device)
    sp = serving_profile(
        g, dev, batch=args.batch, prompt_len=args.prompt, gen_len=args.gen,
        weight_precision=args.precision or spec.default_dtype,
    )
    out = {
        "serving": sp.summary(),
        "prefill": sp.prefill.summary(),
        "decode": sp.decode.summary(),
        "decode_concentration_index": concentration_index(sp.decode),
        "decode_20_80": dominant_roles(sp.decode),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    for f in sp.findings() + sp.decode.findings():
        print(f"  {f}", file=sys.stderr)
    return 0


def cmd_quantize(args) -> int:
    from .ir.graph import Phase, Workload

    reg = _reg(args)
    spec = reg[args.model]
    g = build_graph(spec)
    priors = QuantPriors.load()
    if args.evidence:
        priors = priors.with_evidence(json.loads(Path(args.evidence).read_text(encoding="utf-8")))
    plan = sensitivity_plan(g, priors, is_moe=spec.is_moe)
    ev = evaluate_plan(
        g, plan, Workload(phase=Phase.DECODE, batch=args.batch, context_len=args.context),
        get_device(args.device), baseline_precision=spec.default_dtype,
    )
    print(json.dumps(ev.as_dict(), indent=2, ensure_ascii=False, default=str))
    return 0


def cmd_score(args) -> int:
    a = Assessment.build(
        AssessmentInputs(model_id=args.model, device_key=args.device), _corpus(args)
    )
    print(f"# {a.spec.id} — Silicon Readiness\n")
    print(f"SRS = {a.srs.score:.3f}  -> banda `{a.recommendation}`")
    print(f"veredito: {a.verdict}\n")
    print("| Papel | Custo | LHS | E | F | R | Q | V | M | L |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for c in a.candidates[:10]:
        f = c.scorecard.factors
        vals = " | ".join(f"{float(f[k].value):.2f}" for k in ("E", "F", "R", "Q", "V", "M", "L"))
        print(f"| {c.role} | {c.cost_share:.1%} | **{c.lhs:.3f}** | {vals} |")
    s = a.sens_lhs
    print(
        f"\nsensibilidade (+-{s.perturbation:.0%}, {s.samples} amostras): "
        f"top-1 {s.top1_stability:.1%}, top-3 {s.top3_stability:.1%}, "
        f"banda SRS {(s.band_stability or 0):.1%} -> "
        f"{'DECIDIVEL' if s.decidable else 'NAO DECIDIVEL (F3 disparado)'}"
    )
    return 0


def cmd_partition(args) -> int:
    a = Assessment.build(
        AssessmentInputs(model_id=args.model, device_key=args.device), _corpus(args)
    )
    print(a.part.as_text())
    print(f"\nnivel: {int(a.part.level)} — {a.part.level.label}")
    print(f"fracao endurecida: {a.part.hardened_share:.1%}")
    print(f"teto de Amdahl: {a.part.amdahl_ceiling():.2f}x")
    from .partition import hardening_ceiling_finding

    f = hardening_ceiling_finding(a.part, args.claimed)
    print(f"\nverificacao de alegacao de {args.claimed:g}x:\n  {f.note}")
    return 0


def cmd_economics(args) -> int:
    a = Assessment.build(
        AssessmentInputs(
            model_id=args.model, device_key=args.device, annual_tokens=args.annual_tokens,
            tech_node=args.node, target_tokens_per_second=args.target_tps,
        ),
        _corpus(args),
    )
    print(json.dumps(a.economics.as_dict(), indent=2, ensure_ascii=False, default=str))
    return 0


def cmd_assess(args) -> int:
    inputs = AssessmentInputs(
        model_id=args.model,
        device_key=args.device,
        batch=args.batch,
        prompt_len=args.prompt,
        gen_len=args.gen,
        annual_tokens=args.annual_tokens,
        tech_node=args.node,
        target_tokens_per_second=args.target_tps,
        claimed_gain=args.claimed,
    )
    a = Assessment.build(inputs, _corpus(args))
    try:
        text = a.render()
    except EmissionRefused as exc:
        print(f"EMISSAO RECUSADA: {exc}", file=sys.stderr)
        return 3

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(a.to_json(), encoding="utf-8")
        print(f"json -> {out}", file=sys.stderr)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"relatorio -> {out}", file=sys.stderr)
    else:
        print(text)
    return 0


def cmd_lint(args) -> int:
    target = Path(args.path)
    files = sorted(target.rglob("*.md")) if target.is_dir() else [target]
    total = 0
    for f in files:
        problems = lint_text(f.read_text(encoding="utf-8"))
        for p in problems:
            total += 1
            print(f"{f}:{p.line_no}: {p.term!r} — {p.reason}")
    print(f"\n{len(files)} arquivo(s), {total} ocorrencia(s) de vocabulario proibido")
    return 1 if total else 0


def cmd_gates(args) -> int:
    """Estado dos portoes do ciclo, do D0 ao S6."""
    reg = _reg(args)
    integrity = corpus_integrity(reg)
    ledger_path = ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml"
    ledger = ClaimLedger.load(ledger_path) if ledger_path.exists() else None
    gaps = count_gaps(ROOT / "02_OBSERVATION" / "GAP_REGISTER.md")

    a = Assessment.build(AssessmentInputs(model_id=args.model), _corpus(args)) if args.model else None

    # Criterios conforme os portoes do Metodo 4.1 a 4.7. Cada linha verifica **conteudo**, nao
    # existencia de caminho: um portao que passa por a pasta existir nao e portao. Os
    # verificadores moram em `douvras_core.gates` — a regra e do Metodo, nao deste atlas.
    shared = [i for i in a.invariants if len(i.models) > 1] if a else []

    charter = ROOT / "01_DELIMITATION" / "PROBLEM_CHARTER.md"
    d0 = has_all(
        charter,
        ("Pergunta principal", "objetivos", "Baseline congelado", "Critérios de falha"),
    ) and has_numbered_falsifiers(charter)

    # U2 exige que os casos que NAO se encaixam estejam nomeados no mapa gerado — a condicao
    # aritmetica anterior (models + absent == corpus) era identidade, verdadeira sempre.
    imap = ROOT / "03_UNIFICATION" / "INVARIANT_MAP.md"
    imap_txt = imap.read_text(encoding="utf-8") if imap.exists() else ""
    documented = bool(shared) and any(
        m.id in imap_txt for m in reg
    ) and "Falhas conhecidas" in imap_txt

    # A5 exige verificacao registrada por `scripts/run_silicon_cycle.py`, nao a presenca de tests/.
    a5, vdata = verified_suite(ROOT / "07_SYSTEMATIZATION" / "last_verification.json")
    # Apenas arquivos ER-*.md contam. Um README no diretorio nao e revisao — e o erro que
    # transformaria o portao numa formalidade satisfeita por existir a pasta.
    reviews = external_reviews(ROOT / "04_VALIDATION" / "EXTERNAL_REVIEWS")
    external_review = bool(reviews)

    integrity_ok = integrity.value is not None and integrity.value < 5e-3
    report = summarize(
        [
            Gate("D0", d0,
                 "carta com pergunta, baseline congelado, nao objetivos e criterios F1..Fn"
                 if d0 else "PROBLEM_CHARTER incompleta ou sem criterio de falha numerado"),
            Gate("O1", len(reg) >= 3 and integrity_ok,
                 f"{len(reg)} modelos; erro de parametros "
                 + (f"{integrity.value:.2%}" if integrity.value is not None else "NAO VERIFICADO")),
            Gate("U2", bool(shared) and documented,
                 f"{len(shared)} padrao(oes) compartilhado(s) por mais de um modelo; casos que "
                 f"nao se encaixam {'nomeados no INVARIANT_MAP' if documented else 'NAO nomeados'}"),
            Gate("V3", bool(a and a.decidable and external_review),
                 ("score discrimina" if a and a.decidable else "score NAO discrimina (CE-001)")
                 + "; " + (f"{len(reviews)} revisao(oes) externa(s)" if external_review
                           else "sem revisao adversarial externa (G-010)")),
            Gate("R4", has_all(ROOT / "05_REDUCTION" / "MINIMAL_STRUCTURE.md",
                               ("Função preservada", "Componentes obrigatórios",
                                "Limites de validade")),
                 "UMI com funcao preservada, componentes e limites de validade declarados"),
            Gate("A5", a5,
                 (f"suite verificada em {vdata.get('run_id', '?')}: {vdata.get('passed', 0)} testes"
                  if a5 else "sem verificacao registrada: rode `python scripts/run_silicon_cycle.py`")),
            Gate("S6",
                 ledger is not None
                 and (ROOT / "07_SYSTEMATIZATION" / "CHANGELOG.md").exists()
                 and (ROOT / "00_GOVERNANCE" / "RETRACTIONS_AND_CORRECTIONS.md").exists()
                 and (ROOT / "07_SYSTEMATIZATION" / "OPERATIONS.md").exists(),
                 f"ledger com {len(ledger.claims) if ledger else 0} alegacoes; changelog, "
                 f"retratacoes e operacao presentes"),
        ],
        gaps,
    )
    print(report.render())
    return 0


def cmd_devices(args) -> int:
    for k, d in load_devices().items():
        print(json.dumps(d.as_dict(), indent=2, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atlas",
        description="DOUVRAS Silicon Atlas — o que de um modelo ja esta pronto para virar silicio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--corpus", help="diretorio do corpus (default: corpus/models)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("registry", help="modelos registrados")
    r.add_argument("action", choices=["list", "show", "verify"])
    r.add_argument("model", nargs="?")
    r.add_argument("--repo", help="repositorio HF para verificacao upstream")
    r.add_argument(
        "--write",
        action="store_true",
        help="grava a proveniencia conferida no corpus (fecha G-008)",
    )
    r.set_defaults(func=cmd_registry)

    f = sub.add_parser("fingerprint", help="fingerprint arquitetural")
    f.add_argument("model")
    f.set_defaults(func=cmd_fingerprint)

    d = sub.add_parser("diff", help="diff estrutural entre duas versoes")
    d.add_argument("older")
    d.add_argument("newer")
    d.set_defaults(func=cmd_diff)

    st = sub.add_parser("stability", help="estabilidade de uma familia")
    st.add_argument("family")
    st.set_defaults(func=cmd_stability)

    iv = sub.add_parser("invariants", help="padroes compartilhados no corpus")
    iv.add_argument("--level", choices=["topology", "pattern", "exact"], default="exact")
    iv.add_argument("--min-coverage", type=float, default=0.0)
    iv.add_argument("--top", type=int, default=25)
    iv.set_defaults(func=cmd_invariants)

    pr = sub.add_parser("profile", help="perfil roofline por fase")
    pr.add_argument("model")
    pr.add_argument("--device", default="h100-sxm")
    pr.add_argument("--batch", type=int, default=1)
    pr.add_argument("--prompt", type=int, default=2048)
    pr.add_argument("--gen", type=int, default=512)
    pr.add_argument("--precision", default=None)
    pr.set_defaults(func=cmd_profile)

    q = sub.add_parser("quantize", help="plano de precisao e ganho estimado")
    q.add_argument("model")
    q.add_argument("--device", default="h100-sxm")
    q.add_argument("--batch", type=int, default=1)
    q.add_argument("--context", type=int, default=4096)
    q.add_argument("--evidence", help="json com tolerancias medidas (fecha G-002 parcialmente)")
    q.set_defaults(func=cmd_quantize)

    sc = sub.add_parser("score", help="LHS, SRS e sensibilidade")
    sc.add_argument("model")
    sc.add_argument("--device", default="h100-sxm")
    sc.set_defaults(func=cmd_score)

    pa = sub.add_parser("partition", help="particao fixa/configuravel/programavel")
    pa.add_argument("model")
    pa.add_argument("--device", default="h100-sxm")
    pa.add_argument("--claimed", type=float, default=100.0, help="ganho alegado a confrontar")
    pa.set_defaults(func=cmd_partition)

    ec = sub.add_parser("economics", help="break-even com incerteza propagada")
    ec.add_argument("model")
    ec.add_argument("--device", default="h100-sxm")
    ec.add_argument("--annual-tokens", type=float, default=1e13)
    ec.add_argument("--node", default="6nm")
    ec.add_argument("--target-tps", type=float, default=1000.0)
    ec.set_defaults(func=cmd_economics)

    asm = sub.add_parser("assess", help="Silicon Readiness Assessment completo")
    asm.add_argument("model")
    asm.add_argument("-o", "--output", help="arquivo .md de saida")
    asm.add_argument("--json", help="arquivo .json de saida")
    asm.add_argument("--device", default="h100-sxm")
    asm.add_argument("--batch", type=int, default=1)
    asm.add_argument("--prompt", type=int, default=2048)
    asm.add_argument("--gen", type=int, default=512)
    asm.add_argument("--annual-tokens", type=float, default=1e13)
    asm.add_argument("--node", default="6nm")
    asm.add_argument("--target-tps", type=float, default=1000.0)
    asm.add_argument("--claimed", type=float, default=100.0)
    asm.set_defaults(func=cmd_assess)

    ln = sub.add_parser("lint", help="vocabulario proibido (Metodo 3.2)")
    ln.add_argument("path")
    ln.set_defaults(func=cmd_lint)

    gt = sub.add_parser("gates", help="estado dos portoes do ciclo")
    gt.add_argument("--model", default="llama-3.1-8b")
    gt.set_defaults(func=cmd_gates)

    dv = sub.add_parser("devices", help="baselines de hardware congelados")
    dv.set_defaults(func=cmd_devices)

    return p


def main(argv: list[str] | None = None) -> int:
    # A arte ASCII da particao usa U+251C/U+2514, ausentes em cp1252. No console interativo o
    # Python escreve via WriteConsoleW e funciona; com stdout redirecionado (`> arquivo`, pipe,
    # captura de CI) o encoding cai para a codepage local e o comando morre com
    # UnicodeEncodeError. Reconfigurar aqui cobre os dois casos.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # stream substituido em teste
            pass
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
