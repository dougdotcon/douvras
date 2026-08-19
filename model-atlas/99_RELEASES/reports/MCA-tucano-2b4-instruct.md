---
artifact: MODEL_CAPABILITY_ASSESSMENT
model: tucano-2b4-instruct
run_id: 20260819T135303Z
generated_at: 2026-08-19T13:53:03+00:00
method: DOUVRAS 2.0
cycle: C-002
weakest_status: ASSUMPTION
evaluable: true
---

# Model Capability Assessment — `tucano-2b4-instruct`

> Gerado por `scripts/run_model_cycle.py`. Nao editar a mao: e saida, nao entrada.

## 1 · A pergunta e a resposta

> **`tucano-2b4-instruct` esta pronto para ser especializado por dados, e em qual capacidade?**

**Nao — e o motivo e especifico.** Executado sobre **96 tarefas** do BR-Agent-Bench, `tucano-2b4-instruct` acertou **0.0 %** e emitiu **0 chamadas de ferramenta**.

Nao e que ele erre a ferramenta: ele **nunca chega a chamar uma**. Toda trajetoria termina no primeiro passo, com um objeto JSON que tem a forma do contrato e valores de exemplo — `"ferramenta": "nome_da_ferramenta"` copiado literalmente. O modelo descreve o protocolo em vez de executa-lo.

Isso **nao** significa que o modelo seja incapaz de portugues ou de instrucao: fora do protocolo de acao ele responde bem. Significa que, nesta quantizacao e com este prompt, ele nao instancia um schema de chamada de ferramenta.

**Os qualificadores fazem parte do resultado**, e sem eles o numero engana:

| Qualificador | Valor |
|---|---|
| prompt | `agent-ptbr-v2`, zero-shot |
| quantizacao | `q4` (tucano-2b4-instruct-q4_k_m.gguf) |
| formato de conversa | `raw-instruction` |
| modo | `padrao do modelo` |
| runtime | llama.cpp em CPU, temperatura 0 |
| teto de passos | 6 |

### O que este numero **nao** mede

Cada linha e uma execucao declarada como diagnostica: mesma suite, uma variavel trocada de proposito. Nenhuma delas e escore publicado — elas existem para limitar a leitura do escore que e.

| Variavel trocada | Tarefas | Escore | Chamadas | Comparar com |
|---|---:|---:|---:|---:|
| exemplo demonstrado no prompt | 16 | 0.0% | 0 | 0.0% |

A ultima coluna e o escore **das mesmas tarefas** na execucao publicada, para que a comparacao seja pareada e nao contra o agregado de 96.

## 2 · Ficha e proveniencia

| Campo | Valor |
|---|---|
| id | `tucano-2b4-instruct` |
| repositorio | `TucanoBR/Tucano-2b4-Instruct` |
| revisao | `main` |
| familia | tucano |
| parametros | ≈ 2.4446 B |
| contexto | 4096 |
| licenca | apache-2.0 |
| proveniencia | `UPSTREAM_VERIFIED` |
| pesos locais | sim |
| fonte | https://huggingface.co/api/models/TucanoBR/Tucano-2b4-Instruct |

Ficha **conferida na fonte** com hash e data (`G-108` fechada): a contagem de parametros e a do checkpoint, nao a do nome comercial, e por isso entra como `OBSERVATION` em vez de `ASSUMPTION`.

## 3 · Memoria e quantizacao

Maquina de referencia: **16 GB de RAM, sem GPU dedicada**.

| Quantizacao | Pesos | Com folga de runtime | Cabe? | Qualidade |
|---|---:|---:|:---:|:---:|
| `f16` | 4.89 GB | 5.87 GB | sim | — |
| `q8` | 2.59 GB | 3.11 GB | sim | — |
| `q6` | 2.00 GB | 2.41 GB | sim | — |
| `q5` | 1.69 GB | 2.02 GB | sim | — |
| `q4` | 1.37 GB | 1.64 GB | sim | — |
| `q3` | 1.08 GB | 1.29 GB | sim | — |

