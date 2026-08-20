# Produto 1 — AI Eval Audit

> **Documento 4 de 4** · piloto comercial
> **Base técnica:** [`02_ARQUITETURA_DOUVRAS_MODEL_ATLAS.md`](02_ARQUITETURA_DOUVRAS_MODEL_ATLAS.md) · [`03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md`](03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md)
> **Status:** o harness que este produto vende **já existe e já rodou contra dois modelos reais** — não é plano, é reuso do que está em `model-atlas/`.
> **Pergunta que este documento responde:** o que precisa acontecer entre hoje e o primeiro cliente pagando?

---

## 1 · Por que este é o produto certo pra começar

O ciclo D-O-U-V-R-A-S do doc 2 tem sete etapas. Este produto só depende das quatro primeiras:

```text
D  delimitar capacidade      ──┐
O  observar comportamento      │  JÁ FEITO — reusável para qualquer
U  achar padrão de falha       │  modelo/agente que o cliente trouxer
V  tentar refutar              ──┘

R  achar habilidade ausente   ──┐  NÃO precisa disso pra vender
A  criar dataset/fine-tuning    │  auditoria. Isso é o Produto 3/4,
S  medir de novo               ──┘  passo seguinte da escada.
```

Uma auditoria não promete consertar o modelo do cliente — promete **medir** com rigor.
É exatamente o que `model_atlas.runner` + `graders` + `assessment` já fazem.

## 2 · Prova de credibilidade que já existe, verificável

Isso não é alegação de marketing — é reprodutível a partir do repositório público:

- **Achamos um defeito real no artefato publicado de um modelo** (não no nosso trabalho): o
  template de chat embutido no GGUF do `Tucano-2b4-Instruct` fecha a tag de instrução no lugar
  errado, e produz saída degenerada em qualquer ferramenta padrão (`llama-server --jinja`,
  `apply_chat_template`, Ollama, LM Studio). Prova mostrável em 30 segundos:

  ```
  <instruction>Qual é a capital da França?               → resposta coerente
  <instruction>Qual é a capital da França?</instruction>  → "FFQuala</</. A PerguntQual..."
  ```

- **Formulamos uma hipótese e a derrubamos nós mesmos, no mesmo ciclo**, com o falsificador que
  nós próprios escrevemos antes de medir (`C-108` → `R-102`). Isso é o oposto de "vendemos IA
  mágica" — é "medimos, e quando erramos, publicamos que erramos".

- **O escore agregado não discrimina, e dissemos isso** mesmo sendo desfavorável ao nosso
  próprio instrumento (`R-101`, margem 0,062 abaixo do limiar declarado). Cliente que já foi
  enganado por dashboard de IA bonito reconhece a diferença na hora.

Esses três pontos, juntos, são o pitch: **não vendemos confiança, vendemos verificação — e
mostramos a verificação funcionando contra nós mesmos primeiro.**

## 3 · O que é entregue

Estrutura do doc 3, adaptada pro que o harness atual já produz:

```text
Agent Evaluation Report — <nome do cliente>

Tool use ............... XX%
Instruction following .. XX%
Hallucination ........... XX%
Error recovery .......... XX%
JSON compliance ......... XX%
Security / recusa ....... XX%

N falhas críticas · N falhas médias
+ dataset das falhas encontradas (reproduzível)
+ recomendações priorizadas
```

Mapeamento direto pro que já existe em código:

| Linha do relatório | De onde vem |
|---|---|
| Tool use / Instruction following | `by_capability` do `RunResult` |
| Hallucination / Security | capacidades já no corpus (`hallucination`, `safety_refusal`) |
| N falhas críticas | `failure_counts()` + `FailureAtlas` |
| dataset das falhas | as trajetórias reprovadas, já gravadas em JSON |

O corpus de tarefas atual (financeiro/pagamento/agente) já serve de ponto de partida — pra um
cliente fora desse domínio, adapta-se o `TaskSet` (é o Produto 2, upsell natural).

## 4 · Preço — dois mercados, não uma conversão

O doc 3 tem dois preços diferentes pro mesmo produto, de propósito — não é a mesma cifra em
moedas diferentes:

| Mercado | Preço | Papel |
|---|---|---|
| Brasil — entrada | R$ 1.500–3.000 | conseguir caso real + depoimento, não maximizar preço |
| Internacional — pacote | US$ 1.500 ≈ € 1.300 | já é referência de mercado (Upwork, projetos de ML/eval) |

Câmbio de referência **15/08/2026**: US$ 1 ≈ R$ 5,11, € 1 ≈ R$ 5,98 (cotação do dia; o doc 3
usava R$ 5,22/US$ como referência de quando foi escrito — vale reconferir periodicamente, os
dois documentos já divergem por causa disso).

| Item | Valor |
|---|---|
| Prazo de entrega | depende do nº de tarefas × modelo do cliente — referência: 96 tarefas ≈ 45min–3h de CPU |
| Formato | relatório + dataset de falhas + chamada de apresentação |

Meta declarada no doc 3: **não é faturamento, é o primeiro R$ 1.000 saindo do laboratório.**

## 5 · O que falta pra vender — checklist real

- [x] **nome comercial**: `Agent Ledger`. Liga direto ao `CLAIM_LEDGER` (mecanismo real do
      método), carrega a conotação de auditoria/prestação de contas, funciona em EN e PT.
      DOUVRAS fica como nome da metodologia, citado na página, não como marca de venda.
- [x] **WhatsApp**: `+55 21 98230-1476`, com mensagem pré-preenchida por idioma.
- [x] **landing page** em `landing/` (`index.html`, `style.css`, `script.js`), bilíngue PT/EN
      com toggle, sem dependência externa (sem CDN, sem framework, sem chamada de rede além do
      link do WhatsApp). Testada: JS roda, toggle troca conteúdo/idioma/CTA junto, link do
      WhatsApp monta com número e texto certos nos dois idiomas.
      Usa as três provas de credibilidade da seção 2 (bug do Tucano, retratação de `C-108`,
      honestidade sobre o escore agregado) como conteúdo central, não enfeite.
- [ ] **ressalva de mercado**: o `BR-Agent-Bench` é especificamente brasileiro (R$, boleto).
      Pra cliente em PT europeu, isso é upsell natural (Produto 2 — benchmark adaptado ao
      domínio/mercado do cliente), não algo já pronto. A landing page vende o **método**, com
      prova brasileira — não promete benchmark pronto pra Portugal.
- [ ] relatório de amostra anonimizado, gerado a partir do que já rodamos (Tucano/SmolLM3),
      pra anexar quando alguém pedir mais detalhe além do que está na landing page
- [ ] texto curto (LinkedIn/indicação) usando a seção 2 como gancho
- [ ] domínio próprio (hoje a página roda local; precisa de hospedagem + domínio pra ir ao ar)

## 6 · Próximo passo imediato

Publicar a landing page (GitHub Pages, Netlify ou Vercel — grátis, sem precisar do domínio
ainda) pra ter um link real pra compartilhar antes mesmo de registrar domínio próprio.
