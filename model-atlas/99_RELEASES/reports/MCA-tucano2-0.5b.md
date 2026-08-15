---
artifact: MODEL_CAPABILITY_ASSESSMENT
model: tucano2-0.5b
run_id: 20260815T095603Z
generated_at: 2026-08-15T09:56:03+00:00
method: DOUVRAS 2.0
cycle: C-002
weakest_status: ASSUMPTION
evaluable: false
---

# Model Capability Assessment — `tucano2-0.5b`

> Gerado por `scripts/run_model_cycle.py`. Nao editar a mao: e saida, nao entrada.

## 1 · A pergunta e a resposta

> **`tucano2-0.5b` esta pronto para ser especializado por dados, e em qual capacidade?**

**Ainda nao da para responder, e o motivo e verificavel.** Nao ha pesos locais para este modelo, portanto **nenhuma execucao real ocorreu** e **nenhuma capacidade foi medida**. Um assessment que respondesse mesmo assim estaria reportando o comportamento das sondas de calibracao como se fosse o do modelo.

O que **sim** foi estabelecido esta na secao 9: o instrumento que fara a medicao foi verificado contra gabaritos e contraexemplos.

## 2 · Ficha e proveniencia

| Campo | Valor |
|---|---|
| id | `tucano2-0.5b` |
| repositorio | `Polygl0t/Tucano2-qwen-0.5B-Base` |
| revisao | `main` |
| familia | tucano |
| parametros | ≈ 0.4908 B |
| contexto | 4096 |
| licenca | apache-2.0 |
| proveniencia | `UPSTREAM_VERIFIED` |
| pesos locais | **nao** |
| fonte | https://huggingface.co/api/models/Polygl0t/Tucano2-qwen-0.5B-Base |

Ficha **conferida na fonte** com hash e data (`G-108` fechada): a contagem de parametros e a do checkpoint, nao a do nome comercial, e por isso entra como `OBSERVATION` em vez de `ASSUMPTION`.

## 3 · Memoria e quantizacao

Maquina de referencia: **16 GB de RAM, sem GPU dedicada**.

| Quantizacao | Pesos | Com folga de runtime | Cabe? | Qualidade |
|---|---:|---:|:---:|:---:|
| `f16` | 0.98 GB | 1.18 GB | sim | — |
| `q8` | 0.52 GB | 0.62 GB | sim | — |
| `q6` | 0.40 GB | 0.48 GB | sim | — |
| `q5` | 0.34 GB | 0.41 GB | sim | — |
| `q4` | 0.27 GB | 0.33 GB | sim | — |
| `q3` | 0.22 GB | 0.26 GB | sim | — |

A coluna **Qualidade** esta vazia porque nenhuma perplexidade foi medida (`G-103`).
E a coluna que decide a escolha de quantizacao, e a unica que a aritmetica nao da.

Isto e aritmetica, nao medicao: parametros x bytes por parametro, com folga de runtime. Responde "cabe?" e nao responde "funciona bem?".

## 4 · Latencia e vazao

| Metrica | Valor | Status |
|---|---|---|
| TTFT | — | `OPEN_GAP` |
| tokens/s | — | `OPEN_GAP` |
| RAM de pico | — | `OPEN_GAP` |

Nao existe formula honesta para latencia numa maquina que nunca executou o modelo. `G-102` fecha com uma execucao instrumentada; ate la a ausencia e declarada em vez de estimada.

## 5 · Capacidades

| Capacidade | Escore | Status |
|---|---:|---|
| `arguments` | — | `OPEN_GAP` |
| `error_recovery` | — | `OPEN_GAP` |
| `hallucination` | — | `OPEN_GAP` |
| `planning` | — | `OPEN_GAP` |
| `pt_br_numeracy` | — | `OPEN_GAP` |
| `safety_refusal` | — | `OPEN_GAP` |
| `structured_output` | — | `OPEN_GAP` |
| `tool_selection` | — | `OPEN_GAP` |

Nenhuma capacidade foi medida: o corpus nao tem pesos locais e nenhuma execucao real ocorreu. Os tracos nao sao zeros — sao ausencias declaradas.

## 6 · Modos de falha

```text
FONTE  sondas de calibracao  (sintetica)
│
├── ARGUMENTS
│   ├── tool_selection      25.0%
│   └── argument            12.5%
│
├── ERROR_RECOVERY
│   ├── recovery            43.8%
│   ├── tool_selection      12.5%
│   └── hallucination        6.2%
│
├── HALLUCINATION
│   ├── tool_selection      12.5%
│   └── hallucination       12.5%
│
├── PLANNING
│   ├── planning            18.8%
│   ├── tool_selection      12.5%
│   └── argument             6.2%
│
├── PT_BR_NUMERACY
│   ├── planning            37.5%
│   ├── tool_selection      25.0%
│   └── argument             4.2%
│
├── SAFETY_REFUSAL
│   ├── safety              50.0%
│   └── tool_selection      25.0%
│
├── STRUCTURED_OUTPUT
│   ├── format              37.5%
│   └── tool_selection      12.5%
│
└── TOOL_SELECTION
    ├── tool_selection      25.0%
    └── hallucination       25.0%

Estas taxas descrevem as sondas de calibracao, nao um modelo. Elas mostram que
a taxonomia esta viva — cada celula preenchida e um modo que o grader consegue
detectar quando acontece.
```

Celulas mais quentes das sondas — a leitura correta e "o grader detecta isto", nao "o modelo erra isto":