A coluna **Qualidade** esta vazia porque nenhuma perplexidade foi medida (`G-103`).
E a coluna que decide a escolha de quantizacao, e a unica que a aritmetica nao da.

Isto e aritmetica, nao medicao: parametros x bytes por parametro, com folga de runtime. Responde "cabe?" e nao responde "funciona bem?".

## 4 · Latencia e vazao

Medido em CPU, quantizacao `q4`, 96 tarefas.

| Metrica | Valor | Status |
|---|---:|---|
| tokens/s (geracao) | 12.14 | `OBSERVATION` |
| TTFT medio | 6.422 s | `OBSERVATION` |
| tokens gerados | 24455 | `OBSERVATION` |
| tempo total de modelo | 2630.3 s | `OBSERVATION` |
| RAM de pico | — | `OPEN_GAP` |

O TTFT aqui e o tempo de processamento do prompt reportado pelo servidor, nao um cronometro ate o primeiro token em streaming. E uma boa aproximacao e uma medida ruim se lida como outra coisa — por isso esta dito.

RAM de pico continua `OPEN_GAP`: exige instrumentar o processo, que este harness nao faz.

## 5 · Capacidades

| Capacidade | Escore | Status |
|---|---:|---|
| `arguments` | 0.0% | `OBSERVATION` |
| `error_recovery` | 0.0% | `OBSERVATION` |
| `hallucination` | 0.0% | `OBSERVATION` |
| `planning` | 0.0% | `OBSERVATION` |
| `pt_br_numeracy` | 0.0% | `OBSERVATION` |
| `safety_refusal` | 0.0% | `OBSERVATION` |
| `structured_output` | 0.0% | `OBSERVATION` |
| `tool_selection` | 0.0% | `OBSERVATION` |

## 6 · Modos de falha

```text
FONTE  tucano-2b4-instruct
│
├── ARGUMENTS
│   └── tool_selection     100.0%
│
├── ERROR_RECOVERY
│   ├── tool_selection     100.0%
│   └── recovery           100.0%
│
├── HALLUCINATION
│   ├── tool_selection     100.0%
│   └── hallucination       16.7%
│
├── PLANNING
│   ├── tool_selection      50.0%
│   └── planning            50.0%
│
├── PT_BR_NUMERACY
│   ├── tool_selection     100.0%
│   └── planning           100.0%
│
├── SAFETY_REFUSAL
│   ├── tool_selection     100.0%
│   └── safety             100.0%
│
├── STRUCTURED_OUTPUT
│   ├── tool_selection     100.0%
│   └── format             100.0%
│
└── TOOL_SELECTION
    └── tool_selection     100.0%
```

Celulas mais quentes das sondas — a leitura correta e "o grader detecta isto", nao "o modelo erra isto":

| Capacidade | Modo | Taxa |
|---|---|---:|
| `arguments` | `FAIL_TOOL_SELECTION` | 100.0% |
| `error_recovery` | `FAIL_TOOL_SELECTION` | 100.0% |
| `error_recovery` | `FAIL_RECOVERY` | 100.0% |
| `hallucination` | `FAIL_TOOL_SELECTION` | 100.0% |
| `pt_br_numeracy` | `FAIL_TOOL_SELECTION` | 100.0% |
| `pt_br_numeracy` | `FAIL_PLANNING` | 100.0% |
| `safety_refusal` | `FAIL_TOOL_SELECTION` | 100.0% |
| `safety_refusal` | `FAIL_SAFETY` | 100.0% |

## 7 · Alvo de especializacao (CSS)

Alvo: **`tool_selection`** (margem 0.00750 contra ruido 0.00457).

## 8 · Oportunidades de dataset

Derivadas dos modos que o instrumento **consegue** detectar. Sao hipoteses de produto, nao achados sobre este modelo:

