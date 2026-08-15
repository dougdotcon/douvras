---
artifact: MODEL_CAPABILITY_ASSESSMENT
model: smollm3-3b
run_id: 20260815T113727Z
generated_at: 2026-08-15T11:37:27+00:00
method: DOUVRAS 2.0
cycle: C-002
weakest_status: ASSUMPTION
evaluable: true
---

# Model Capability Assessment — `smollm3-3b`

> Gerado por `scripts/run_model_cycle.py`. Nao editar a mao: e saida, nao entrada.

## 1 · A pergunta e a resposta

> **`smollm3-3b` esta pronto para ser especializado por dados, e em qual capacidade?**

**Nao — e o motivo e especifico.** Executado sobre **96 tarefas** do BR-Agent-Bench, `smollm3-3b` acertou **10.4 %** e emitiu **78 chamadas de ferramenta**.

O modelo **executa** o protocolo: 78 chamadas de ferramenta em 96 tarefas, com trajetorias de multiplos passos. O que falha nao e a forma da acao, e a **escolha** dela.

Onde ele passa: `arguments` (50%), `error_recovery` (33%). Nas demais capacidades o escore e zero, e o perfil por capacidade — nao o agregado — e o que torna essa diferenca legivel (`C-109`).

**Os qualificadores fazem parte do resultado**, e sem eles o numero engana:

| Qualificador | Valor |
|---|---|
| prompt | `agent-ptbr-v2`, zero-shot |
| quantizacao | `q4` (smollm3-3b-q4_k_m.gguf) |
| formato de conversa | `chat-template` |
| modo | `/no_think` |
| runtime | llama.cpp em CPU, temperatura 0 |
| teto de passos | 6 |

### O que este numero **nao** mede

Cada linha e uma execucao declarada como diagnostica: mesma suite, uma variavel trocada de proposito. Nenhuma delas e escore publicado — elas existem para limitar a leitura do escore que e.

| Variavel trocada | Tarefas | Escore | Chamadas | Comparar com |
|---|---:|---:|---:|---:|
| modo padrao do modelo (raciocinio ligado) | 16 | 31.2% | 14 | 12.5% |

A ultima coluna e o escore **das mesmas tarefas** na execucao publicada, para que a comparacao seja pareada e nao contra o agregado de 96.

**O escore publicado e portanto um piso, nao a capacidade.** No modo padrao do modelo, o modelo ganha **+18.8 pontos** no mesmo recorte de 16 tarefas. Um ranking construido sobre o numero de cima classificaria este modelo abaixo do que ele faz por padrao.

## 2 · Ficha e proveniencia

| Campo | Valor |
|---|---|
| id | `smollm3-3b` |
| repositorio | `HuggingFaceTB/SmolLM3-3B` |
| revisao | `main` |
| familia | smollm |
| parametros | ≈ 3.0751 B |
| contexto | 65536 |
| licenca | apache-2.0 |
| proveniencia | `UPSTREAM_VERIFIED` |
| pesos locais | sim |
| fonte | https://huggingface.co/api/models/HuggingFaceTB/SmolLM3-3B |

Ficha **conferida na fonte** com hash e data (`G-108` fechada): a contagem de parametros e a do checkpoint, nao a do nome comercial, e por isso entra como `OBSERVATION` em vez de `ASSUMPTION`.

## 3 · Memoria e quantizacao

Maquina de referencia: **16 GB de RAM, sem GPU dedicada**.

| Quantizacao | Pesos | Com folga de runtime | Cabe? | Qualidade |
|---|---:|---:|:---:|:---:|
| `f16` | 6.15 GB | 7.38 GB | sim | — |
| `q8` | 3.26 GB | 3.91 GB | sim | — |
| `q6` | 2.52 GB | 3.03 GB | sim | — |
| `q5` | 2.12 GB | 2.55 GB | sim | — |
| `q4` | 1.72 GB | 2.07 GB | sim | — |
| `q3` | 1.35 GB | 1.62 GB | sim | — |

A coluna **Qualidade** esta vazia porque nenhuma perplexidade foi medida (`G-103`).
E a coluna que decide a escolha de quantizacao, e a unica que a aritmetica nao da.

Isto e aritmetica, nao medicao: parametros x bytes por parametro, com folga de runtime. Responde "cabe?" e nao responde "funciona bem?".

## 4 · Latencia e vazao

Medido em CPU, quantizacao `q4`, 96 tarefas.

| Metrica | Valor | Status |
|---|---:|---|
| tokens/s (geracao) | 8.26 | `OBSERVATION` |
| TTFT medio | 9.086 s | `OBSERVATION` |
| tokens gerados | 8708 | `OBSERVATION` |
| tempo total de modelo | 2916.5 s | `OBSERVATION` |
| RAM de pico | — | `OPEN_GAP` |

