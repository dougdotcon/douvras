---
artifact: CHANGELOG
---

# Changelog — Model Atlas

Registra mudanças de **código, corpus, priors e alegações**. Uma mudança de prior que altera
uma recomendação é tão relevante quanto uma mudança de código, e por isso entra aqui.

## [0.3.1] — 2026-08-15 — O modo de raciocínio vale +18,8 pontos, e o escore publicado vira piso

`smollm3-3b` executado em `/think` — o modo **padrão** dele — em 16 tarefas, 2 por capacidade,
pareadas contra as mesmas 16 da execução publicada em `/no_think`.

| | `/no_think` (publicado) | `/think` (padrão do modelo) |
|---|---:|---:|
| escore nas mesmas 16 tarefas | 12,5 % | **31,2 %** |
| chamadas de ferramenta | 14 | **14** |
| `tool_selection` | 0 % | **100 %** |
| `hallucination` | 0 % | **100 %** |
| `error_recovery` | 50 % | 0 % |
| custo por tarefa | ~30 s | 109 s |

**As chamadas de ferramenta são idênticas.** Raciocinar não faz o modelo agir mais — faz ele
**escolher melhor**. É a confirmação direta do que a seção 1 do assessment já dizia sobre esse
modelo: o que falha não é a forma da ação, é a escolha dela.

Consequência: **os 10,4 % publicados são piso, não capacidade.** O assessment passa a dizer
isso, derivado da comparação pareada e não afirmado à mão. `G-116` vai a **PARCIAL** — fechar
exige as 96 tarefas em `/think`, ≈ 2,9 h de CPU.

### Adicionado

- `MeasurementRole` — `role` (publicável ou diagnóstica) separado de `fewshot` (descreve o
  prompt). Eram o mesmo campo fazendo dois trabalhos, e foi por isso que uma execução zero-shot
  quase foi gravada como `fewshot: true` só para não virar escore. `role` gravado
  explicitamente nos quatro artefatos; a regra de compatibilidade serve só a artefato antigo.
- O assessment lista **todos** os diagnósticos numa tabela pareada, comparando com o escore das
  mesmas tarefas na execução publicada — não contra o agregado, que seria comparação torta.
- `G-117` — nenhum modelo do corpus foi comparado sob orçamento de tempo igual, e `/think`
  custa 3,6× por tarefa. Qualquer ranking entre modelo com e sem raciocínio depende disso.

## [0.3.0] — 2026-08-15 — Segundo modelo medido, e `C-108` retratada no mesmo ciclo

`smollm3-3b` Q4_K_M executado nas mesmas 96 tarefas, mesmo prompt, mesma máquina. A alegação
registrada horas antes não sobreviveu ao próprio falsificador.

### O contraexemplo

| | `tucano-2b4-instruct` | `smollm3-3b` |
|---|---:|---:|
| chamadas de ferramenta | **0** | **78** |
| passos totais | 96 | 205 |
| passos numa mesma tarefa | sempre 1 | até 6 |
| tipos de ação emitidos | só `responder` | as quatro |
| escore geral | 0,0 % | **10,4 %** |
| `arguments` | 0,0 % | **50,0 %** |
| `error_recovery` | 0,0 % | **33,3 %** |
| tokens/s | 12,14 | 8,26 |

`C-108` — *"modelos instruídos de 2B a 3B não instanciam protocolo de chamada de ferramenta"* —
**retratada** por `R-102`. Porte não era a variável. O que é fica em `G-115`, sem resposta.

### O que a segunda medição não desfez

A margem agregada entre os dois modelos reais é **0,104** — ainda abaixo do limiar de 0,20 de
`F3`, entre um modelo que nunca chama ferramenta e um que chama 78 vezes. A segunda medição
portanto **reforça** a retratação `R-101` em vez de enfraquecê-la. O sinal está no perfil por
capacidade (+0,500 em `arguments`), não no agregado — registrado como `C-109`, conjectura nova
com falsificador próprio, e **não** como ressurreição de `C-102`.

### Adicionado

- `ConversationFormat` — o envelope de conversa vira campo declarado do instrumento, não
  pressuposto embutido. `raw-instruction` para o Tucano (template publicado quebrado),
  `chat-template` para o SmolLM3 (template verificado e correto).
- `system_mode` e `conversation_format` no artefato de medição.
- `smollm3-3b` com pesos locais e template verificado pelo `RB-102` antes de qualquer medição.
- 20 testes para `backends.py`, que tinha **zero** — a peça que decide todo escore
  (`parse_action`) é função pura e estava sem cobertura por hábito, não por necessidade.
- 3 testes fixando o contraexemplo e a margem que sustenta `R-101`.

### Corrigido

