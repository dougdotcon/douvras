# Arquitetura — DOUVRAS Model Atlas

> **Documento 2 de 3** · correção arquitetural (v2)
> **Status:** **superseda** [`01_TESE_LABORATORIO_DE_DADOS_E_EVALS.md`](01_TESE_LABORATORIO_DE_DADOS_E_EVALS.md) na parte de estrutura e nomenclatura.
> **Correção central:** não criar um "BR-Agent-Lab" do zero — o repositório [`ASICs`](ASICs/) já contém grande parte da infraestrutura intelectual e de engenharia necessária.
> **Pergunta que este documento responde:** onde esse laboratório de evals deve nascer?

---

## Sumário

1. [A correção](#1-a-correção)
2. [O que você já construiu](#2-o-que-você-já-construiu)
3. [A lacuna atual do ASICs é a oportunidade](#3-a-lacuna-atual-do-asics-é-a-oportunidade)
4. [Os dois eixos: capability × silicon](#4-os-dois-eixos-capability--silicon)
5. [A estrutura proposta](#5-a-estrutura-proposta)
6. [A correspondência módulo a módulo](#6-a-correspondência-módulo-a-módulo)
7. [Capability Specialization Score (CSS)](#7-capability-specialization-score-css)
8. [O ciclo DOUVRAS aplicado a capacidades](#8-o-ciclo-douvras-aplicado-a-capacidades)
9. [Hugging Face como substrato, não como objetivo](#9-hugging-face-como-substrato-não-como-objetivo)
10. [O diferencial não é o leaderboard — é o Failure Atlas](#10-o-diferencial-não-é-o-leaderboard--é-o-failure-atlas)
11. [Como isso realimenta o Silicon Atlas](#11-como-isso-realimenta-o-silicon-atlas)
12. [O dataset difícil de copiar](#12-o-dataset-difícil-de-copiar)
13. [Recomendação revisada](#13-recomendação-revisada)
14. [O primeiro experimento](#14-o-primeiro-experimento)
15. [Fontes](#fontes)

---

## 1. A correção

Sim, é possível. E eu faria uma correção importante ao que propus antes:

> **Você não precisa criar um "BR-Agent-Lab" do zero. O `ASICs` já contém grande parte da infraestrutura intelectual e de engenharia necessária.**

Depois de ler a estrutura do repositório, vejo um caminho mais interessante:

> **Transformar o DOUVRAS Silicon Atlas em uma das primeiras aplicações de uma plataforma maior: o DOUVRAS Model Atlas.**

O Silicon Atlas continuaria estudando *hardware readiness*. A nova camada estudaria *capability readiness*, datasets, evals, quantização empírica, fine-tuning e comportamento de modelos.

---

## 2. O que você já construiu

Seu repositório não é só uma ideia ou documentação. Hoje ele possui um pipeline executável com registro de modelos, IR canônica, fingerprint, profiler, análise de invariantes, quantização, readiness, partitioning, economia e emissão de assessment. O README reporta cerca de **6.900 linhas de implementação, 149 testes e um ciclo completo reproduzível**. ([GitHub][1])

Além disso, você já criou justamente a parte chata que normalmente falta em projetos independentes:

| Mecanismo               | Papel                                  |
| ----------------------- | -------------------------------------- |
| `CLAIM_LEDGER`          | controle de alegações                  |
| `GAP_REGISTER`          | registro de lacunas                    |
| `DEPENDENCY_DAG`        | dependências visíveis                  |
| status epistemológico   | classificação de maturidade da evidência |
| falsificadores          | critérios antecipados de refutação     |
| contraexemplos          | busca deliberada por refutação         |
| benchmarks              | medição comparável                     |
| experimentos            | protocolo reproduzível                 |
| revisão externa         | auditoria adversarial                  |
| baseline congelado      | referência estável                     |
| retratações             | correção pública de erro               |
| portões D0 → S6         | avanço condicionado a evidência        |

O diretório `04_VALIDATION`, por exemplo, já está separado em `BENCHMARKS`, `COUNTEREXAMPLES`, `EXPERIMENTS`, `EXTERNAL_REVIEWS` e reprodutibilidade. ([GitHub][2])

Isso é praticamente a espinha dorsal de um laboratório de evals.

E seu próprio Método DOUVRAS já define explicitamente como resultados válidos coisas como benchmark, contraexemplo, software científico reproduzível e mapa de lacunas. ([GitHub][3])

Portanto, **metodologicamente você já estava construindo a máquina de que precisaríamos.**

---

## 3. A lacuna atual do ASICs é a oportunidade

O Silicon Atlas atualmente **não executa os modelos**. O próprio README deixa isso explícito:

> não precisa de GPU, pesos, `torch` nem rede. ([GitHub][1])

Seu corpus atual contém nove descrições/configurações de modelos — Llama, Mistral, Mixtral, Phi, Gemma e Qwen — em vez de datasets de comportamento e execução real dos pesos. ([GitHub][4])

E existem lacunas que você mesmo já identificou:

- quantização é baseada em priors;
- nenhuma perplexidade foi medida;
- roofline ainda não foi calibrado contra latência real;
- qualidade sob quantização não foi empiricamente medida;
- o gate V3 permanece bloqueado;
- há dívida de evidência explícita. ([GitHub][1])

Isso, para o que estamos discutindo, é **excelente** — porque existe uma evolução natural:

| Silicon Atlas v1 (hoje)  | DOUVRAS Model Atlas (proposto) |
| ------------------------ | ------------------------------ |
| CONFIGURAÇÃO             | MODELO REAL                    |
| ↓ ARQUITETURA            | ↓ ARQUITETURA                  |
| ↓ IR                     | ↓ QUANTIZAÇÃO                  |
| ↓ FINGERPRINT            | ↓ EXECUÇÃO                     |
| ↓ CUSTO ANALÍTICO        | ↓ CAPABILITY EVALS             |
| ↓ **HARDWARE READINESS** | ↓ FAILURE ANALYSIS             |
|                          | ↓ DATASET                      |
|                          | ↓ FINE-TUNING                  |
|                          | ↓ RE-EVALUATION                |
|                          | ↓ **CAPABILITY READINESS**     |
|                          | ↓ **SILICON READINESS**        |

Agora as duas pesquisas se conectam.

---

## 4. Os dois eixos: capability × silicon

Hoje o Silicon Atlas pergunta:

> **Que parte desse modelo está madura o suficiente para virar hardware?**

Eu acrescentaria uma pergunta anterior:

> **Que capacidades desse modelo estão realmente presentes, estáveis, mensuráveis e especializáveis?**

Então surgem dois eixos:

```text
                    CAPABILITY
                       ▲
                       │
       bom modelo      │     bom modelo
       ruim hardware   │     bom hardware
                       │
───────────────────────┼──────────────► SILICON
                       │
       ruim modelo     │     eficiente,
       ruim hardware   │     mas incapaz
                       │
```

Esse gráfico conceitual é muito mais interessante que simplesmente fazer outro fine-tune no Hugging Face.

---

## 5. A estrutura proposta

Eu **não destruiria nem transformaria** o `ASICs`. Ele tem identidade própria, e seu README define a posição estratégica como uma camada que decide o que merece virar silício. ([GitHub][1])

Eu faria:

```text
DOUVRAS
│
├── douvras-core
│   ├── status
│   ├── claims
│   ├── gaps
│   ├── evidence
│   ├── provenance
│   ├── gates
│   └── reports
│
├── Silicon Atlas
│   └── ASICs
│
└── Model Atlas
    ├── models
    ├── datasets
    ├── evals
    ├── traces
    ├── experiments
    ├── adapters
    └── assessments
```

O que hoje é infraestrutura genérica no `ASICs` deveria progressivamente migrar:

```diff
- src/silicon_atlas/status.py
+ src/douvras_core/status.py
```

Seu `status.py` sozinho já tem mais de 400 linhas de implementação; portanto não faz sentido reimplementar esse contrato em outro projeto. ([GitHub][5])

E dentro do Model Atlas:

```text
Model Atlas
│
├── Architecture Atlas
├── Capability Atlas
├── Failure Atlas
├── Dataset Atlas
├── Quantization Atlas
└── Agent Atlas
```

A organização final passa a ser:

```text
                    DOUVRAS
                       │
                  DOUVRAS CORE
                       │
         ┌─────────────┴────────────┐
         │                          │
     MODEL ATLAS               SILICON ATLAS
         │                          │
  comportamento                  hardware
         │                          │
  datasets/evals                ASIC/FPGA
         │                          │
  fine-tuning                   partitioning
         │                          │
         └──────────┬───────────────┘
                    │
                 CODESIGN
```

Isso é significativamente mais ambicioso — mas também **muito mais coerente com o que você já construiu**.

---

## 6. A correspondência módulo a módulo

A correspondência é quase 1:1.

| Silicon Atlas     | Model Atlas                  | O que produz                        |
| ----------------- | ---------------------------- | ----------------------------------- |
| `registry.py`     | `model_registry.py`          | especificação de modelos reais do Hub |
| `fingerprint.py`  | `capability_fingerprint.py`  | vetor de capacidades medidas        |
| `profiler.py`     | `inference_profiler.py`      | custo real de execução              |
| `quantization.py` | `quantization.py` (empírico) | precision cliff medido, não prior   |

### 6.1 `model_registry.py`

```python
HFModelSpec(
    repo="...",
    revision="...",
    params=...,
    architecture=...,
    quantization=...,
    license=...,
    provenance=...
)
```

### 6.2 `capability_fingerprint.py`

```json
{
  "tool_calling": 0.71,
  "json": 0.92,
  "planning": 0.43,
  "recovery": 0.31,
  "pt_br": 0.84,
  "instruction_following": 0.77
}
```

### 6.3 `inference_profiler.py`

Medindo: TTFT, tokens/s, RAM, CPU, latência, prompt tokens, generation tokens, context size.

E isso pode finalmente começar a fechar algumas das lacunas empíricas que o Silicon Atlas hoje declara. ([GitHub][1])

### 6.4 `quantization.py` — de prior a medição

Deixaria de trabalhar apenas com prior. Você poderia realmente executar `FP16 · Q8 · Q6 · Q5 · Q4 · Q3` e medir qualidade, RAM, latência, tokens/s e capability score.

Então surge algo extremamente interessante:

| Precisão | Score    |
| -------- | -------- |
| Q8       | 74,1     |
| Q6       | 74,0     |
| Q5       | 73,8     |
| Q4       | 71,2     |
| Q3       | **54,3** |

E você descobre empiricamente um **precision cliff**. Isso interessa tanto para modelos quanto para seu projeto de hardware.

---

## 7. Capability Specialization Score (CSS)

Seu Silicon Atlas já possui o conceito de `Layer Hardening Score`. Eu criaria o irmão dele:

> **CSS — Capability Specialization Score**
> Essa capacidade é boa candidata para especialização através de dados/fine-tuning?

Por exemplo, para um `Qwen-small`:

| Capability     | Score    |
| -------------- | -------- |
| JSON           | 0.95     |
| Tool selection | 0.83     |
| PT-BR          | 0.79     |
| Error recovery | **0.34** |
| Planning       | **0.29** |
| Long horizon   | **0.18** |

O sistema identifica:

```text
TARGET = error_recovery
```

Depois você cria dataset específico.

---

## 8. O ciclo DOUVRAS aplicado a capacidades

A coisa mais DOUVRAS possível seria **não treinar primeiro**. Seu método praticamente já exige isso:

| Fase | Aplicação a capacidades              |
| ---- | ------------------------------------ |
| D    | delimitar capacidade                 |
| O    | observar comportamento dos modelos   |
| U    | encontrar padrões de falha           |
| V    | tentar refutar o diagnóstico         |
| R    | encontrar habilidade mínima ausente  |
| A    | criar dataset/fine-tuning            |
| S    | medir continuamente                  |

Isso encaixa absurdamente bem no que você já construiu. O próprio documento do método separa explicitamente ciclo científico e ciclo de engenharia e exige que produto vendável não seja confundido com validação científica. ([GitHub][3])

---

## 9. Hugging Face como substrato, não como objetivo

Eu faria o Hugging Face ser o **substrato experimental do Model Atlas**:

```text
Hugging Face Hub
     │
     ▼
Model Registry
     │
     ▼
DOUVRAS Model Atlas
     │
 ┌───┼───────────┐
 ▼   ▼           ▼
eval dataset   traces
 │   │           │
 └───┼───────────┘
     ▼
Capability Fingerprint
     │
     ▼
Failure Atlas
     │
     ▼
Training Dataset
     │
     ▼
LoRA / PEFT
     │
     ▼
Re-evaluation
```

O Hugging Face tem o **LightEval**, criado especificamente para avaliação de LLMs com resultados por amostra, e suporta criação de tarefas customizadas. ([Hugging Face][6]) Portanto você não precisa reinventar o executor inteiro — você cria a camada científica por cima dele.

### 9.1 Uma task registrada

```yaml
id: DOUVRAS-BR-TOOL-001

capability:
  tool_selection

difficulty:
  2

language:
  pt-BR

expected:
  tool: consultar_estoque

failure_modes:
  - hallucinated_tool
  - wrong_tool
  - premature_answer

status:
  EXPERIMENTAL_EVIDENCE
```

E aí roda contra Tucano, Qwen, SmolLM, Gemma, Llama, Mistral, etc.

| Modelo       | Tool selection |
| ------------ | -------------: |
| Qwen-small   |            82% |
| Gemma-small  |            77% |
| Tucano-small |            73% |
| SmolLM       |            68% |

---

## 10. O diferencial não é o leaderboard — é o Failure Atlas

Leaderboard já existe aos montes. O interessante é o **Failure Atlas**:

```text
MODEL
Qwen-X

FAILURES
│
├── TOOL
│   ├── selection          7.2%
│   ├── arguments         11.8%
│   └── hallucination      2.1%
│
├── PLANNING
│   ├── ordering          18.4%
│   ├── premature_stop    14.3%
│   └── loop               4.1%
│
└── RECOVERY
    ├── timeout           42.1%
    ├── malformed_json    31.0%
    └── unexpected_data   28.7%
```

Isso começa a ser **dados sobre os modelos**, não apenas datasets para eles.

---

## 11. Como isso realimenta o Silicon Atlas

Imagine, depois de centenas de modelos:

| Dimensão        | Observação                     |
| --------------- | ------------------------------ |
| tool selection  | alta estabilidade entre modelos |
| planning        | alta variabilidade             |
| recovery        | alta variabilidade             |
| matmul          | alta estabilidade arquitetural |
| MLP             | alta estabilidade arquitetural |

Você passa a possuir dois tipos de invariantes: **behavioral invariants + architectural invariants**.

A interseção:

```text
behavioral
     ∩
architectural
     ∩
cost dominant
     ∩
quantization tolerant
```

pode ser exatamente:

> **o que realmente merece ser especializado.**

Isso torna seu ASICs mais forte também.

### 11.1 A descoberta escondida no seu resultado atual

Seu Silicon Atlas encontrou:

> nenhuma região fixa suficientemente justificável com as evidências atuais. ([GitHub][1])

Isso não significa *"ASICs são inúteis"*. Significa:

> **a granularidade usada para procurar invariantes pode ainda ser grande demais.**

Você procurou em `architecture → layers → operators`. Agora pode começar a investigar:

```text
model
→ behavior
→ execution trace
→ operator trace
→ architectural structure
```

Muito mais informação.

---

## 12. O dataset difícil de copiar

Suponha que cem tarefas de tool calling produzam constantemente:

```text
tool selection → structured arguments → decode
```

Você pode correlacionar:

```text
capability × architecture × quantization × latency × memory × failure rate
```

Isso vira um dataset do tipo `DOUVRAS/ModelAtlas`, com milhões de observações. Não necessariamente milhões de textos, mas:

```text
modelo · configuração · quantização · hardware · task · prompt
trajectory · output · score · failure · latency · memory · tokens
```

Esse é um dataset **muito mais difícil de copiar**.

### 12.1 E sua máquina consegue gerar grande parte dele

Isso é especialmente adequado ao seu cenário porque muito do trabalho é:

```text
gerar tasks
validar schemas
executar testes
registrar resultados
analisar erros
criar datasets
rodar modelos pequenos quantizados
```

e não treinamento de bilhões de parâmetros.

Quando precisar de treinamento:

```text
dataset local → Hugging Face → GPU eventualmente → LoRA → adapter
```

PEFT/LoRA existe justamente para adaptar modelos treinando apenas uma fração adicional dos parâmetros, reduzindo drasticamente o custo comparado ao fine-tuning integral ([Hugging Face][7]), e seus datasets podem ser publicados diretamente no Hub via `push_to_hub`, em formato reutilizável/versionado. ([Hugging Face][8])

---

## 13. Recomendação revisada

Antes eu te disse:

> ~~faça o BR-Agent-Bench.~~

Depois de ver o ASICs: **não.**

Eu faria o **DOUVRAS Model Atlas**, e manteria o **Silicon Atlas** como outra aplicação sobre o mesmo core.

---

## 14. O primeiro experimento

Eu não mexeria em LoRA ainda. Pegaria **dois modelos pequenos que rodem na sua máquina**, criaria apenas **50–100 evals**, integraria LightEval e faria o Model Atlas emitir seu primeiro:

```text
MODEL CAPABILITY ASSESSMENT
```

igual ao seu `SILICON READINESS ASSESSMENT`, só que contendo:

```text
architecture
quantization
RAM
latency
capabilities
failure modes
evidence status
gaps
counterexamples
dataset opportunities
specialization targets
```

Quando isso existir, você terá conectado **ASICs + Hugging Face + datasets + evals + modelos pequenos + fine-tuning** em uma única linha de pesquisa.

E essa direção é bem mais interessante do que abandonar o `ASICs` e começar mais um projeto isolado.

---

## Fontes

1. [dougdotcon/ASICs — GitHub](https://github.com/dougdotcon/ASICs.git)
2. [ASICs/04_VALIDATION — GitHub](https://github.com/dougdotcon/ASICs/tree/master/04_VALIDATION)
3. [ASICs/METODO_DOUVRAS_E_SILICON_ATLAS.md — GitHub](https://github.com/dougdotcon/ASICs/blob/master/METODO_DOUVRAS_E_SILICON_ATLAS.md)
4. [ASICs/corpus/models — GitHub](https://github.com/dougdotcon/ASICs/tree/master/corpus/models)
5. [ASICs/src/silicon_atlas/status.py — GitHub](https://github.com/dougdotcon/ASICs/blob/master/src/silicon_atlas/status.py)
6. [Lighteval — Hugging Face](https://huggingface.co/docs/lighteval/en/index)
7. [LoRA — Hugging Face](https://huggingface.co/docs/peft/package_reference/lora)
8. [Share a dataset to the Hub — Hugging Face](https://huggingface.co/docs/datasets/upload_dataset)

<!-- definições de referência para as citações inline -->

[1]: https://github.com/dougdotcon/ASICs.git "GitHub - dougdotcon/ASICs: Descobre quais partes de um modelo de IA já estão estáveis, dominantes em custo e tolerantes a baixa precisão o suficiente para virar silício — e a partir de qual volume isso se paga."
[2]: https://github.com/dougdotcon/ASICs/tree/master/04_VALIDATION "ASICs/04_VALIDATION at master · dougdotcon/ASICs · GitHub"
[3]: https://github.com/dougdotcon/ASICs/blob/master/METODO_DOUVRAS_E_SILICON_ATLAS.md "ASICs/METODO_DOUVRAS_E_SILICON_ATLAS.md at master · dougdotcon/ASICs · GitHub"
[4]: https://github.com/dougdotcon/ASICs/tree/master/corpus/models "ASICs/corpus/models at master · dougdotcon/ASICs · GitHub"
[5]: https://github.com/dougdotcon/ASICs/blob/master/src/silicon_atlas/status.py "ASICs/src/silicon_atlas/status.py at master · dougdotcon/ASICs · GitHub"
[6]: https://huggingface.co/docs/lighteval/en/index?utm_source=chatgpt.com "Lighteval"
[7]: https://huggingface.co/docs/peft/package_reference/lora?utm_source=chatgpt.com "LoRA · Hugging Face"
[8]: https://huggingface.co/docs/datasets/upload_dataset?utm_source=chatgpt.com "Share a dataset to the Hub"
