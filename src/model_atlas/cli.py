"""Interface de linha de comando do DOUVRAS Model Atlas.

    matlas registry list                 modelos registrados e proveniencia
    matlas tasks list                    corpus de tarefas por capacidade
    matlas tasks validate                toda tarefa tem regra que algum grader implementa
    matlas instrument                    o benchmark mede o que diz medir?
    matlas probes                        cada sonda dispara o modo que prometeu
    matlas failures                      Failure Atlas das sondas
    matlas capability <modelo>           vetor de capacidades (ou as ausencias declaradas)
    matlas css <modelo>                  alvo de especializacao e diagnostico de discriminacao
    matlas profile <modelo>              memoria por quantizacao e telemetria ausente
    matlas assess <modelo> -o r.md       Model Capability Assessment completo
    matlas gates                         estado dos portoes do ciclo C-002
    matlas lint <caminho>                vocabulario proibido (Metodo 3.2)
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

from . import css as css_mod
from .assessment import Assessment, AssessmentInputs, EmissionRefused
from .capability import CapabilityFingerprint
from .failure import FailureAtlas
from .instrument import MIN_TASKS_PER_CAPABILITY, evaluate_instrument, probe_expectations
from .profiler import InferenceProfile, MemoryBudget
from .registry import (
    Registry,
    UpstreamUnavailable,
    corpus_provenance,
    record_verification,
    verify_spec,
    weights_available,
)
from .runner import PROBES, run_suite
from .tasks import TaskSet

ROOT = project_root("model-atlas")


def _tasks(args) -> TaskSet:
    return TaskSet.load(Path(args.corpus) if getattr(args, "corpus", None) else None)


def _registry(args) -> Registry:
    return Registry.load(Path(args.models) if getattr(args, "models", None) else None)


# ------------------------------------------------------------------------- comandos ---


def cmd_registry(args) -> int:
    reg = _registry(args)
    if args.sub == "list":
        print(f"{'id':<22}{'repo':<34}{'params':>9}  {'pesos':<7}proveniencia")
        for s in reg:
            p = f"{s.params_b} B" if s.params_b else "—"
            print(
                f"{s.id:<22}{s.repo:<34}{p:>9}  "
                f"{'sim' if s.weights_local else 'nao':<7}{s.provenance}"
            )
        print()
        print(f"  {corpus_provenance(reg)}")
        print(f"  {weights_available(reg)}")
        return 0
    if args.sub == "show":
        print(json.dumps(reg[args.model].as_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.sub == "verify":
        # Sem modelo nomeado, confere o corpus inteiro: G-108 fala do corpus, nao de um item.
        alvos = [reg[args.model]] if args.model else list(reg)
        ok, divergiram, falharam = [], [], []
        print(f"{'modelo':<18}{'veredicto':<14}{'params upstream':>16}  descobertos")
        for spec in alvos:
            try:
                r = verify_spec(spec)
            except (ValueError, PermissionError, UpstreamUnavailable) as exc:
                falharam.append((spec.id, str(exc)))
                print(f"{spec.id:<18}{'SEM UPSTREAM':<14}{'—':>16}  {exc}")
                continue
            p = f"{r['params_upstream']:,}" if r["params_upstream"] else "—"
            print(
                f"{spec.id:<18}{'CONFERE' if r['matches'] else 'DIVERGE':<14}{p:>16}  "
                f"{', '.join(f'{k}={v}' for k, v in r['discovered'].items()) or '—'}"
            )
            (ok if r["matches"] else divergiram).append(r)
            if r["matches"] and args.write:
                record_verification(spec.id, r, Path(args.models) if args.models else None)

        for r in divergiram:
            print(f"\n{r['model']} — campos que divergem da fonte:")
            print(json.dumps(r["divergences"], indent=2, ensure_ascii=False))

        print(
            f"\n{len(ok)} conferido(s), {len(divergiram)} divergente(s), "
            f"{len(falharam)} sem verificacao"
        )
        if args.write and ok:
            print(f"proveniencia gravada para {len(ok)} modelo(s) — fecha G-108")
        elif ok and not args.write:
            print("use --write para gravar a proveniencia no corpus e fechar G-108")
        return 1 if (divergiram or falharam) else 0
    return 1


def cmd_tasks(args) -> int:
    ts = _tasks(args)
    if args.sub == "list":
        print(f"{'capacidade':<22}{'tarefas':>8}  {'contraexemplos':>15}")
        for cap, items in ts.by_capability().items():
            ce = sum(len(t.counterexamples) for t in items)
            marca = "" if len(items) >= MIN_TASKS_PER_CAPABILITY else "  <- cobertura fina"
            print(f"{str(cap):<22}{len(items):>8}  {ce:>15}{marca}")
        print(f"\ntotal: {len(ts)} tarefas, minimo declarado por capacidade: "
              f"{MIN_TASKS_PER_CAPABILITY}")
        return 0
    if args.sub == "show":
        t = ts[args.task]
        print(json.dumps({**t.as_dict(), "prompt": t.prompt, "rules": dict(t.rules)},
                         indent=2, ensure_ascii=False))
        return 0
    if args.sub == "validate":
        rep = evaluate_instrument(ts, check_determinism=False)
        if rep.ungradable:
            for u in rep.ungradable:
                print(f"SEM GRADER  {u}")
            return 1
        print(f"{len(ts)} tarefas, todas com regra implementada por algum grader")
        return 0
    return 1


def cmd_instrument(args) -> int:
    rep = evaluate_instrument(_tasks(args))
    print(f"tarefas                     {rep.tasks}")
    print(f"aceitacao do gabarito       {rep.gold_acceptance:.1%}  "
          f"({rep.gold_accepted}/{rep.gold_total})")
    print(f"rejeicao de contraexemplo   {rep.counterexample_rejection:.1%}  "
          f"({len(rep.counterexamples)} declarados)")
    print(f"precisao do rotulo          {rep.label_precision:.1%}")
    print(f"margem de discriminacao     {rep.discrimination_margin:.3f}  "
          f"({'discrimina' if rep.discriminates else 'NAO discrimina'})")
    print(f"determinismo                {'sim' if rep.deterministic else 'NAO'}")
    print(f"modos sem sonda             {[str(m) for m in rep.dead_modes] or 'nenhum'}")
    print()
    print("sensibilidade por sonda (diagnostico de CE-101, nao criterio):")
    print(f"  {'sonda':<20}{'alvo':>7}{'% corpus':>10}{'queda no alvo':>15}{'queda agregada':>16}")
    for d in rep.probe_sensitivity():
        print(
            f"  {d['sonda']:<20}{d['tarefas_no_alvo']:>7}{d['fracao_do_corpus']:>10.1%}"
            f"{d['queda_no_alvo']:>15.3f}{d['queda_agregada']:>16.3f}"
        )
    print()
    print(f"{'falsificador':<14}{'estado':<16}medido")
    for k, v in rep.falsifiers().items():
        estado = "DISPARADO" if v["disparado"] else "nao disparado"
        print(f"{k:<14}{estado:<16}{v['medido']}")
    for c in rep.counterexamples:
        if not c.rejected or not c.labeled:
            print(f"  FALHA  {c.task_id} [{c.label}] esperado {c.expected}, "
                  f"observado {[str(m) for m in c.observed] or 'nenhuma falha'}")
    return 0


def cmd_probes(args) -> int:
    print(f"{'sonda':<20}{'escore':>8}  {'cumpriu':<9}prometido / observado")
    for row in probe_expectations(_tasks(args)):
        print(
            f"{row['sonda']:<20}{row['escore']:>8.3f}  "
            f"{'sim' if row['cumpriu'] else 'NAO':<9}"
            f"{row['prometido']} / {row['observado']}"
        )
    return 0


def cmd_failures(args) -> int:
    ts = _tasks(args)
    atlas = FailureAtlas.merged([run_suite(ts, p) for p, _ in PROBES], "sondas de calibracao")
    print(atlas.render_tree())
    return 0


def cmd_capability(args) -> int:
    reg = _registry(args)
    ts = _tasks(args)
    spec = reg[args.model]
    fp = CapabilityFingerprint.unmeasured(spec.id, sorted(ts.by_capability(), key=str))
    print(fp.render())
    return 0


def cmd_css(args) -> int:
    reg = _registry(args)
    ts = _tasks(args)
    fp = CapabilityFingerprint.unmeasured(reg[args.model].id, sorted(ts.by_capability(), key=str))
    cand = css_mod.build_candidates(fp, css_mod.load_priors())
    res = css_mod.score(cand, css_mod.Weights.load())
    print(css_mod.css_finding(fp, res))
    if not cand:
        print(
            "\nNenhum candidato: o CSS precisa de deficit medido, e deficit precisa de execucao.\n"
            "O motor esta implementado e coberto por teste com fingerprint sintetico — a licao\n"
            "do G-014 do Silicon Atlas, onde o caminho economico atravessou um ciclo inteiro\n"
            "sem nunca ter sido executado."
        )
    return 0


def cmd_profile(args) -> int:
    spec = _registry(args)[args.model]
    budget = MemoryBudget.build(spec)
    print(budget.render(args.ram * 1e9))
    print()
    for f in InferenceProfile(model_id=spec.id).findings().items:
        print(f"  {f}")
    return 0


def cmd_assess(args) -> int:
    a = Assessment.build(
        AssessmentInputs(model_id=args.model, ram_bytes=args.ram * 1e9), _registry(args)
    )
    try:
        texto = a.render()
    except EmissionRefused as exc:
        print(f"portao de emissao recusou: {exc}", file=sys.stderr)
        return 3
    if args.output:
        Path(args.output).write_text(texto, encoding="utf-8")
        print(f"escrito {args.output}")
    else:
        print(texto)
    return 0


def cmd_gates(args) -> int:
    ts = _tasks(args)
    reg = _registry(args)
    rep = evaluate_instrument(ts)
    gaps = count_gaps(ROOT / "02_OBSERVATION" / "GAP_REGISTER.md")

    ledger_path = ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml"
    ledger = ClaimLedger.load(ledger_path) if ledger_path.exists() else None
    charter = ROOT / "01_DELIMITATION" / "PROBLEM_CHARTER.md"
    d0 = has_all(
        charter, ("Pergunta principal", "objetivos", "Baseline congelado", "Critérios de falha")
    ) and has_numbered_falsifiers(charter)

    # U2 exige padrao compartilhado **e** os casos que nao se encaixam nomeados. Um modo de
    # falha que nenhuma sonda dispara e exatamente um caso que nao se encaixa.
    mapa = ROOT / "03_UNIFICATION" / "FAILURE_MAP.md"
    mapa_txt = mapa.read_text(encoding="utf-8") if mapa.exists() else ""
    compartilhados = [
        m for m in rep.observed_modes
        if sum(1 for cap in ts.by_capability() if any(
            m in g.failures for r in rep.probe_runs for g in r.grades if g.capability == cap
        )) > 1
    ]
    u2 = bool(compartilhados) and "Modos sem sonda" in mapa_txt

    a5, vdata = verified_suite(ROOT / "07_SYSTEMATIZATION" / "last_verification.json")
    reviews = external_reviews(ROOT / "04_VALIDATION" / "EXTERNAL_REVIEWS")

    report = summarize(
        [
            Gate("D0", d0,
                 "carta com pergunta, baseline congelado, nao objetivos e criterios F1..Fn"
                 if d0 else "PROBLEM_CHARTER incompleta ou sem criterio de falha numerado"),
            Gate("O1", len(ts) >= 50 and not rep.thin_capabilities and len(reg) >= 3,
                 f"{len(ts)} tarefas em {len(rep.coverage)} capacidades, {len(reg)} modelos; "
                 + ("cobertura minima atendida" if not rep.thin_capabilities
                    else f"cobertura fina em {rep.thin_capabilities}")),
            Gate("U2", u2,
                 f"{len(compartilhados)} modo(s) de falha atravessam mais de uma capacidade; "
                 f"casos que nao se encaixam "
                 f"{'nomeados no FAILURE_MAP' if 'Modos sem sonda' in mapa_txt else 'NAO nomeados'}"),
            Gate("V3", rep.discriminates and bool(reviews),
                 ("instrumento discrimina" if rep.discriminates
                  else f"instrumento NAO discrimina (margem {rep.discrimination_margin:.3f})")
                 + "; " + (f"{len(reviews)} revisao(oes) externa(s)" if reviews
                           else "sem revisao adversarial externa (G-110)")),
            Gate("R4", has_all(ROOT / "05_REDUCTION" / "MINIMAL_STRUCTURE.md",
                               ("Função preservada", "Componentes obrigatórios",
                                "Limites de validade")),
                 "UMI com funcao preservada, componentes e limites de validade declarados"),
            Gate("A5", a5,
                 (f"suite verificada em {vdata.get('run_id', '?')}: {vdata.get('passed', 0)} testes"
                  if a5 else "sem verificacao registrada: rode `python scripts/run_model_cycle.py`")),
            Gate("S6",
                 ledger is not None
                 and (ROOT / "07_SYSTEMATIZATION" / "CHANGELOG.md").exists()
                 and (ROOT / "07_SYSTEMATIZATION" / "OPERATIONS.md").exists(),
                 f"ledger com {len(ledger.claims) if ledger else 0} alegacoes; changelog e "
                 f"operacao presentes"),
        ],
        gaps,
    )
    print(report.render())
    return 0


def cmd_lint(args) -> int:
    alvo = Path(args.path)
    arquivos = sorted(alvo.rglob("*.md")) if alvo.is_dir() else [alvo]
    total = 0
    for f in arquivos:
        for p in lint_text(f.read_text(encoding="utf-8")):
            total += 1
            print(f"{f}:{p.line_no}: {p.term!r} — {p.reason}")
    print(f"\n{len(arquivos)} arquivo(s), {total} ocorrencia(s) de vocabulario proibido")
    return 1 if total else 0


# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="matlas", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", help="diretorio de tarefas (default: model-atlas/corpus/tasks)")
    p.add_argument("--models", help="diretorio de modelos (default: model-atlas/corpus/models)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("registry", help="modelos registrados e proveniencia")
    r.add_argument("sub", choices=["list", "show", "verify"])
    r.add_argument("model", nargs="?")
    r.add_argument(
        "--write",
        action="store_true",
        help="grava a proveniencia conferida no corpus (fecha G-108)",
    )
    r.set_defaults(fn=cmd_registry)

    t = sub.add_parser("tasks", help="corpus de tarefas")
    t.add_argument("sub", choices=["list", "show", "validate"])
    t.add_argument("task", nargs="?")
    t.set_defaults(fn=cmd_tasks)

    sub.add_parser("instrument", help="o benchmark mede o que diz medir?").set_defaults(
        fn=cmd_instrument
    )
    sub.add_parser("probes", help="cada sonda dispara o modo que prometeu").set_defaults(
        fn=cmd_probes
    )
    sub.add_parser("failures", help="Failure Atlas das sondas").set_defaults(fn=cmd_failures)

    c = sub.add_parser("capability", help="vetor de capacidades")
    c.add_argument("model")
    c.set_defaults(fn=cmd_capability)

    s = sub.add_parser("css", help="alvo de especializacao")
    s.add_argument("model")
    s.set_defaults(fn=cmd_css)

    pr = sub.add_parser("profile", help="memoria por quantizacao")
    pr.add_argument("model")
    pr.add_argument("--ram", type=float, default=16.0, help="RAM disponivel em GB")
    pr.set_defaults(fn=cmd_profile)

    a = sub.add_parser("assess", help="Model Capability Assessment")
    a.add_argument("model")
    a.add_argument("-o", "--output")
    a.add_argument("--ram", type=float, default=16.0)
    a.set_defaults(fn=cmd_assess)

    sub.add_parser("gates", help="estado dos portoes do ciclo").set_defaults(fn=cmd_gates)

    ln = sub.add_parser("lint", help="vocabulario proibido")
    ln.add_argument("path")
    ln.set_defaults(fn=cmd_lint)
    return p


def main(argv: list[str] | None = None) -> int:
    # `matlas failures | more` morria com UnicodeEncodeError na arvore do Failure Atlas.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):  # pragma: no cover
        pass
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
