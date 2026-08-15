"""MODEL CAPABILITY ASSESSMENT — o produto de entrada do Model Atlas.

O analogo do `Silicon Readiness Assessment`, e com a mesma regra de ouro: o relatorio responde
a pergunta que originou o pedido **mesmo quando a resposta e "nao da para saber ainda"**, com
cada numero rastreavel ate sua premissa.

Neste ciclo a resposta e negativa por construcao, e isso e o resultado: nenhum peso local,
logo nenhuma capacidade medida, logo nenhum alvo de especializacao decidido. O que o relatorio
entrega no lugar e mais util que um numero inventado — o que ja se sabe por aritmetica (cabe
em 16 GB? em qual quantizacao?), o estado verificado do instrumento que vai medir, e a lista
exata do que fecha cada lacuna.

O portao de emissao recusa o relatorio se ele se contradizer: dizer "nenhuma capacidade foi
medida" na secao 5 enquanto o anexo publica um CSS e exatamente o defeito `G-012` que custou
uma retratacao no Silicon Atlas, e aqui ele e verificado por codigo.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from typing import Any

from douvras_core.report import (
    EmissionRefused,
    check_coherence,
    check_finite,
    check_no_hand_promotion,
    check_sections,
    check_vocabulary,
    evidence_appendix,
    frontmatter,
)
from douvras_core.status import Finding, FindingSet, Status

from . import css as css_mod
from .capability import CapabilityFingerprint
from .failure import FailureAtlas
from .instrument import InstrumentReport, evaluate_instrument
from .profiler import InferenceProfile, MemoryBudget
from .registry import Registry, corpus_provenance
from .runner import PROBES, run_suite
from .tasks import Capability, TaskSet

#: RAM de referencia do laboratorio (Documento 1, secao 4): 16 GB, sem GPU dedicada.
DEFAULT_RAM_BYTES = 16 * 1024**3

MANDATORY_SECTIONS: tuple[str, ...] = (
    "pergunta_e_resposta",
    "proveniencia",
    "memoria_e_quantizacao",
    "latencia_e_vazao",
    "capacidades",
    "modos_de_falha",
    "alvo_de_especializacao",
    "oportunidades_de_dataset",
    "estado_do_instrumento",
    "lacunas",
    "o_que_nao_demonstra",
)

#: Confrontos texto x `Finding` exigidos pelo portao (`G-012`).
COHERENCE_RULES: tuple[tuple[str, str], ...] = (
    (r"nenhuma capacidade foi medida", "css_alvo"),
    (r"nenhuma execucao real ocorreu", "tokens_por_segundo"),
)


@dataclass
class AssessmentInputs:
    model_id: str
    ram_bytes: float = DEFAULT_RAM_BYTES
    run_id: str = ""


@dataclass
class Assessment:
    spec: Any
    tasks: TaskSet
    instrument: InstrumentReport
    fingerprint: CapabilityFingerprint
    atlas: FailureAtlas
    budget: MemoryBudget
    profile: InferenceProfile
    css_result: css_mod.CSSResult
    findings: FindingSet
    inputs: AssessmentInputs
    run_id: str = ""
    generated_at: str = ""

    # ------------------------------------------------------------------ construcao ---
    @classmethod
    def build(
        cls,
        inputs: AssessmentInputs,
        registry: Registry | None = None,
        tasks: TaskSet | None = None,
        instrument: InstrumentReport | None = None,
    ) -> "Assessment":
        # `is None`, nao `or`: um `TaskSet` vazio tem `len() == 0` e portanto e *falsy*, e
        # `tasks or TaskSet.load()` trocava silenciosamente o corpus explicitamente passado
        # pelo corpus padrao. O relatorio saia completo, com 96 tarefas, para quem pediu
        # zero — que e a forma mais silenciosa de um assessment falar de outra coisa.
        reg = Registry.load() if registry is None else registry
        spec = reg[inputs.model_id]
        ts = TaskSet.load() if tasks is None else tasks
        inst = evaluate_instrument(ts) if instrument is None else instrument

        # Sem pesos locais nao ha execucao real. As sondas rodam mesmo assim, porque o que elas
        # medem — se o instrumento enxerga cada modo de falha — vale independentemente do modelo.
        fp = CapabilityFingerprint.unmeasured(spec.id, sorted(ts.by_capability(), key=str))
        atlas = FailureAtlas.merged(
            [run_suite(ts, p) for p, _ in PROBES], source="sondas de calibracao"
        )

        budget = MemoryBudget.build(spec)
        profile = InferenceProfile(model_id=spec.id, measured=False)

        priors = css_mod.load_priors()
        candidatos = css_mod.build_candidates(fp, priors)
        css_res = css_mod.score(candidatos, css_mod.Weights.load())

        fs = FindingSet(f"MODEL CAPABILITY ASSESSMENT — {spec.id}")
        fs.add(corpus_provenance(reg))
        fs.extend(budget.findings(inputs.ram_bytes).items)
        fs.extend(profile.findings().items)
        fs.extend(fp.findings().items)
        fs.extend(inst.findings().items)
        fs.add(css_mod.css_finding(fp, css_res))

        run_id = inputs.run_id or _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        return cls(
            spec=spec,
            tasks=ts,
            instrument=inst,
            fingerprint=fp,
            atlas=atlas,
            budget=budget,
            profile=profile,
            css_result=css_res,
            findings=fs,
            inputs=inputs,
            run_id=run_id,
            generated_at=(
                f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}T"
                f"{run_id[9:11]}:{run_id[11:13]}:{run_id[13:15]}+00:00"
            ),
        )

    # --------------------------------------------------------------------- secoes ---
    @property
    def evaluable(self) -> bool:
        """O assessment consegue responder sobre capacidade, ou so sobre o instrumento?"""
        return self.fingerprint.measured

    def sections(self) -> dict[str, str]:
        s: dict[str, str] = {}

        s["pergunta_e_resposta"] = "\n".join(
            [
                "## 1 · A pergunta e a resposta",
                "",
                f"> **`{self.spec.id}` esta pronto para ser especializado por dados, e em qual "
                f"capacidade?**",
                "",
                (
                    "**Ainda nao da para responder, e o motivo e verificavel.** Nao ha pesos "
                    "locais para este modelo, portanto **nenhuma execucao real ocorreu** e "
                    "**nenhuma capacidade foi medida**. Um assessment que respondesse mesmo "
                    "assim estaria reportando o comportamento das sondas de calibracao como se "
                    "fosse o do modelo."
                    if not self.evaluable
                    else
                    f"Capacidade medida sobre {len(self.tasks)} tarefas do BR-Agent-Bench. "
                    f"Pior capacidade observada: `{self.fingerprint.weakest[0]}`."
                ),
                "",
                "O que **sim** foi estabelecido neste ciclo esta na secao 9: o instrumento que "
                "fara a medicao foi verificado contra gabaritos e contraexemplos.",
            ]
        )

        s["proveniencia"] = "\n".join(
            [
                "## 2 · Ficha e proveniencia",
                "",
                "| Campo | Valor |",
                "|---|---|",
                f"| id | `{self.spec.id}` |",
                f"| repositorio | `{self.spec.repo}` |",
                f"| revisao | `{self.spec.revision}` |",
                f"| familia | {self.spec.family or '—'} |",
                f"| parametros | {f'≈ {self.spec.params_b} B' if self.spec.params_b else '—'} |",
                f"| contexto | {self.spec.context_len or '—'} |",
                f"| licenca | {self.spec.license or '—'} |",
                f"| proveniencia | `{self.spec.provenance}` |",
                f"| pesos locais | {'sim' if self.spec.weights_local else '**nao**'} |",
                f"| fonte | {self.spec.source or '—'} |",
                "",
                "A contagem de parametros e **aproximada** (`A-101`): a fonte diz \"cerca de\", e "
                "transformar isso num inteiro exato seria inventar digitos. Nenhuma ficha deste "
                "corpus foi conferida contra o upstream — `G-108`, fechada por "
                "`matlas registry verify`.",
            ]
        )

        s["memoria_e_quantizacao"] = "\n".join(
            [
                "## 3 · Memoria e quantizacao",
                "",
                f"Maquina de referencia: **{self.inputs.ram_bytes / 1e9:.0f} GB de RAM, sem GPU "
                f"dedicada**.",
                "",
                self.budget.render(self.inputs.ram_bytes),
                "",
                "Isto e aritmetica, nao medicao: parametros x bytes por parametro, com folga de "
                "runtime. Responde \"cabe?\" e nao responde \"funciona bem?\".",
            ]
        )

        s["latencia_e_vazao"] = "\n".join(
            [
                "## 4 · Latencia e vazao",
                "",
                "| Metrica | Valor | Status |",
                "|---|---|---|",
                "| TTFT | — | `OPEN_GAP` |",
                "| tokens/s | — | `OPEN_GAP` |",
                "| RAM de pico | — | `OPEN_GAP` |",
                "",
                "Nao existe formula honesta para latencia numa maquina que nunca executou o "
                "modelo. `G-102` fecha com uma execucao instrumentada; ate la a ausencia e "
                "declarada em vez de estimada.",
            ]
        )

        s["capacidades"] = "\n".join(
            ["## 5 · Capacidades", "", self.fingerprint.render()]
        )

        quentes = self.atlas.dominant()[:8]
        s["modos_de_falha"] = "\n".join(
            [
                "## 6 · Modos de falha",
                "",
                "```text",
                self.atlas.render_tree(),
                "```",
                "",
                "Celulas mais quentes das sondas — a leitura correta e \"o grader detecta isto\", "
                "nao \"o modelo erra isto\":",
                "",
                "| Capacidade | Modo | Taxa |",
                "|---|---|---:|",
                *[f"| `{c}` | `{m}` | {r:.1%} |" for c, m, r in quentes],
            ]
        )

        if self.evaluable and self.css_result.leader:
            alvo = (
                f"Alvo: **`{self.css_result.leader}`** "
                f"(margem {self.css_result.leader_margin:.5f} contra ruido "
                f"{self.css_result.weight_noise:.5f})."
                if self.css_result.discriminates
                else (
                    f"O CSS **nao discrimina**: o lider `{self.css_result.leader}` vence por "
                    f"{self.css_result.leader_margin:.5f}, menos que o ruido dos proprios pesos "
                    f"({self.css_result.weight_noise:.5f}). Nenhum alvo e decidido."
                )
            )
        else:
            alvo = (
                "Sem capacidade medida nao existe deficit, e sem deficit nao existe CSS. O motor "
                "esta implementado e exercitado sob teste com fingerprint sintetico — a licao do "
                "`G-014` do Silicon Atlas, onde todo o caminho economico atravessou um ciclo sem "
                "nunca ter sido executado."
            )
        s["alvo_de_especializacao"] = "\n".join(
            ["## 7 · Alvo de especializacao (CSS)", "", alvo]
        )

        s["oportunidades_de_dataset"] = "\n".join(
            [
                "## 8 · Oportunidades de dataset",
                "",
                "Derivadas dos modos que o instrumento **consegue** detectar. Sao hipoteses de "
                "produto, nao achados sobre este modelo:",
                "",
                *[
                    f"- `{m}` em `{c}` — dataset dirigido a esse par, medido antes e depois "
                    f"pelo mesmo grader"
                    for c, m, _ in quentes[:5]
                ],
                "",
                "A ordem so vira prioridade quando houver medicao real: hoje ela reflete a "
                "cobertura do corpus de tarefas, nao a fraqueza de nenhum modelo.",
            ]
        )

        f = self.instrument.falsifiers()
        s["estado_do_instrumento"] = "\n".join(
            [
                "## 9 · Estado do instrumento",
                "",
                f"- tarefas no corpus: **{self.instrument.tasks}**",
                f"- aceitacao do gabarito: **{self.instrument.gold_acceptance:.1%}** "
                f"({self.instrument.gold_accepted}/{self.instrument.gold_total})",
                f"- rejeicao de contraexemplo: **{self.instrument.counterexample_rejection:.1%}** "
                f"({len(self.instrument.counterexamples)} declarados)",
                f"- precisao do rotulo: **{self.instrument.label_precision:.1%}**",
                f"- margem de discriminacao: **{self.instrument.discrimination_margin:.3f}** "
                f"({'discrimina' if self.instrument.discriminates else 'NAO discrimina'})",
                f"- modos de falha sem sonda: "
                f"**{[str(m) for m in self.instrument.dead_modes] or 'nenhum'}**",
                "",
                "| Falsificador | Estado |",
                "|---|---|",
                *[
                    f"| {k} — {v['criterio']} | "
                    f"{'**disparado**' if v['disparado'] else 'nao disparado'} |"
                    for k, v in f.items()
                ],
            ]
        )

        s["lacunas"] = "\n".join(
            [
                "## 10 · Lacunas que travam este resultado",
                "",
                "| Lacuna | O que fecha |",
                "|---|---|",
                "| `G-101` — nenhuma execucao real | baixar pesos e rodar a suite (`[run]`) |",
                "| `G-102` — sem telemetria | execucao instrumentada com TTFT e tokens/s |",
                "| `G-103` — precision cliff nao medido | qualidade por quantizacao na mesma suite |",
                "| `G-104` — priors do CSS nao calibrados | tres casos com desfecho conhecido |",
                "| `G-105` — limiar de discriminacao sem base | replicacao com benchmarks publicos |",
                "| `G-108` — corpus transcrito | `matlas registry verify` contra o Hub |",
                "",
                f"Lacunas abertas mantem todo derivado em `CONDITIONAL_RESULT` ou abaixo. Elo "
                f"mais fraco deste conjunto: **`{self.findings.weakest.name}`**.",
            ]
        )

        s["o_que_nao_demonstra"] = "\n".join(
            [
                "## 11 · O que este relatorio nao demonstra",
                "",
                "- **Nao** mede nenhuma capacidade de `" + self.spec.id + "`.",
                "- **Nao** compara modelos: sem execucao nao ha ranking.",
                "- **Nao** valida o corpus de tarefas contra desempenho humano — as tarefas sao "
                "sinteticas e a dificuldade declarada e de autoria, nao calibrada.",
                "- **Nao** demonstra que as sondas cobrem o espaco de falhas reais; elas cobrem "
                "os modos **declarados**, que e coisa diferente.",
                "- O numero de memoria diz que cabe, nao que roda em velocidade util.",
            ]
        )
        return s

    # --------------------------------------------------------------------- emissao ---
    def render(self) -> str:
        secoes = self.sections()
        check_sections(secoes, MANDATORY_SECTIONS)
        check_finite(self.findings)
        check_no_hand_promotion(self.findings)

        if self.instrument.gold_total == 0:
            raise EmissionRefused(
                "corpus de tarefas vazio: nao ha instrumento a reportar, e um assessment sobre "
                "nenhuma tarefa e um documento sobre nada"
            )

        texto = self._assemble(secoes)
        check_coherence(texto, self.findings, COHERENCE_RULES)
        check_vocabulary(texto)
        return texto

    def _assemble(self, secoes: dict[str, str]) -> str:
        cab = frontmatter(
            artifact="MODEL_CAPABILITY_ASSESSMENT",
            model=self.spec.id,
            run_id=self.run_id,
            generated_at=self.generated_at,
            method="DOUVRAS 2.0",
            cycle="C-002",
            weakest_status=self.findings.weakest.name,
            evaluable=str(self.evaluable).lower(),
        )
        corpo = [
            cab,
            "",
            f"# Model Capability Assessment — `{self.spec.id}`",
            "",
            "> Gerado por `scripts/run_model_cycle.py`. Nao editar a mao: e saida, nao entrada.",
            "",
        ]
        corpo += [secoes[k] + "\n" for k in MANDATORY_SECTIONS]
        corpo.append(evidence_appendix(self.findings, "Anexo · rastreabilidade"))
        return "\n".join(corpo).rstrip() + "\n"

    def to_json(self) -> str:
        return json.dumps(
            {
                "artifact": "MODEL_CAPABILITY_ASSESSMENT",
                "run_id": self.run_id,
                "generated_at": self.generated_at,
                "cycle": "C-002",
                "model": self.spec.as_dict(),
                "evaluable": self.evaluable,
                "capabilities": self.fingerprint.as_dict(),
                "failure_atlas": self.atlas.as_dict(),
                "css": self.css_result.as_dict(),
                "instrument": {
                    "tasks": self.instrument.tasks,
                    "coverage": self.instrument.coverage,
                    "gold_acceptance": round(self.instrument.gold_acceptance, 4),
                    "counterexample_rejection": round(
                        self.instrument.counterexample_rejection, 4
                    ),
                    "label_precision": round(self.instrument.label_precision, 4),
                    "discrimination_margin": round(self.instrument.discrimination_margin, 4),
                    "falsifiers": self.instrument.falsifiers(),
                },
                "findings": self.findings.as_dict(),
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )


__all__ = [
    "Assessment",
    "AssessmentInputs",
    "EmissionRefused",
    "MANDATORY_SECTIONS",
    "COHERENCE_RULES",
    "DEFAULT_RAM_BYTES",
]