- `FAIL_TOOL_SELECTION` em `arguments` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_TOOL_SELECTION` em `error_recovery` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_RECOVERY` em `error_recovery` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_TOOL_SELECTION` em `hallucination` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_TOOL_SELECTION` em `pt_br_numeracy` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader

A ordem so vira prioridade quando houver medicao real: hoje ela reflete a cobertura do corpus de tarefas, nao a fraqueza de nenhum modelo.

## 9 · Estado do instrumento

- tarefas no corpus: **96**
- aceitacao do gabarito: **100.0%** (96/96)
- rejeicao de contraexemplo: **100.0%** (144 declarados)
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

- **Mede** capacidade real de `tucano-2b4-instruct`, mas so nas 96 tarefas deste corpus, com o prompt e a quantizacao declarados na secao 1 — outro prompt ou outra quantizacao e outro instrumento (`G-112`, `G-113`).
- **Compara** com outro modelo real quando ambos tem execucao publicada, mas dois modelos nao sustentam ranking geral — sustentam contraexemplo (`C-108` retratada) e conjectura (`C-109`, `C-110`), nao lei de comportamento.
- **Nao** valida o corpus de tarefas contra desempenho humano — as tarefas sao sinteticas e a dificuldade declarada e de autoria, nao calibrada.
- **Nao** demonstra que as sondas cobrem o espaco de falhas reais; elas cobrem os modos **declarados**, que e coisa diferente.
- O numero de memoria diz que cabe, nao que roda em velocidade util.

## Anexo · rastreabilidade

| Resultado | Valor | Status | Premissas | Lacunas |
|---|---|---|---|---|
| `proveniencia_verificada` | 1 | `OBSERVATION` | — | — |
| `parametros` | 2444600000 parametros | `OBSERVATION` | — | — |
| `footprint_pesos.f16` | 4.889 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q8` | 2.591 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q6` | 2.005 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q5` | 1.687 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q4` | 1.369 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q3` | 1.076 GB | `ASSUMPTION` | A-102 | — |
| `quantizacoes_que_cabem` | ['f16', 'q8', 'q6', 'q5', 'q4', 'q3'] | `ASSUMPTION` | A-101, A-102 | — |
| `ttft` | 6.422 s | `OBSERVATION` | — | — |
| `tokens_por_segundo` | 12.14 tok/s | `OBSERVATION` | — | — |
| `ram_de_pico` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-102 |
| `capacidade.arguments` | 0 | `OBSERVATION` | — | — |
| `capacidade.error_recovery` | 0 | `OBSERVATION` | — | — |
| `capacidade.hallucination` | 0 | `OBSERVATION` | — | — |
| `capacidade.planning` | 0 | `OBSERVATION` | — | — |
| `capacidade.pt_br_numeracy` | 0 | `OBSERVATION` | — | — |
| `capacidade.safety_refusal` | 0 | `OBSERVATION` | — | — |
| `capacidade.structured_output` | 0 | `OBSERVATION` | — | — |
| `capacidade.tool_selection` | 0 | `OBSERVATION` | — | — |
| `tarefas_no_corpus` | 96 tarefas | `OBSERVATION` | — | — |
| `aceitacao_do_gabarito` | 1 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `rejeicao_de_contraexemplo` | 1 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `precisao_do_rotulo` | 1 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `margem_de_discriminacao` | 0.0625 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `instrumento_discrimina` | False | `COMPUTATIONAL_EVIDENCE` | — | G-105 |
| `queda_no_alvo_minima` | 0.25 | `COMPUTATIONAL_EVIDENCE` | — | — |
| `modos_de_falha_sem_sonda` | [] | `COMPUTATIONAL_EVIDENCE` | — | — |
| `css_alvo` | tool_selection | `COMPUTATIONAL_EVIDENCE` | — | G-104 |

Elo mais fraco do conjunto: **`ASSUMPTION`**. Divida de evidencia: **25.0%**.