- `registry verify` deixava `params_b` arredondado quando a diferença cabia na tolerância:
  `smollm3-3b` ficava com `3.0` num checkpoint de 3,0751 B, marcado como conferido, com o
  footprint 2,5 % abaixo do real. A tolerância decide se é **erro de transcrição**, não se vale
  gravar a contagem real. Conferido passa a significar exato.
- A seção 1 do assessment tinha texto fixo ("nunca chega a chamar uma") ao lado de número
  calculado — falso para o SmolLM3. O diagnóstico passa a derivar da contagem.
- `publish_run.py` carregava o GGUF inteiro na RAM para o hash e estourava a partir de ~1,5 GB.
- Um artefato de medição foi gravado com `fewshot: true` para uma execução zero-shot e removido
  antes de qualquer publicação: rótulo errado em proveniência é pior que artefato ausente.

### Lacunas novas

`G-115` (porte não explica a diferença; o que explica não foi medido), `G-116` (`smollm3-3b`
medido em `/no_think`, e o padrão dele é `/think`).

## [0.2.0] — 2026-08-15 — Primeira execução real: `G-101` e `G-102` parciais

`tucano-2b4-instruct` Q4_K_M executado nas 96 tarefas do BR-Agent-Bench, em CPU, via llama.cpp
b10435. É a primeira capacidade **medida** do eixo.

### Resultado

| Medida | Valor |
|---|---:|
| escore geral | **0,0 %** (0/96) |
| chamadas de ferramenta emitidas | **0** |
| tokens/s (geração, Q4, CPU) | 12,14 |
| TTFT médio | 6,42 s |
| tempo de modelo | 2 630 s |

O modelo não erra a ferramenta — **nunca chega a chamar uma**. Toda trajetória termina no
primeiro passo com um objeto JSON que tem a forma do contrato e valores de exemplo
(`"ferramenta": "nome_da_ferramenta"` copiado literalmente). Ele descreve o protocolo em vez
de executá-lo. Fora do protocolo, responde português normalmente.

**A hipótese óbvia foi testada e rejeitada**: um exemplo demonstrado injetado no prompt
(`G-112`, modo diagnóstico, 16 tarefas cobrindo as oito capacidades) manteve o escore em 0,0 %
e as chamadas em zero.

### Adicionado

- `backends.py` — `llama-server` por HTTP, telemetria, prompt versionado, parser sem reparo.
- `measurements.py` — execução real vira **evidência versionada** em `99_RELEASES/runs/`, com
  hash dos pesos, runtime, quantização e versão de prompt. O ciclo reemite o assessment offline
  a partir dela, preservando o `ADR-0006`.
- `tucano-2b4-instruct` no corpus, ficha conferida na fonte (2 444 628 480 parâmetros).
- `RB-102` — runbook de execução real, com o procedimento de diagnóstico de formato.
- `C-108` como **conjectura** a partir de uma observação, com falsificadores declarados.

### Encontrado no artefato publicado do modelo

**O template de chat embutido no GGUF está errado** (`G-114`). Ele fecha `</instruction>` dentro
do prompt; o modelo foi treinado para emitir essa tag. Medido:

| Prompt | Saída |
|---|---|
| `<instruction>Q` | `</instruction>A capital da França é Paris…` |
| `<instruction>Q</instruction>` | `FFQuala</</. A PerguntQualfQual…` |

O tokenizer está correto e não depende de BOS. Consequência: toda ferramenta que aplique o
template publicado recebe saída degenerada desse modelo.

### Corrigido antes de medir

- Harness enviava role `system`, que o template do modelo rejeita por exceção.
- Prompt `v1` punha o contrato antes da lista de ferramentas, e o modelo **continuava a lista**
  em vez de agir. `v2` move o contrato para o fim, colado à geração. Revisão feita antes de
  qualquer execução completa e declarada em `PROMPT_VERSION`.
- Terceira regra de coerência no portão de emissão: a seção 2 seguia afirmando "nenhuma ficha
  foi conferida" depois de `G-108` fechar, porque a frase era fixa e o `Finding` era calculado.

### Lacunas novas

`G-112` (prompt zero-shot, nunca ablacionado), `G-113` (só Q4 executado), `G-114` (template do
GGUF defeituoso).

## [0.1.1] — 2026-08-15 — `G-108` fechada, duas fichas corrigidas

Primeira execução de `matlas registry verify` contra o Hub. **3 de 3 fichas conferidas**, com
hash e data gravados no corpus.

### Adicionado

- `verify_spec` e `record_verification`: o comando deixou de ser um aviso e passou a conferir
  contra a API do Hub. Separa **conferir** (campo declarado diverge = erro de transcrição) de
  **descobrir** (campo nulo preenchido pela fonte = lacuna fechando).
- Tolerância de 5 % em `params_b`: a ficha vinha de documento que diz "cerca de", e exigir
  igualdade exata reprovaria uma transcrição honesta.

### Corrigido