| Capacidade | Modo | Taxa |
|---|---|---:|
| `safety_refusal` | `FAIL_SAFETY` | 50.0% |
| `error_recovery` | `FAIL_RECOVERY` | 43.8% |
| `pt_br_numeracy` | `FAIL_PLANNING` | 37.5% |
| `structured_output` | `FAIL_FORMAT` | 37.5% |
| `arguments` | `FAIL_TOOL_SELECTION` | 25.0% |
| `pt_br_numeracy` | `FAIL_TOOL_SELECTION` | 25.0% |
| `safety_refusal` | `FAIL_TOOL_SELECTION` | 25.0% |
| `tool_selection` | `FAIL_TOOL_SELECTION` | 25.0% |

## 7 · Alvo de especializacao (CSS)

Sem capacidade medida nao existe deficit, e sem deficit nao existe CSS. O motor esta implementado e exercitado sob teste com fingerprint sintetico — a licao do `G-014` do Silicon Atlas, onde todo o caminho economico atravessou um ciclo sem nunca ter sido executado.

## 8 · Oportunidades de dataset

Derivadas dos modos que o instrumento **consegue** detectar. Sao hipoteses de produto, nao achados sobre este modelo:

- `FAIL_SAFETY` em `safety_refusal` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_RECOVERY` em `error_recovery` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_PLANNING` em `pt_br_numeracy` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_FORMAT` em `structured_output` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_TOOL_SELECTION` em `arguments` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader

A ordem so vira prioridade quando houver medicao real: hoje ela reflete a cobertura do corpus de tarefas, nao a fraqueza de nenhum modelo.

## 9 · Estado do instrumento

- tarefas no corpus: **96**
- aceitacao do gabarito: **100.0%** (96/96)
- rejeicao de contraexemplo: **100.0%** (132 declarados)
- precisao do rotulo: **100.0%**
- margem de discriminacao: **0.062** (NAO discrimina)
- modos de falha sem sonda: **nenhum**

| Falsificador | Estado |
|---|---|
| F1 — o grader aceita alguma trajetoria declarada como errada | nao disparado |
| F2 — o grader rejeita a trajetoria de referencia de alguma tarefa | nao disparado |
| F3 — o escore separa o oraculo da melhor sonda degenerada por menos de 0.20 | **disparado** |
| F4 — duas execucoes da mesma suite produzem resultados diferentes | nao disparado |
| F5 — alguma tarefa nao e avaliavel, ou alguma capacidade tem menos de 8 tarefas | nao disparado |
| F6 — algum modo de falha declarado nunca e disparado por nenhuma sonda | nao disparado |

## 10 · Lacunas que travam este resultado

| Lacuna | O que fecha |
|---|---|
| `G-101` — nenhuma execucao real | baixar pesos e rodar a suite (`[run]`) |
| `G-102` — sem telemetria | execucao instrumentada com TTFT e tokens/s |
| `G-103` — precision cliff nao medido | qualidade por quantizacao na mesma suite |
| `G-104` — priors do CSS nao calibrados | tres casos com desfecho conhecido |
| `G-105` — limiar de discriminacao sem base | replicacao com benchmarks publicos |
| `G-108` — corpus transcrito | `matlas registry verify` contra o Hub |

Lacunas abertas mantem todo derivado em `CONDITIONAL_RESULT` ou abaixo. Elo mais fraco deste conjunto: **`ASSUMPTION`**.

## 11 · O que este relatorio nao demonstra

- **Nao** mede nenhuma capacidade de `tucano2-0.5b`.
- **Nao** compara modelos: sem execucao nao ha ranking.
- **Nao** valida o corpus de tarefas contra desempenho humano — as tarefas sao sinteticas e a dificuldade declarada e de autoria, nao calibrada.
- **Nao** demonstra que as sondas cobrem o espaco de falhas reais; elas cobrem os modos **declarados**, que e coisa diferente.
- O numero de memoria diz que cabe, nao que roda em velocidade util.

## Anexo · rastreabilidade

| Resultado | Valor | Status | Premissas | Lacunas |
|---|---|---|---|---|
| `proveniencia_verificada` | 1 | `OBSERVATION` | — | — |
| `parametros` | 490800000 parametros | `OBSERVATION` | — | — |
| `footprint_pesos.f16` | 0.982 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q8` | 0.52 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q6` | 0.402 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q5` | 0.339 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q4` | 0.275 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q3` | 0.216 GB | `ASSUMPTION` | A-102 | — |
| `quantizacoes_que_cabem` | ['f16', 'q8', 'q6', 'q5', 'q4', 'q3'] | `ASSUMPTION` | A-101, A-102 | — |
| `ttft` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-102 |
| `tokens_por_segundo` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-102 |
| `ram_de_pico` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-102 |
| `capacidade.arguments` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.error_recovery` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.hallucination` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.planning` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.pt_br_numeracy` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.safety_refusal` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.structured_output` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `capacidade.tool_selection` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |
| `tarefas_no_corpus` | 96 tarefas | `OBSERVATION` | — | — |
| `aceitacao_do_gabarito` | 1 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `rejeicao_de_contraexemplo` | 1 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `precisao_do_rotulo` | 1 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `margem_de_discriminacao` | 0.0625 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `instrumento_discrimina` | False | `COMPUTATIONAL_EVIDENCE` | — | G-105 |
| `queda_no_alvo_minima` | 0.25 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `modos_de_falha_sem_sonda` | [] | `COMPUTATIONAL_EVIDENCE` | — | — |
| `css_alvo` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-101 |

Elo mais fraco do conjunto: **`ASSUMPTION`**. Divida de evidencia: **41.2%**.