O TTFT aqui e o tempo de processamento do prompt reportado pelo servidor, nao um cronometro ate o primeiro token em streaming. E uma boa aproximacao e uma medida ruim se lida como outra coisa — por isso esta dito.

RAM de pico continua `OPEN_GAP`: exige instrumentar o processo, que este harness nao faz.

## 5 · Capacidades

| Capacidade | Escore | Status |
|---|---:|---|
| `arguments` | 50.0% | `OBSERVATION` |
| `error_recovery` | 33.3% | `OBSERVATION` |
| `hallucination` | 0.0% | `OBSERVATION` |
| `planning` | 0.0% | `OBSERVATION` |
| `pt_br_numeracy` | 0.0% | `OBSERVATION` |
| `safety_refusal` | 0.0% | `OBSERVATION` |
| `structured_output` | 0.0% | `OBSERVATION` |
| `tool_selection` | 0.0% | `OBSERVATION` |

## 6 · Modos de falha

```text
FONTE  smollm3-3b
│
├── ARGUMENTS
│   ├── argument            50.0%
│   └── planning            50.0%
│
├── ERROR_RECOVERY
│   └── recovery            66.7%
│
├── HALLUCINATION
│   └── tool_selection     100.0%
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
│   └── format             100.0%
│
└── TOOL_SELECTION
    └── tool_selection     100.0%
```

Celulas mais quentes das sondas — a leitura correta e "o grader detecta isto", nao "o modelo erra isto":

| Capacidade | Modo | Taxa |
|---|---|---:|
| `hallucination` | `FAIL_TOOL_SELECTION` | 100.0% |
| `pt_br_numeracy` | `FAIL_TOOL_SELECTION` | 100.0% |
| `pt_br_numeracy` | `FAIL_PLANNING` | 100.0% |
| `safety_refusal` | `FAIL_TOOL_SELECTION` | 100.0% |
| `safety_refusal` | `FAIL_SAFETY` | 100.0% |
| `structured_output` | `FAIL_FORMAT` | 100.0% |
| `tool_selection` | `FAIL_TOOL_SELECTION` | 100.0% |
| `error_recovery` | `FAIL_RECOVERY` | 66.7% |

## 7 · Alvo de especializacao (CSS)

Alvo: **`tool_selection`** (margem 0.00750 contra ruido 0.00457).

## 8 · Oportunidades de dataset

Derivadas dos modos que o instrumento **consegue** detectar. Sao hipoteses de produto, nao achados sobre este modelo:

- `FAIL_TOOL_SELECTION` em `hallucination` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_TOOL_SELECTION` em `pt_br_numeracy` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_PLANNING` em `pt_br_numeracy` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_TOOL_SELECTION` em `safety_refusal` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader
- `FAIL_SAFETY` em `safety_refusal` — dataset dirigido a esse par, medido antes e depois pelo mesmo grader

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

- **Nao** mede nenhuma capacidade de `smollm3-3b`.
- **Nao** compara modelos: sem execucao nao ha ranking.
- **Nao** valida o corpus de tarefas contra desempenho humano — as tarefas sao sinteticas e a dificuldade declarada e de autoria, nao calibrada.
- **Nao** demonstra que as sondas cobrem o espaco de falhas reais; elas cobrem os modos **declarados**, que e coisa diferente.
- O numero de memoria diz que cabe, nao que roda em velocidade util.

## Anexo · rastreabilidade

| Resultado | Valor | Status | Premissas | Lacunas |
|---|---|---|---|---|
| `proveniencia_verificada` | 1 | `OBSERVATION` | — | — |
| `parametros` | 3075100000 parametros | `OBSERVATION` | — | — |
| `footprint_pesos.f16` | 6.15 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q8` | 3.26 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q6` | 2.522 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q5` | 2.122 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q4` | 1.722 GB | `ASSUMPTION` | A-102 | — |
| `footprint_pesos.q3` | 1.353 GB | `ASSUMPTION` | A-102 | — |
| `quantizacoes_que_cabem` | ['f16', 'q8', 'q6', 'q5', 'q4', 'q3'] | `ASSUMPTION` | A-101, A-102 | — |
| `ttft` | 9.086 s | `OBSERVATION` | — | — |
| `tokens_por_segundo` | 8.26 tok/s | `OBSERVATION` | — | — |
| `ram_de_pico` | — *(ausencia declarada)* | `OPEN_GAP` | — | G-102 |
| `capacidade.arguments` | 0.5 | `OBSERVATION` | — | — |
| `capacidade.error_recovery` | 0.3333 | `OBSERVATION` | — | — |
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