- **COR-101** — `tucano2-0.5b` declarava `Qwen2ForCausalLM`, inferido do nome do repositório;
  o checkpoint diz `Qwen3ForCausalLM`. Parâmetros: 0,5 → 0,4908 B.
- **COR-102** — `qwen3.5-0.8b` declarava 0,8 B; o checkpoint tem **0,8734 B**, erro de 8,4 %.
  O nome comercial não é a contagem. O footprint publicado estava 8,4 % abaixo do real em toda
  quantização — para menos, que é a direção perigosa quando a pergunta é "cabe em 16 GB?".

### Descoberto pela fonte

`license` nos três; `context_len` de `tucano2-0.5b` (4096) e `smollm3-3b` (65536); e a
arquitetura de `qwen3.5-0.8b` — `Qwen3_5ForConditionalGeneration`, que não é puramente causal e
merece atenção antes de ser tratada como baseline de agente de texto.

### Efeito no contrato

`params_b` conferido não carrega mais `A-101`: o `Finding` `parametros` sai como `OBSERVATION`
em vez de `ASSUMPTION`, e `corpus_provenance` subiu de `CONDITIONAL_RESULT` para `OBSERVATION`.
Lacunas abertas: 11 → **10**.

## [0.1.0] — 2026-08-14 — Ciclo C-002: o instrumento antes da medida

### Adicionado

- `douvras_core` extraído do Silicon Atlas (`ADR-0005`): `status`, `paths`, `gates`, `report`.
  Os dois atlas passam a compartilhar escala de status, portões e portão de emissão.
- `model_atlas` com nove módulos: `tasks` (vocabulário e ambiente executável), `graders`
  (17 regras declarativas), `runner` (execução e sondas), `instrument` (verificação do
  instrumento), `capability`, `failure`, `css`, `profiler`, `registry`, `assessment` e `cli`.
- **BR-Agent-Bench v0.1**: 96 tarefas em 8 capacidades, 132 contraexemplos rotulados, gerados
  por `scripts/build_task_corpus.py` sem nenhuma fonte de aleatoriedade.
- Oito sondas de calibração, cada uma com o modo de falha que promete disparar declarado em
  `runner.PROBES` **antes** da execução.
- `MODEL CAPABILITY ASSESSMENT` com portão de emissão: seções obrigatórias, vocabulário,
  números não-finitos, coerência interna e promoção à mão.
- Governança completa do ciclo: carta com seis falsificadores, premissas `A-101`..`A-106`,
  onze lacunas, baseline congelado, protocolo `X-002`, duas UMIs, três ADRs, runbook.

### Medido

| Métrica | Valor |
|---|---:|
| aceitação do gabarito | 100,0 % (96/96) |
| rejeição de contraexemplo | 100,0 % (132) |
| precisão do rótulo | 100,0 % |
| determinismo | idêntico entre execuções |
| modos de falha sem sonda | nenhum |
| margem de discriminação agregada | **0,062** |

### Retratado — precede as correções (Método §4.7)

- **R-101** — `C-102`, a alegação de que o escore agregado separa respondente correto de
  degenerado por margem maior que 0,20. Falsificador `F3` disparado com 0,062. Diagnóstico em
  `CE-101`: cada sonda ataca uma família e o agregado dilui o dano pelo corpus inteiro —
  `desiste-no-erro` destrói 100 % do que ataca e move o agregado em 0,125.

### Corrigido durante o ciclo

- `check_status_floor` do core verificava condição inalcançável (um `Finding` com lacuna não
  nasce acima de `CONDITIONAL_RESULT`, o construtor impede). Substituída por
  `check_no_hand_promotion`, que verifica algo que pode de fato acontecer.
- Primeiro diagnóstico de `CE-101` comparava o oráculo com a melhor sonda **dentro de cada
  capacidade** e devolvia 0,000 em todas — porque para toda capacidade existe alguma sonda que
  não a ataca. Substituído pela comparação de cada sonda contra o oráculo no alvo que ela
  própria declarou.
- `Environment.call` tinha lógica de `recover_after` que nunca se recuperava, tornando "falha
  transitória" indistinguível de "falha permanente" e esvaziando metade das tarefas de
  recuperação.
- `_rule_must_ask` levantava `StopIteration` em trajetória sem nenhuma chamada.

### Lacunas novas

`G-101` a `G-111`. As três do caminho crítico: `G-101` (nenhuma execução real), `G-104` (priors
do CSS não calibrados) e `G-107` (corpus sintético, validade externa não estabelecida).

### Verificação de não-regressão do Silicon Atlas

Os 24 artefatos do ciclo C-001 foram reemitidos após a extração do core e comparados com a
versão anterior, ignorando `run_id` e timestamp: **zero diferença de conteúdo**. Os 149 testes
do eixo de silício seguem verdes.
