# Modelo de Negócio e Precificação

> **Documento 3 de 3** · camada comercial
> **Base técnica:** [`01_TESE_LABORATORIO_DE_DADOS_E_EVALS.md`](01_TESE_LABORATORIO_DE_DADOS_E_EVALS.md) · [`02_ARQUITETURA_DOUVRAS_MODEL_ATLAS.md`](02_ARQUITETURA_DOUVRAS_MODEL_ATLAS.md)
> **Câmbio de referência:** US$ 1 ≈ **R$ 5,22** ([IPEA Data][3])
> **Pergunta que este documento responde:** isso paga as contas — e quanto, quando?
>
> ⚠️ Os nomes de produto abaixo (`BR-Agent-Bench`, `BR-Agent-Lab`) vêm da tese v1. O documento 2 os superseda por **DOUVRAS Model Atlas**; a estrutura comercial permanece idêntica.

---

## Sumário

1. [A premissa econômica](#1-a-premissa-econômica)
2. [A escada de receita](#2-a-escada-de-receita)
3. [Os quatro produtos](#3-os-quatro-produtos)
4. [A mudança quando você vende em dólar](#4-a-mudança-quando-você-vende-em-dólar)
5. [Venda pacote, não hora](#5-venda-pacote-não-hora)
6. [Comparação com um SaaS de R$ 99](#6-comparação-com-um-saas-de-r-99)
7. [O híbrido em três etapas](#7-o-híbrido-em-três-etapas)
8. [Cenários numéricos](#8-cenários-numéricos)
9. [O nível que muda tudo](#9-o-nível-que-muda-tudo)
10. [A primeira meta](#10-a-primeira-meta)
11. [Fontes](#fontes)

---

## 1. A premissa econômica

Pode valer **bem mais por cliente** do que um SaaS genérico. A diferença é que o SaaS costuma ter teto maior quando escala; já **datasets + evals + fine-tuning especializado** têm uma chance muito melhor de gerar caixa com poucos clientes.

### Referências de mercado

| Referência internacional (Upwork)     | Faixa                     |
| ------------------------------------- | ------------------------- |
| Engenheiros de ML                     | US$ 50–200/h              |
| PoCs                                  | US$ 1.500–4.000           |
| Desenvolvimento de modelo customizado | US$ 4.000–12.000/projeto  |
| Sistemas NLP/visão                    | US$ 6.000–18.000/projeto  |
| Deployment/MLOps                      | US$ 8.000–20.000/projeto  |

([Upwork][1])

No Brasil, dados de contratos internacionais colocam seniors gerais perto de **US$ 42/h** e especialistas fortes em ML chegando a aproximadamente **US$ 65/h**. ([Lemon.io][2])

Com o dólar em aproximadamente **R$ 5,22**, essas faixas internacionais ficam grandes rapidamente. ([IPEA Data][3])

> Mas eu **não assumiria que você consegue cobrar isso amanhã**. Você ainda teria que construir reputação especificamente em ML/evals.

---

## 2. A escada de receita

| Estágio                                        | Receita mensal plausível |
| ---------------------------------------------- | -----------------------: |
| começando / primeiros clientes                 |       **R$ 2 mil–8 mil** |
| portfólio já convincente                       |      **R$ 8 mil–20 mil** |
| especialista de nicho                          |     **R$ 20 mil–40 mil** |
| clientes internacionais                        |    **R$ 30 mil–70 mil+** |
| laboratório reconhecido / contratos enterprise |   **R$ 70 mil–150 mil+** |

Isso é **faturamento**, não salário garantido, e os últimos níveis dependem de reputação, distribuição e vendas.

O interessante é **como** você chega nesses números.

---

## 3. Os quatro produtos

### Produto 1 — AI Eval Audit

Esse seria o primeiro que eu venderia. O cliente já possui *chatbot / RAG / agente / modelo próprio*.

Você roda seu benchmark e entrega:

```text
Agent Evaluation Report

Model: XXXXX

Tool use ............... 72%
Instruction following .. 91%
Hallucination .......... 18%
Error recovery ......... 37%
JSON compliance ........ 96%
Security ............... 81%

Critical failures: 17
High failures: 38
Medium failures: 71
```

E junto: 500–2.000 casos de teste, relatório, dataset das falhas, recomendações e reprodutores.

| Momento                        | Preço                 | Objetivo                          |
| ------------------------------ | --------------------- | --------------------------------- |
| Entrada                        | **R$ 1.500–3.000**    | conseguir casos reais e depoimentos |
| Depois                         | **R$ 4.000–8.000**    | —                                 |
| Com reputação                  | **R$ 10.000–20.000+** | —                                 |

A existência de uma disciplina inteira de red teaming/evaluation de agentes torna esse tipo de trabalho bem defensável; a OWASP mantém inclusive uma iniciativa específica para avaliação e red teaming de IA. ([OWASP Gen AI Security Project][4])

---

### Produto 2 — Benchmark personalizado

Aqui começa a ficar melhor. Imagine uma empresa brasileira criando um *agente de IA para departamento financeiro*.

Você diz:

> "Eu construo um benchmark privado simulando 2.000 operações financeiras brasileiras."

Eles recebem:

```text
finance-agent-bench/

cases/
    pagamentos.jsonl
    boletos.jsonl
    pix.jsonl
    notas_fiscais.jsonl
    conciliacao.jsonl

graders/
    payment.py
    hallucination.py
    arithmetic.py

report/
    baseline.pdf
```

| Momento                  | Preço                |
| ------------------------ | -------------------- |
| Inicial                  | **R$ 4 mil–10 mil**  |
| Depois de provar qualidade | **R$ 10 mil–30 mil** |

---

### Produto 3 — Dataset personalizado

Agora fica ainda mais interessante. A empresa diz:

> "Nosso modelo erra muito quando usuário manda informação incompleta."

Você cria **`IncompleteRequestRecovery-50K`** — 50.000 exemplos especializados. Por exemplo:

```text
USER:
Faça o pagamento.

AGENT:
Preciso saber qual fornecedor e valor.

USER:
Fornecedor XPTO.

AGENT:
Qual valor deverá ser pago?
```

Mais milhares de variações.

| Escopo                                                   | Preço                 |
| -------------------------------------------------------- | --------------------- |
| Produção + validação (inicial)                            | **R$ 5 mil–15 mil**   |
| Dataset especializado, validado e com benchmark          | **R$ 15 mil–50 mil+** |

Dependendo do tamanho e da exclusividade.

---

### Produto 4 — Dataset + modelo

Aqui você começa a vender **resultado**.

| Agent Recovery | Score     |
| -------------- | --------- |
| Modelo original | 34,2%    |
| Modelo ajustado | **71,8%** |

**Entrega:** dataset · LoRA · modelo · benchmark · código · relatório

| Mercado                    | Preço                                       |
| -------------------------- | ------------------------------------------- |
| Projeto brasileiro         | **R$ 10 mil–30 mil**                        |
| Internacional (referência) | **US$ 4 mil–12 mil** ([Upwork][1])          |
| Internacional em reais     | **≈ R$ 21 mil–63 mil** ([IPEA Data][3])     |

---

## 4. A mudança quando você vende em dólar

Suponha que daqui a algum tempo seu Hugging Face tenha:

```text
dougdotcon/
    BR-Agent-Bench      3.400 downloads
    BR-Tool-Use-100K   12.800 downloads
    BR-Agent-0.8B       7.100 downloads
```

E alguns posts técnicos demonstrando:

> Qwen baseline: 42% → depois do nosso dataset: 68%

Agora aparece uma startup americana. Você não se vende como:

> ~~"Desenvolvedor brasileiro procurando freelance."~~

Você se apresenta como:

> **LLM Evaluation & Post-Training Engineer**

A conversa muda.

### 4.1 US$ 50/h já muda sua realidade

A referência inferior atual da Upwork para ML é aproximadamente **US$ 50/h** ([Upwork][1]) — com o câmbio atual, **≈ R$ 261/h**. ([IPEA Data][3])

| Horas/mês | Receita       |
| --------- | ------------- |
| 40h       | R$ 10.400/mês |
| 80h       | R$ 20.900/mês |

Você não precisa trabalhar 160 horas.

### 4.2 E US$ 100/h?

Para especialistas, US$ 100/h está dentro da faixa de mercado publicada atualmente para ML freelance ([Upwork][1]) — **≈ R$ 522/h**. ([IPEA Data][3])

| Horas/mês | Receita      |
| --------- | ------------ |
| 20h       | R$ 10.400    |
| 40h       | R$ 20.900    |
| 80h       | R$ 41.800    |

Isso começa a combinar muito mais com um trabalho de pesquisa independente.

---

## 5. Venda pacote, não hora

Preço por hora seria apenas seu **piso**. Eu venderia pacote:

| Pacote                          |     Preço | Equivalente |
| ------------------------------- | --------: | ----------- |
| Agent Evaluation                | US$ 1.500 | ≈ R$ 7.800  |
| Custom benchmark                | US$ 3.000 | ≈ R$ 15.700 |
| Dataset + fine-tuning           | US$ 5.000 | ≈ R$ 26.100 |
| Complete post-training project  | US$ 10.000 | ≈ R$ 52.200 |

Conversões usando aproximadamente R$ 5,22/US$ de hoje. ([IPEA Data][3])

E isso não está fora do planeta: os benchmarks publicados pela Upwork hoje colocam custom ML em US$ 4k–12k, NLP/CV em US$ 6k–18k e deployment/MLOps em US$ 8k–20k. ([Upwork][1])

---

## 6. Comparação com um SaaS de R$ 99

Agora você vai entender o que me atrai nesse modelo.

| | SaaS R$ 99/mês | Projeto de AI eval |
| --- | --- | --- |
| Para faturar R$ 10.000/mês | **~101 clientes pagando todo mês** | **1 cliente** |
| Custo operacional | marketing, landing page, cadastro, checkout, infra, onboarding, suporte, churn, billing, bugs, novas funcionalidades | entrega do projeto |

Você está justamente cansado da coluna da esquerda.

Um projeto internacional de **US$ 5.000** pode representar aproximadamente **R$ 26 mil** ([IPEA Data][3]) — equivalente em receita bruta a aproximadamente **264 mensalidades de R$ 99**.

**Essa é a assimetria.**

### 6.1 Mas o SaaS ganha em outra coisa

```text
SaaS                          Consultoria/data

Cliente A → R$99              Cliente A → R$15.000
Cliente B → R$99              acabou projeto
Cliente C → R$99              Cliente B → R$20.000
    ↓                         acabou projeto
recorrência
    ↓
   MRR
    ↓
 escala
```

Então eu faria um **híbrido**.

---

## 7. O híbrido em três etapas

### Etapa 1 — Serviço

Ganhar dinheiro com: `AI Eval Audit` · `Custom Benchmark` · `Dataset Engineering` · `Fine-tuning`

**Objetivo: R$ 10–20 mil/mês.**

### Etapa 2 — Contratos recorrentes

Você vende **Continuous Evaluation**, por exemplo a **R$ 2.000/mês**. Toda versão nova do modelo do cliente:

```text
v1.3
↓
executa 5.000 evals
↓
compara v1.2
↓
detecta regressões
↓
gera relatório
```

| Clientes | MRR             |
| -------- | --------------- |
| 5        | R$ 10.000       |
| 10       | R$ 20.000       |

Agora você começa a ganhar as vantagens de SaaS sem precisar vender um SaaS genérico para centenas de pessoas.

### Etapa 3 — Licensing

A parte mais interessante. Seu dataset pode ser open source:

```text
BR-Agent-Bench          → open source
BR-Agent-Bench Enterprise → 50.000 casos privados
                            financeiro · jurídico · ERP
                            contabilidade · cybersecurity
                            tool use · agent trajectories
```

A empresa paga licença — por exemplo **R$ 1.500/mês**. Dez empresas: **R$ 15.000 MRR**.

E você não está executando 10 projetos. Está vendendo **o mesmo ativo**.

### 7.1 O funil completo

```text
              BR-Agent-Lab

              OPEN SOURCE
                  │
        ┌─────────┼─────────┐
        ↓         ↓         ↓
     models    datasets   benchmark
        │         │         │
        └─────────┼─────────┘
                  ↓
               AUDIENCE
                  ↓
        ┌─────────┼─────────┐
        ↓         ↓         ↓
      audits   datasets   tuning
        │         │         │
        └─────────┼─────────┘
                  ↓
             ENTERPRISE
                  ↓
       Continuous Evaluation
                  ↓
               LICENSE
```

Isso já é uma empresa.

---

## 8. Cenários numéricos

### 8.1 Cenário Brasil — pé no chão, depois de portfólio

| Linha                                | Cálculo             | Total       |
| ------------------------------------ | ------------------- | ----------- |
| 2 AI Eval Audits                     | R$ 5.000 cada       | R$ 10.000   |
| 1 dataset/fine-tuning                | R$ 10.000           | R$ 10.000   |
| 5 clientes continuous eval           | R$ 1.500 cada       | R$ 7.500    |
| **Total**                            |                     | **R$ 27.500/mês** |

Isso não exige 200 clientes. São **8 relações comerciais**.

### 8.2 Cenário internacional

| Linha                     | Cálculo         | Total            |
| ------------------------- | --------------- | ---------------- |
| 1 custom benchmark        | US$ 3.000       | US$ 3.000        |
| 1 fine-tuning/dataset     | US$ 5.000       | US$ 5.000        |
| 3 clientes recurring      | US$ 1.000 × 3   | US$ 3.000        |
| **Total**                 |                 | **US$ 11.000/mês** |
| **Ao câmbio atual**       |                 | **≈ R$ 57 mil/mês** ([IPEA Data][3]) |

> Não estou dizendo que você vai fazer isso em seis meses. Estou mostrando que **a matemática econômica permite isso**.

---

## 9. O nível que muda tudo

Imagine que você cria o **BR-Agent-Bench** e ele se torna benchmark conhecido para modelos em português.

Uma fintech pergunta:

> "Você consegue criar uma versão privada focada em serviços financeiros?"

Agora o que ela está comprando não são suas horas. Ela está comprando:

> **um conhecimento que você acumulou durante dois anos.**

R$ 30k, R$ 50k ou mais por engagement passa a ser economicamente possível.

O mercado de AI red teaming já apresenta serviços empresariais publicamente anunciados em faixas de **milhares a dezenas de milhares de dólares** — embora essas referências sejam de empresas especializadas e não sejam comparáveis diretamente a um freelancer iniciante. ([Bluefire Red Team][5])

---

## 10. A primeira meta

Não é R$ 100.000/mês. Nem competir com a OpenAI. Sua meta inicial é:

> ## **fazer alguém pagar R$ 1.000 por algo que saiu do seu laboratório.**

Porque depois muda tudo.

```text
R$0 → R$1.000 → R$3.000 → R$5.000 → R$10.000 → US$1.000 → US$3.000 → US$5.000
```

A barreira mais difícil é **R$ 0 → R$ 1**. Depois você possui evidência de que existe mercado.

E, considerando que você está sem emprego e precisa de caixa, eu **não passaria seis meses apenas pesquisando**. Faria o BR-Agent-Bench aberto, mas já desenharia desde o primeiro mês um serviço vendável de **"auditoria independente de agentes/LLMs"**. Seu laboratório vira simultaneamente **portfólio, pesquisa, marketing e infraestrutura do serviço**.

É uma estratégia bem diferente de voltar a construir mais um CRM, chatbot ou automação para cliente — e, financeiramente, um único contrato especializado internacional já pode valer dezenas ou centenas de mensalidades de um SaaS barato. ([Upwork][1])

> 📌 Como preços de IA especializada mudam rápido, vale acompanhar vagas/projetos e faixas de contratação em LLM evals, Hugging Face e post-training para recalibrar esses números periodicamente.

---

## Fontes

1. [Best Freelance Machine Learning Engineers for Hire (Aug 2026) — Upwork](https://www.upwork.com/hire/machine-learning-experts/)
2. [Software Developer Salary in Brazil 2026: $20–$80/hr — Lemon.io](https://lemon.io/rate-calculator/brazil/)
3. [Taxa de câmbio — IPEA Data](https://www.ipeadata.gov.br/ExibeSerie.aspx?module=M&serid=38590)
4. [Red Teaming & Evaluation — OWASP Gen AI Security Project](https://genai.owasp.org/initiative/red-teaming-evaluation/)
5. [Red Team Cost 2025–2026 — Bluefire Red Team](https://bluefire-redteam.com/red-team-cost/)

<!-- definições de referência para as citações inline -->

[1]: https://www.upwork.com/hire/machine-learning-experts/ "Best Freelance Machine Learning Engineers for Hire (Aug 2026) - Upwork"
[2]: https://lemon.io/rate-calculator/brazil/ "Software Developer Salary in Brazil 2026: $20–$80/hr"
[3]: https://www.ipeadata.gov.br/ExibeSerie.aspx?module=M&serid=38590&utm_source=chatgpt.com "Taxa de câmbio"
[4]: https://genai.owasp.org/initiative/red-teaming-evaluation/?utm_source=chatgpt.com "Red Teaming & Evaluation - OWASP Gen AI Security Project"
[5]: https://bluefire-redteam.com/red-team-cost/?utm_source=chatgpt.com "Red Team Cost 2025–2026"
