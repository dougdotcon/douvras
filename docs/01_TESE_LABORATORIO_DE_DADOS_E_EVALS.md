# Tese — Laboratório de Dados, Evals e Modelos Pequenos

> **Documento 1 de 3** · tese inicial (v1)
> **Status:** parcialmente **superseda** por [`02_ARQUITETURA_DOUVRAS_MODEL_ATLAS.md`](02_ARQUITETURA_DOUVRAS_MODEL_ATLAS.md) na parte de estrutura e nomenclatura. A direção de pesquisa, o método benchmark-first e o plano de 30 dias continuam válidos.
> **Monetização:** detalhada em [`03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md`](03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md).
> **Pergunta que este documento responde:** dá para fazer pesquisa de IA relevante com CPU e 16 GB de RAM?

---

## Sumário

1. [A premissa: redefinir "competir com OpenAI/Anthropic"](#1-a-premissa-redefinir-competir-com-openaianthropic)
2. [A empresa: Data + Evals + Small Models](#2-a-empresa-data--evals--small-models)
3. [O produto científico: BR-Agent-Bench](#3-o-produto-científico-br-agent-bench)
4. [Viabilidade no hardware disponível](#4-viabilidade-no-hardware-disponível)
5. [Modelos-base de partida](#5-modelos-base-de-partida)
6. [Datasets como ativo](#6-datasets-como-ativo)
7. [A assimetria: por que a vantagem é sua](#7-a-assimetria-por-que-a-vantagem-é-sua)
8. [Infraestrutura: Hugging Face](#8-infraestrutura-hugging-face)
9. [A ordem correta de trabalho](#9-a-ordem-correta-de-trabalho)
10. [Como isso vira dinheiro](#10-como-isso-vira-dinheiro)
11. [Quarta direção: modelos ultrapequenos](#11-quarta-direção-modelos-ultrapequenos)
12. [Alocação de esforço](#12-alocação-de-esforço)
13. [Primeiros 30 dias](#13-primeiros-30-dias)
14. [Cadência de versões](#14-cadência-de-versões)
15. [Conclusão: qual é o gargalo real](#15-conclusão-qual-é-o-gargalo-real)
16. [Fontes](#fontes)

---

## 1. A premissa: redefinir "competir com OpenAI/Anthropic"

Sim, é possível. Mas eu mudaria a definição de **"competir com OpenAI/Anthropic"**.

Com um 3200G-class, 16 GB de RAM e sem GPU dedicada, você não vai competir treinando um foundation model de bilhões de parâmetros do zero. A vantagem é que **você não precisa competir nessa camada**.

Hoje OpenAI e Anthropic estão avançando fortemente em agentes, tool use, execução de código, tarefas longas e integração com sistemas. ([OpenAI][1]) Ao mesmo tempo, a própria Anthropic está enfatizando que **avaliação de agentes** — testes objetivos, graders, verificação de tool calls, outcome verification etc. — virou parte crítica dessa infraestrutura. ([Anthropic][2])

E existe uma oportunidade particularmente interessante no Brasil.

---

## 2. A empresa: Data + Evals + Small Models

Algo provisoriamente chamado **BR Agent Lab**.

> ⚠️ **Nomenclatura superseda.** O documento 2 argumenta que esse laboratório não deve nascer do zero, e sim como **DOUVRAS Model Atlas**, reaproveitando a infraestrutura do repositório `ASICs`. Leia esta seção como a *forma* do laboratório, não como o nome final.

Não seria inicialmente um chatbot. Seria um laboratório Hugging Face composto por uma cadeia:

```text
BR-Agent-Data → BR-Agent-Bench → BR-Agent-0.8B → BR-Agent-Space
```

### 2.1 A janela aberta pelo Tucano 2

Em março de 2026 saiu o **Tucano 2**, uma família aberta focada em português. O projeto publicou modelos de aproximadamente 0,5B a 3,7B parâmetros, datasets, benchmarks, código de treinamento e receitas. ([Hugging Face][3])

Mais importante: os próprios autores apontaram como próximos problemas em aberto:

- melhores dados sintéticos;
- preference datasets maiores;
- contextos maiores;
- **agentic capabilities**;
- tool use;
- planejamento multi-step;
- interação dinâmica. ([Hugging Face][3])

Ou seja:

> **eles praticamente deixaram uma placa escrita "há pesquisa para fazer aqui".**

Isso é muito mais interessante do que produzir o 9.382º fine-tune genérico de Llama.

---

## 3. O produto científico: BR-Agent-Bench

Um benchmark aberto para medir:

> **"Quão bom é um modelo pequeno operando como agente em português brasileiro?"**

Esse é o produto científico. A sequência derivada é:

```text
benchmark → datasets que melhoram o benchmark → modelos treinados nesses datasets
                                                        ↓
                          empresas pagam para testar ou melhorar os modelos delas
```

### 3.1 Anatomia de uma tarefa

Não faça coisas do tipo *"Qual é a capital da França?"*. Crie situações reais:

```text
Usuário:
Tenho R$ 3.482,91 disponíveis.

Preciso pagar:
Fornecedor A: R$ 987,32
Fornecedor B: R$ 1.287,90
Fornecedor C: R$ 1.498,50

Ferramentas disponíveis:
consultar_saldo()
pagar_boleto(valor, fornecedor)
solicitar_aprovacao(valor)

Objetivo:
Pague o máximo possível sem deixar o saldo negativo.
```

O benchmark verifica:

- ✓ chamou a ferramenta correta
- ✓ usou valor correto
- ✓ não inventou saldo
- ✓ não gastou mais do que disponível
- ✓ identificou pagamento impossível
- ✓ não executou ferramenta desnecessária

Isso é muito mais valioso para agentes do que simplesmente medir se o português do modelo parece bonito. A Anthropic descreve exatamente esse tipo de avaliação: verificação de tool calls, parâmetros, resultados, testes binários e análise de trajetória. ([Anthropic][2])

### 3.2 Famílias de tarefas

E você poderia criar milhares dessas situações:

| Família               | Exemplo                               |
| --------------------- | ------------------------------------- |
| Tool calling          | escolher ferramenta correta           |
| Structured output     | JSON válido                           |
| Planejamento          | executar operações em ordem           |
| Recuperação de erro   | API retorna 500                       |
| Ambiguidade           | usuário fornece informação incompleta |
| Segurança             | recusar ação indevida                 |
| Matemática brasileira | R$, vírgula decimal, porcentagem      |
| Datas                 | formato DD/MM/AAAA                    |
| Documentos            | extrair campos                        |
| Atendimento           | decidir encaminhamento                |
| ERP                   | pedido/estoque/faturamento            |
| Financeiro            | conciliação                           |
| SQL                   | gerar consulta                        |
| Suporte de TI         | diagnosticar incidente                |
| Long horizon          | 5–20 ações consecutivas               |
| Hallucination         | não inventar resultado de ferramenta  |

E você não precisa de GPU para construir boa parte disso.

---

## 4. Viabilidade no hardware disponível

Com **16 GB de RAM e sem GPU dedicada**, eu dividiria assim:

| Atividade                         |                 Seu PC |
| --------------------------------- | ---------------------: |
| Criar datasets                    |           🟢 excelente |
| Limpar datasets                   |           🟢 excelente |
| Deduplicação                      |                     🟢 |
| Gerar variações programaticamente |                     🟢 |
| Criar benchmark                   |           🟢 excelente |
| Rodar testes determinísticos      |           🟢 excelente |
| Construir graders                 |                     🟢 |
| Embeddings pequenos               |                     🟢 |
| Inferência 0,5–0,8B               |                     🟢 |
| Inferência 1–3B quantizado        |                     🟡 |
| LoRA ~0,5B CPU                    | 🟡 possível, mas lento |
| Fine-tune 3B CPU                  |    🔴 não recomendaria |
| Treinar 3B do zero                |                     🔴 |
| Treinar 7B+                       |                   🔴🔴 |
| GPT concorrente do zero           |                     ☠️ |

O `llama.cpp` existe justamente para executar modelos localmente em CPU/GPU, e o Hugging Face suporta diretamente modelos GGUF e agentes locais usando llama.cpp. ([GitHub][4]) Quantização reduz memória e custo computacional representando os pesos em precisões menores, inclusive 4-bit. ([Hugging Face][5])

---

## 5. Modelos-base de partida

### 5.1 Modelo A — Tucano2 0.5B

Existe atualmente **`Polygl0t/Tucano2-qwen-0.5B-Base`**, com versões **Instruct** e **Think**. ([Hugging Face][6])

Ele é extremamente interessante porque o projeto é explicitamente voltado ao português.

Você não começaria treinando um modelo. Começaria perguntando:

> **Onde o Tucano 2 0.5B quebra como agente?**

Isso gera pesquisa.

### 5.2 Modelo B — Qwen3.5-0.8B

O Qwen disponibiliza um modelo de apenas **0,8B**, explicitamente apontado para prototipagem, fine-tuning específico de tarefa e pesquisa. ([Hugging Face][7]) Esse seria seu segundo baseline.

O resultado tem esta forma:

| BR-Agent-Bench v0.1 | Score |
| ------------------- | ----: |
| Tucano2 0.5B        | 31,7% |
| Qwen3.5 0.8B        | 44,3% |
| SmolLM3 3B          | 61,8% |
| modelo X            |   ... |
| modelo Y            |   ... |
| GPT/Claude          |   ... |

> Os números acima são **apenas ilustração da estrutura** — você produziria os resultados reais.

### 5.3 Do baseline ao problema mensurável

Imagine que você descobre:

| Qwen3.5-0.8B     | Score |
| ---------------- | ----: |
| tool selection   |   81% |
| JSON validity    |   92% |
| Portuguese       |   84% |
| multi-step       |   31% |
| error recovery   |   27% |
| financial tasks  |   39% |

Agora você possui **um problema mensurável**.

Em vez de dizer *"vou fazer fine-tuning"*, você diz:

> "vou aumentar error recovery de 27% para 60%."

Essa diferença é gigantesca. É assim que você transforma brincadeira com LLM em pesquisa.

---

## 6. Datasets como ativo

### 6.1 BR-Agent-Recovery-10k

10.000 trajetórias contendo:

```json
{
  "instruction": "...",
  "tools": [...],
  "trajectory": [...],
  "expected_outcome": "...",
  "failure_type": "tool_timeout",
  "difficulty": 3
}
```

Com erros artificiais injetados:

| Classe          | Casos                                     |
| --------------- | ----------------------------------------- |
| Rede/timeout    | `timeout`                                 |
| HTTP            | `401`, `403`, `404`, `429`, `500`         |
| Formato         | JSON malformado                           |
| Conteúdo        | retorno vazio, contraditório ou parcial   |

E ensina o modelo a:

```text
detectar
→ interpretar
→ corrigir
→ tentar novamente
→ abandonar se necessário
```

Isso começa a virar propriedade intelectual interessante.

### 6.2 Dados de trajetória — a possibilidade ainda melhor

As empresas estão deixando de treinar apenas `pergunta → resposta` e trabalhando cada vez mais com agentes capazes de interagir com ambientes.

Você poderia criar:

```text
problema
→ pensamento operacional
→ tool call
→ observação
→ decisão
→ tool call
→ observação
→ resultado
```

O Hugging Face já documenta inclusive formato de **Session Traces** e ecossistema de agentes. ([Hugging Face][8])

Seu ativo deixa de ser apenas texto. Passa a ser:

> **experiência simulada de agentes.**

### 6.3 BR-Computer-Agent-100k

100 mil tarefas sintéticas simulando operações de computador.

**Objetivo:**

```text
Localize o relatório de maio
extraia o total faturado
adicione o valor à planilha financeira.
```

**Ambiente:** `list_files()`, `read_file()`, `write_sheet()`, `search()`

**Trajetória correta:**

```text
list_files("/relatorios")
→ maio.pdf

read_file("maio.pdf")
→ faturamento: R$ 17.839,92

write_sheet(cell="C17", value=17839.92)
```

E você cria automaticamente variantes.

---

## 7. A assimetria: por que a vantagem é sua

Você falou que cansou de desenvolver software. Curiosamente, isso ajuda — porque agora **o software é apenas instrumento do experimento**, não o produto.

Você escreve 200 linhas para criar:

```text
10.000 ambientes
100.000 problemas
100.000 testes
50.000 trajetórias
```

E descarta o código depois, se quiser. O produto é **DATA**.

OpenAI pode gastar bilhões em compute. Você não. Mas um engenheiro sozinho pode descobrir:

> "Modelos atuais não conseguem fazer X."

E construir:

> "Aqui estão 20.000 exemplos que ensinam X."

E provar:

```text
antes: 34%
depois: 71%
```

Essa pequena tabela vale mais do que um SaaS genérico.

---

## 8. Infraestrutura: Hugging Face

### 8.1 Layout do laboratório

```text
huggingface.co/SEU_LAB
│
├── datasets
│   ├── BR-Agent-Bench
│   ├── BR-ToolCalling
│   ├── BR-Agent-Recovery
│   └── BR-Agent-Trajectories
│
├── models
│   ├── BR-Agent-0.5B
│   ├── BR-Agent-0.8B
│   └── adapters
│
└── spaces
    └── BR-Agent-Leaderboard
```

Hugging Face Datasets foi feito justamente para criação, processamento e compartilhamento desses conjuntos ([Hugging Face][9]), e um Gradio Space vira automaticamente uma API acessível externamente. ([Hugging Face][10])

### 8.2 Compute gratuito: o que dá e o que não dá

O Hugging Face possui **ZeroGPU**. Hoje ele disponibiliza infraestrutura compartilhada baseada em RTX Pro 6000 Blackwell; usuários podem utilizá-lo gratuitamente. Contas pessoais gratuitas em bom estado, verificadas e com mais de 30 dias podem atualmente hospedar até **2 ZeroGPU Spaces**. ([Hugging Face][11])

| Uso                                              | Veredito                        |
| ------------------------------------------------ | ------------------------------- |
| demos, avaliação, inferência, experimentos, Spaces | 🟢 arma interessante            |
| cluster gratuito de treinamento infinito          | 🔴 não trate assim              |
| pipeline de geração massiva via Inference Providers | 🔴 crédito Free é **US$ 0,10/mês** ([Hugging Face][12]) |

### 8.3 Stack de fine-tuning

O Hugging Face já tem exatamente a stack necessária:

| Ferramenta | Função                                                       |
| ---------- | ------------------------------------------------------------ |
| **PEFT**   | treinar apenas uma fração dos parâmetros ([Hugging Face][13]) |
| **LoRA**   | representar adaptações com matrizes menores ([Hugging Face][14]) |
| **TRL**    | SFT e outras formas de post-training ([Hugging Face][15])     |

A documentação atual do `SFTTrainer` usa inclusive **Qwen3-0.6B** como exemplo de treinamento compacto. ([Hugging Face][16])

Você poderia eventualmente fazer:

```text
BASE            Qwen3.5-0.8B
  + LoRA
  + BR-Agent-Recovery-10K
  = douglas/BR-Agent-Recovery-0.8B
```

---

## 9. A ordem correta de trabalho

Essa é a principal coisa que eu mudaria na sua estratégia.

**Não faça:**

```text
modelo → fine tune → testa → talvez seja bom
```

**Faça:**

```text
PROBLEMA
↓
BENCHMARK
↓
BASELINE
↓
FAILURE ANALYSIS
↓
DATASET
↓
TRAINING
↓
BENCHMARK
↓
ABLAÇÃO
↓
PUBLICAÇÃO
```

Isso é muito mais próximo de laboratório de IA.

---

## 10. Como isso vira dinheiro

Downloads no Hugging Face, sozinhos, provavelmente não vão pagar suas contas. O open source funciona como **distribuição**.

> 💰 Precificação, escada de receita e modelo híbrido estão detalhados em [`03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md`](03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md). Abaixo, só a estrutura das fontes de receita.

### Camada aberta

```text
BR-Agent-Bench
BR-Agent-1K
leaderboard
modelo básico
paper
Space
```

### Fonte 1 — Enterprise Eval

A empresa manda o agente dela. Você entrega:

```text
Tool-use score          82%
Hallucination           17%
Error recovery          39%
Structured output       94%
Brazilian Portuguese    88%
Security                73%

127 falhas identificadas
38 falhas críticas
dataset recomendado
```

Isso já é um serviço.

### Fonte 2 — Custom post-training

Uma empresa diz: *"temos um agente para contabilidade."*

Você cria `Accounting-Agent-Bench` + dataset privado + LoRA + eval, e cobra. Não precisa hospedar SaaS nenhum. Você entrega:

```text
adapter.safetensors
dataset
benchmark
report
```

### Fonte 3 — Datasets privados

| Entregável             | Exemplo de preço |
| ---------------------- | ---------------- |
| 50.000 exemplos        | R$ 8.000         |
| 100.000 exemplos       | R$ 15.000        |
| benchmark customizado  | R$ 5.000         |
| fine-tuning            | R$ 5.000         |

> Esses valores são apenas exemplos de modelo comercial, **não** uma cotação de mercado.

A sacada é que você passa a vender **capacidade de uma IA** em vez de vender horas desenvolvendo CRUD.

---

## 11. Quarta direção: modelos ultrapequenos

Existe uma corrida interessante em modelos menores:

- **SmolLM3** — modelo totalmente aberto de 3B, com reasoning, português e contexto longo. ([Hugging Face][17])
- **Qwen3.5-0.8B** — ainda menor. ([Hugging Face][7])
- **Tucano2** — versões em torno de 0,5B. ([Hugging Face][6])

Isso permite perguntar algo cientificamente interessante:

> **Quanto podemos especializar um modelo de 500M–800M até ele derrotar um modelo muito maior em UMA tarefa?**

Aí você consegue competir. Não:

> ~~BR-Agent é melhor que GPT-5.6.~~

Mas:

> BR-Agent-0.8B supera modelos generalistas muito maiores em classificação e execução do workflow X.

**Esse tipo de vitória é possível.**

---

## 12. Alocação de esforço

| Frente                          | Esforço |
| ------------------------------- | ------: |
| Datasets                        | **50%** |
| Benchmarks/evals                | **25%** |
| Treinamento de modelos pequenos | **15%** |
| Spaces/publicação/divulgação    | **10%** |
| Treinar foundation model do zero | **~0%** |

---

## 13. Primeiros 30 dias

### Semana 1 — Benchmark mínimo

Criar `BR-Agent-Bench` com apenas **100 problemas**:

| Categoria         | Problemas |
| ----------------- | --------: |
| tool selection    |        20 |
| structured output |        20 |
| error recovery    |        20 |
| planning          |        20 |
| Brazilian-context |        20 |

Rodar em `Tucano2-0.5B` e `Qwen3.5-0.8B`.

### Semana 2 — Taxonomia de falhas

Analisar todos os erros e criar a taxonomia:

```text
FAIL_TOOL_SELECTION
FAIL_ARGUMENT
FAIL_FORMAT
FAIL_PLANNING
FAIL_RECOVERY
FAIL_HALLUCINATION
```

Isso já pode gerar um relatório interessante.

### Semana 3 — Dataset dirigido

Criar `BR-Agent-Data-10K`, direcionado para o **pior failure mode encontrado**.

### Semana 4 — Primeiro adapter

Treinar o primeiro adapter e rodar novamente:

```text
BASE     31%
TUNED    54%
```

Se aparecer uma diferença grande e reproduzível: **você encontrou algo. Publique.**

---

## 14. Cadência de versões

| Versão   | Evals | Exemplos de treino |
| -------- | ----: | ------------------ |
| **v0.1** |   100 | 10k                |
| **v0.2** |   500 | 50k                |
| **v0.3** |    1k | 100k               |
| **v1.0** |    5k | 1M trajectories    |

---

## 15. Conclusão: qual é o gargalo real

Você não precisa comprar uma RTX 5090 para começar isso. Seu gargalo inicial não é FLOPS. Seu gargalo é:

> **inventar uma avaliação que revele uma deficiência importante dos modelos existentes.**

E isso é justamente uma das poucas partes da cadeia de IA em que **um pesquisador indie com um computador fraco ainda consegue produzir algo realmente novo**.

Se eu estivesse no seu lugar, começaria **hoje pelo BR-Agent-Bench**, usando **Tucano2-0.5B + Qwen3.5-0.8B**, e só compraria hardware quando o benchmark demonstrasse uma necessidade concreta. O próprio Tucano 2 praticamente entrega a direção de pesquisa: preferência, dados sintéticos, tool use e agentic capabilities ainda são áreas abertas para expansão em português. ([Hugging Face][3])

---

## Fontes

1. [The next evolution of the Agents SDK — OpenAI](https://openai.com/index/the-next-evolution-of-the-agents-sdk/)
2. [Demystifying evals for AI agents — Anthropic](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
3. [Building Tucano 2: Open-Source Language Models That Actually *Think* in Portuguese — Hugging Face](https://huggingface.co/blog/Polygl0t/tucano2)
4. [ggml-org/llama.cpp: LLM inference in C/C++ — GitHub](https://github.com/ggml-org/llama.cpp)
5. [Quantization — Hugging Face](https://huggingface.co/docs/transformers/main_classes/quantization)
6. [Tucano2 — a Polygl0t Collection](https://huggingface.co/collections/Polygl0t/tucano2)
7. [Qwen/Qwen3.5-0.8B — Hugging Face](https://huggingface.co/Qwen/Qwen3.5-0.8B)
8. [Local Agents with llama.cpp — Hugging Face](https://huggingface.co/docs/hub/agents-local)
9. [Create a dataset — Hugging Face](https://huggingface.co/docs/datasets/create_dataset)
10. [Spaces as API endpoints — Hugging Face](https://huggingface.co/docs/hub/spaces-api-endpoints)
11. [Spaces ZeroGPU: Dynamic GPU Allocation for Spaces — Hugging Face](https://huggingface.co/docs/hub/spaces-zerogpu)
12. [Pricing and Billing — Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/pricing)
13. [PEFT — Hugging Face](https://huggingface.co/docs/peft/index)
14. [LoRA — Hugging Face](https://huggingface.co/docs/peft/package_reference/lora)
15. [TRL — Transformers Reinforcement Learning](https://huggingface.co/docs/trl/index)
16. [SFT Trainer — Hugging Face](https://huggingface.co/docs/trl/sft_trainer)
17. [HuggingFaceTB/SmolLM3-3B — Hugging Face](https://huggingface.co/HuggingFaceTB/SmolLM3-3B)

<!-- definições de referência para as citações inline -->

[1]: https://openai.com/index/the-next-evolution-of-the-agents-sdk/?utm_source=chatgpt.com "The next evolution of the Agents SDK"
[2]: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents "Demystifying evals for AI agents \ Anthropic"
[3]: https://huggingface.co/blog/Polygl0t/tucano2 "Building Tucano 2: Open-Source Language Models That Actually _Think_ in Portuguese"
[4]: https://github.com/ggml-org/llama.cpp?utm_source=chatgpt.com "ggml-org/llama.cpp: LLM inference in C/C++"
[5]: https://huggingface.co/docs/transformers/main_classes/quantization?utm_source=chatgpt.com "Quantization"
[6]: https://huggingface.co/collections/Polygl0t/tucano2?utm_source=chatgpt.com "Tucano2 - a Polygl0t Collection"
[7]: https://huggingface.co/Qwen/Qwen3.5-0.8B?utm_source=chatgpt.com "Qwen/Qwen3.5-0.8B"
[8]: https://huggingface.co/docs/hub/agents-local "Local Agents with llama.cpp · Hugging Face"
[9]: https://huggingface.co/docs/datasets/create_dataset?utm_source=chatgpt.com "Create a dataset"
[10]: https://huggingface.co/docs/hub/spaces-api-endpoints?utm_source=chatgpt.com "Spaces as API endpoints"
[11]: https://huggingface.co/docs/hub/spaces-zerogpu "Spaces ZeroGPU: Dynamic GPU Allocation for Spaces · Hugging Face"
[12]: https://huggingface.co/docs/inference-providers/pricing?utm_source=chatgpt.com "Pricing and Billing"
[13]: https://huggingface.co/docs/peft/index?utm_source=chatgpt.com "PEFT"
[14]: https://huggingface.co/docs/peft/package_reference/lora?utm_source=chatgpt.com "LoRA · Hugging Face"
[15]: https://huggingface.co/docs/trl/index?utm_source=chatgpt.com "TRL - Transformers Reinforcement Learning"
[16]: https://huggingface.co/docs/trl/sft_trainer?utm_source=chatgpt.com "SFT Trainer"
[17]: https://huggingface.co/HuggingFaceTB/SmolLM3-3B "HuggingFaceTB/SmolLM3-3B · Hugging Face"
