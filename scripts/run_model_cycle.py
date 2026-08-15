"""Executa um ciclo DOUVRAS completo do **Model Atlas** e regenera os artefatos derivados.

    python scripts/run_model_cycle.py [--models a,b,c] [--ram 16] [--skip-tests]

Regenera, todos sob `model-atlas/`:
    03_UNIFICATION/FAILURE_MAP.md              — taxonomia medida, com os modos sem sonda
    03_UNIFICATION/DEPENDENCY_DAG.md           — onde a cadeia de evidencia ainda nao fecha
    04_VALIDATION/EXPERIMENTS/X-002-RESULT.md  — resultado do experimento inaugural
    99_RELEASES/reports/MCA-<modelo>.md/.json  — Model Capability Assessments
    00_GOVERNANCE/CLAIM_LEDGER.yaml            — evidencia anexada; retratacao automatica
    07_SYSTEMATIZATION/last_verification.json  — registro que o portao A5 consome

Nenhum destes deve ser editado a mao: sao saida, nao entrada. O que se edita sao os templates
em `scripts/build_task_corpus.py`, os priors em `config/`, as fichas em `corpus/models/` e as
alegacoes no `CLAIM_LEDGER.yaml`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

ROOT = REPO / "model-atlas"

from douvras_core.gates import count_gaps  # noqa: E402
from douvras_core.status import ClaimLedger  # noqa: E402
from model_atlas.assessment import Assessment, AssessmentInputs  # noqa: E402
from model_atlas.failure import FailureAtlas  # noqa: E402
from model_atlas.instrument import evaluate_instrument, probe_expectations  # noqa: E402
from model_atlas.registry import Registry, corpus_provenance  # noqa: E402
from model_atlas.runner import PROBES, run_suite  # noqa: E402
from model_atlas.tasks import FailureMode, TaskSet  # noqa: E402


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  escrito  {path.relative_to(REPO)}")
    return path


def build_failure_map(tasks: TaskSet, rep, atlas: FailureAtlas, run_id: str) -> str:
    partes = [
        "---",
        "artifact: FAILURE_MAP",
        f"run_id: {run_id}",
        "generated_by: scripts/run_model_cycle.py",
        "status: COMPUTATIONAL_EVIDENCE",
        "---",
        "",
        "# Mapa de falhas",
        "",
        "> Arquivo **gerado**. Editar a mao apaga a rastreabilidade. Para mudar o conteudo,",
        "> mude os templates de tarefa ou as sondas e reexecute `python scripts/run_model_cycle.py`.",
        "",
        f"Corpus: {len(tasks)} tarefas em {len(rep.coverage)} capacidades.",
        "Estas taxas descrevem as **sondas de calibracao**, nao um modelo: elas mostram que a",
        "taxonomia esta viva, ou seja, que cada celula preenchida corresponde a um modo que o",
        "grader consegue detectar quando ele acontece.",
        "",
        "## Cobertura por capacidade",
        "",
        "| Capacidade | Tarefas | Contraexemplos |",
        "|---|---:|---:|",
    ]
    por_cap = tasks.by_capability()
    for cap, items in por_cap.items():
        ce = sum(len(t.counterexamples) for t in items)
        partes.append(f"| `{cap}` | {len(items)} | {ce} |")

    partes += ["", "## Celulas da taxonomia", "", "```text", atlas.render_tree(), "```", ""]

    partes += [
        "## Modos que atravessam mais de uma capacidade",
        "",
        "| Modo | Capacidades em que aparece |",
        "|---|---|",
    ]
    cruzados = 0
    for modo in sorted(atlas.observed_modes(), key=str):
        caps = sorted(
            (str(c) for c, cel in atlas.per_capability.items() if modo in cel), key=str
        )
        if len(caps) > 1:
            cruzados += 1
        partes.append(f"| `{modo}` | {', '.join(f'`{c}`' for c in caps)} |")

    partes += [
        "",
        f"**{cruzados} modo(s)** aparecem em mais de uma capacidade. Um modo que atravessa",
        "capacidades e candidato a dataset transversal: corrigi-lo move mais de uma medida.",
        "",
        "## Modos sem sonda",
        "",
    ]
    if rep.dead_modes:
        partes += [
            "Modos declarados no corpus que **nenhuma sonda consegue provocar**. Cada um e uma",
            "celula morta: o benchmark alega medir algo que nunca foi visto acontecer.",
            "",
            *[f"- `{m}`" for m in rep.dead_modes],
        ]
    else:
        partes += [
            "Nenhum. Todo modo declarado no corpus e disparado por ao menos uma sonda, portanto",
            "e detectavel quando ocorre **na forma em que a sonda o produz** (`A-106`). Isto nao",
            "e o mesmo que cobrir as formas em que um modelo real erra — ver `G-110`.",
        ]

    partes += [
        "",
        "## Casos que nao se encaixam",
        "",
        "Preservados em vez de suavizados (Metodo, portao U2):",
        "",
        f"- `FAIL_NO_ANSWER` existe como regra do grader e e exercitado por contraexemplo, mas",
        f"  nenhuma tarefa o declara em `failure_modes` — nenhuma sonda termina sem responder.",
        f"- `plano-invertido` cai apenas {min((d['queda_no_alvo'] for d in rep.probe_sensitivity()), default=0):.3f}",
        "  dentro do proprio alvo declarado: o alvo e definido pelos modos da tarefa, mais grosso",
        "  que o que a sonda de fato ataca (`G-111`).",
        "- As tarefas de `planning` misturam dois contratos distintos — ordem de operacoes e",
        "  pergunta ante ambiguidade — e nenhuma sonda ataca os dois.",
    ]
    return "\n".join(partes) + "\n"


def build_dependency_dag(rep, run_id: str) -> str:
    return "\n".join(
        [
            "---",
            "artifact: DEPENDENCY_DAG",
            f"run_id: {run_id}",
            "generated_by: scripts/run_model_cycle.py",
            "---",
            "",
            "# Grafo de dependencias",
            "",
            "> Arquivo **gerado**. As setas tracejadas sao lacunas abertas — os lugares onde a",
            "> cadeia ainda nao fecha.",
            "",
            "```mermaid",
            "flowchart TD",
            '    T["corpus de tarefas<br/>COMPUTATIONAL_EVIDENCE"] --> G["grader verificado<br/>COMPUTATIONAL_EVIDENCE"]',
            '    G --> I["instrumento<br/>COMPUTATIONAL_EVIDENCE"]',
            '    I -.->|"G-107 corpus sintetico"| V["validade externa"]',
            '    W["pesos locais"] -.->|"G-101 ausente"| C["capacidade medida"]',
            '    C --> D["deficit"]',
            '    D --> S["CSS"]',
            '    P["priors de capacidade<br/>ASSUMPTION"] -.->|"G-104 nao calibrados"| S',
            '    S --> A["alvo de dataset"]',
            '    F["ficha do modelo<br/>ASSUMPTION"] -.->|"G-108 nao verificada"| M["footprint de memoria"]',
            '    M --> R["cabe em 16 GB"]',
            '    T2["telemetria"] -.->|"G-102 ausente"| RO["roda em velocidade util"]',
            "",
            "    style C fill:#78350f,color:#fff",
            "    style S fill:#78350f,color:#fff",
            "    style A fill:#78350f,color:#fff",
            "    style I fill:#166534,color:#fff",
            "    style G fill:#166534,color:#fff",
            "```",
            "",
            "## Onde a cadeia fecha",
            "",
            "Do corpus ao instrumento verificado, sem lacuna pendurada: sao afirmacoes sobre",
            "codigo e corpus que estao no repositorio e reexecutam identicos.",
            "",
            "## Onde a cadeia nao fecha",
            "",
            "| Aresta ausente | Lacuna | Consequencia |",
            "|---|---|---|",
            "| pesos locais -> capacidade medida | `G-101` | nenhuma capacidade e medida; o CSS nao tem entrada |",
            "| priors calibrados -> CSS | `G-104` | mesmo com medicao, o alvo carrega premissa nao demonstrada |",
            "| ficha verificada -> footprint | `G-108` | o 'cabe?' herda a aproximacao da contagem de parametros |",
            "| telemetria -> velocidade util | `G-102` | caber nao e rodar, e o relatorio nao pode dizer que roda |",
            "| corpus real -> validade externa | `G-107` | o instrumento mede o gerador ate prova em contrario |",
            "",
            f"Lacunas registradas neste ciclo: **{count_gaps(ROOT / '02_OBSERVATION' / 'GAP_REGISTER.md')}**.",
        ]
    ) + "\n"


def build_experiment_result(tasks: TaskSet, rep, run_id: str) -> str:
    f = rep.falsifiers()
    disparados = [k for k, v in f.items() if v["disparado"]]
    partes = [
        "---",
        "artifact: EXPERIMENT_RESULT",
        "id: X-002",
        f"run_id: {run_id}",
        "generated_by: scripts/run_model_cycle.py",
        "cycle: C-002",
        "---",
        "",
        "# X-002 — resultado",
        "",
        "> Arquivo **gerado**. O protocolo esta em [X-002.md](X-002.md) e foi escrito antes.",
        "",
        "## Medidas",
        "",
        "| Símbolo | Medida | Valor | Alvo |",
        "|---|---|---:|---:|",
        f"| M1 | aceitacao do gabarito | {rep.gold_acceptance:.3f} | 1,000 |",
        f"| M2 | rejeicao de contraexemplo | {rep.counterexample_rejection:.3f} | 1,000 |",
        f"| M3 | precisao do rotulo | {rep.label_precision:.3f} | 1,000 |",
        f"| M4 | determinismo | {'identico' if rep.deterministic else 'DIVERGIU'} | identico |",
        f"| M5 | cobertura minima por capacidade | {min(rep.coverage.values(), default=0)} | ≥ 8 |",
        f"| M6 | margem de discriminacao agregada | {rep.discrimination_margin:.3f} | ≥ 0,200 |",
        f"| M7 | modos sem sonda | {len(rep.dead_modes)} | 0 |",
        "",
        "## Falsificadores",
        "",
        "| # | Criterio | Estado | Medido |",
        "|---|---|---|---|",
    ]
    for k, v in f.items():
        estado = "**DISPARADO**" if v["disparado"] else "nao disparado"
        partes.append(f"| {k} | {v['criterio']} | {estado} | `{v['medido']}` |")

    partes += [
        "",
        "## Sondas: prometido contra observado",
        "",
        "A promessa de cada sonda foi declarada em `runner.PROBES` antes da execucao.",
        "",
        "| Sonda | Escore | Prometido | Cumpriu | Observado |",
        "|---|---:|---|:---:|---|",
    ]
    for row in probe_expectations(tasks):
        partes.append(
            f"| `{row['sonda']}` | {row['escore']:.3f} | "
            f"{', '.join(f'`{m}`' for m in row['prometido']) or '—'} | "
            f"{'sim' if row['cumpriu'] else '**nao**'} | "
            f"{', '.join(f'`{m}`' for m in row['observado']) or '—'} |"
        )

    partes += [
        "",
        "## Sensibilidade por sonda",
        "",
        "Diagnostico de [CE-101](../COUNTEREXAMPLES/CE-101-margem-agregada-diluida.md), **nao**",
        "criterio: `F3` foi declarado sobre a margem agregada e permanece como estava.",
        "",
        "| Sonda | Tarefas no alvo | % do corpus | Queda no alvo | Queda agregada |",
        "|---|---:|---:|---:|---:|",
    ]
    for d in rep.probe_sensitivity():
        partes.append(
            f"| `{d['sonda']}` | {d['tarefas_no_alvo']} | {d['fracao_do_corpus']:.1%} | "
            f"{d['queda_no_alvo']:.3f} | {d['queda_agregada']:.3f} |"
        )

    partes += [
        "",
        "## Interpretacao",
        "",
        (
            f"**{len(disparados)} de 6 falsificadores dispararam** ({', '.join(disparados)})."
            if disparados
            else "**Nenhum falsificador disparou.**"
        ),
        "",
    ]
    if "F3" in disparados:
        partes += [
            "O escore agregado nao separa respondente correto de degenerado pela margem",
            "declarada. `C-102` foi retratada em",
            "[R-101](../../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) e o portao V3 esta",
            "bloqueado. A metrica **nao** foi trocada: redefinir um falsificador depois de",
            "ve-lo disparar seria ajustar o instrumento ao resultado.",
            "",
        ]
    partes += [
        "O que sobrevive: o grader aceita todo gabarito, rejeita todo contraexemplo com o",
        "rotulo correto, a suite e deterministica e nenhum modo declarado ficou sem sonda.",
        "Sao afirmacoes sobre **o instrumento**, e e tudo o que este ciclo autoriza dizer.",
        "",
        "## Interpretacao proibida",
        "",
        "Qualquer frase sobre a capacidade de qualquer modelo. Nenhum modelo foi executado.",
    ]
    return "\n".join(partes) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", help="lista separada por virgula")
    ap.add_argument("--ram", type=float, default=16.0, help="RAM da maquina de referencia, em GB")
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()

    run_id = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    print(f"ciclo C-002 — run_id {run_id}\n")

    tasks = TaskSet.load()
    reg = Registry.load()
    escolhidos = args.models.split(",") if args.models else [s.id for s in reg]

    print(f"corpus: {len(tasks)} tarefas, {len(reg)} modelos")
    print(f"  {corpus_provenance(reg)}\n")

    rep = evaluate_instrument(tasks)
    atlas = FailureAtlas.merged(
        [run_suite(tasks, p) for p, _ in PROBES], "sondas de calibracao"
    )

    for mid in escolhidos:
        a = Assessment.build(
            AssessmentInputs(model_id=mid, ram_bytes=args.ram * 1e9, run_id=run_id),
            reg, tasks, rep,
        )
        write(ROOT / "99_RELEASES" / "reports" / f"MCA-{mid}.md", a.render())
        write(ROOT / "99_RELEASES" / "reports" / f"MCA-{mid}.json", a.to_json())

    write(ROOT / "03_UNIFICATION" / "FAILURE_MAP.md",
          build_failure_map(tasks, rep, atlas, run_id))
    write(ROOT / "03_UNIFICATION" / "DEPENDENCY_DAG.md", build_dependency_dag(rep, run_id))
    write(ROOT / "04_VALIDATION" / "EXPERIMENTS" / "X-002-RESULT.md",
          build_experiment_result(tasks, rep, run_id))

    # Evidencia anexada as alegacoes. `record_run` retrata sozinho quando o falsificador
    # dispara, e **nunca** promove: promocao de status e decisao humana registrada.
    f = rep.falsifiers()
    ledger_path = ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml"
    if ledger_path.exists():
        ledger = ClaimLedger.load(ledger_path)
        ledger.record_run(
            {
                "C-101": {"falsified": f["F1"]["disparado"] or f["F2"]["disparado"],
                          "reason": "F1 ou F2 disparado: o grader diverge do proprio exemplo"},
                "C-102": {"falsified": f["F3"]["disparado"],
                          "reason": f"F3 disparado: margem agregada {f['F3']['medido']} "
                                    f"abaixo do limiar declarado (ver CE-101)"},
                "C-103": {"falsified": f["F5"]["disparado"],
                          "reason": "F5 disparado: tarefa sem grader ou cobertura fina"},
                "C-104": {"falsified": f["F6"]["disparado"],
                          "reason": "F6 disparado: modo de falha declarado sem sonda"},
                "C-105": {"falsified": f["F4"]["disparado"],
                          "reason": "F4 disparado: execucoes divergiram"},
            },
            run_id,
        )
        ledger.save(ledger_path)
        print(f"  escrito  {ledger_path.relative_to(REPO)}")

    print("\nresumo:")
    print(f"  aceitacao do gabarito       {rep.gold_acceptance:.1%}")
    print(f"  rejeicao de contraexemplo   {rep.counterexample_rejection:.1%}")
    print(f"  precisao do rotulo          {rep.label_precision:.1%}")
    print(f"  margem agregada             {rep.discrimination_margin:.3f}  "
          f"({'discrimina' if rep.discriminates else 'NAO discrimina'})")
    print(f"  modos sem sonda             {[str(m) for m in rep.dead_modes] or 'nenhum'}")
    disparados = [k for k, v in f.items() if v["disparado"]]
    print(f"  falsificadores disparados   {', '.join(disparados) or 'nenhum'}")

    if not args.skip_tests:
        import subprocess

        print("\nverificando a suite...")
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/core", "tests/model", "--tb=no"],
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
                        "Registro consumido pelo portao A5 em `matlas gates`. Gerado por "
                        "scripts/run_model_cycle.py; nao editar a mao."
                    ),
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        print(f"  suite: {'verde' if r.returncode == 0 else 'VERMELHA'} "
              f"({passed} passaram, {failed} falharam)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
