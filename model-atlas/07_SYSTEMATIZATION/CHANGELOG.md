---
artifact: CHANGELOG
---

# Changelog — Model Atlas

Registra mudanças de **código, corpus, priors e alegações**. Uma mudança de prior que altera
uma recomendação é tão relevante quanto uma mudança de código, e por isso entra aqui.

## [0.4.0] — 2026-08-19 — Primeiro caso de `G-104`: achado um exploit de grader antes de publicar

Primeira tentativa de calibrar os priors do CSS (`G-104`): medir uma capacidade, construir
dataset direcionado, fine-tunar, medir de novo. `structured_output`, LoRA em
`smollm2-360m-instruct` (o único modelo do corpus que roda fine-tuning nesta máquina — ver
"Feasibility de fine-tuning" abaixo).

### Achado ao vivo: "0 % → 100 %" era exploit, não capacidade

O adaptador saiu das 12 tarefas reais de `structured_output` com 100 %. Inspecionar a
trajetória crua (não só o veredicto agregado) mostrou por quê: em todas as 12, sem exceção, o
modelo chamava `consultar_chamado` com a chave errada (`ticket` em vez de `id`, garantindo
falha), recebia erro, e respondia um JSON fixo e plausível — `"departamento": "Servicos de
Transporte"`, valor que **não existe** em nenhuma tabela do corpus.

O grader não pegava porque `answer_json` só verificava presença de chave (nunca valor) e
`must_call` só verificava o nome da ferramenta usada (nunca se a chamada teve sucesso). Doze
tarefas, doze respostas fabricadas, zero detecção.

**Corrigido (`G-120`, fechada):**
- regra nova `answer_grounded` — a resposta final tem que bater com a última observação
  bem-sucedida da ferramenta, não só ter as chaves certas;
- `arg_equals` adicionado às 12 tarefas, travando o argumento correto;
- contraexemplo reproduzindo o exploit exato, verificado como rejeitado;
- 5 testes novos em `test_graders_and_env.py` fixando o comportamento, incluindo um teste
  que confirma que `answer_grounded` é opt-in (não afeta tarefas que não o declaram).

Sob o grader corrigido, o mesmo par saiu **0 % → 0 %**: nenhum ganho real de capacidade nesta
tentativa. `G-104` vai a **PARCIAL** (1/3 casos) com esse resultado — explicitamente marcado
como fraco/confundido, não uma calibração limpa (ver razão abaixo). `C-111` registrada como
`CONJECTURE`. O prior declarado (`tractability: 0.90`) **não foi alterado**: um caso confundido
não é motivo para reponderar o instrumento.

Nada disso chegou a ser publicado ou commitado antes da correção — mas o número chegou a ser
calculado, e quase virou a base da primeira calibração de `G-104`. Documentado em
`RETRACTIONS_AND_CORRECTIONS.md` como correção de percurso.

### Feasibility de fine-tuning nesta máquina (achado à parte, vale para além de `G-104`)

- **LoRA em `smollm3-3b` (3B) não é viável aqui**: nem um passo de gradiente completou sem
  esgotar a RAM (venv 64-bit, 14 GB de RAM), mesmo com `gradient_checkpointing`. Confirma
  empiricamente o que o documento de planejamento original só supunha.
- **LoRA em `smollm2-360m-instruct` (360 M) é viável, mas lento**: ~800–850 s por passo de
  gradiente em CPU pura. 80 exemplos, 1 época = 80 passos = **18h21min** de treino real.
- Ambos os modelos pequenos alternativos do corpus (`tucano2-0.5b`, `qwen3.5-0.8b`) foram
  descartados antes de tentar: o primeiro é modelo base sem instruction-tuning, o segundo tem
  arquitetura `Qwen3_5ForConditionalGeneration`, não um LM causal padrão.

### Infraestrutura nova

- `.local/train_lora_structured_output.py` — script de treino LoRA, parametrizado por modelo/
  dataset/saída, com checkpoint a cada passo e callback de progresso (`tqdm` não aparece em log
  redirecionado — sem isso, uma execução de 18h fica sem nenhum sinal visível).
- `.local/build_structured_output_dataset.py` — gera exemplos de treino em domínios ausentes
  do corpus de avaliação (pedido/funcionário/produto/contrato, não "chamado"), no mesmo formato
  exato do harness real (`CABECALHO`/`CONTRATO` de `backends.py`) — treino e avaliação têm que
  falar o mesmo formato, ou uma diferença de formato se disfarça de capacidade.
- `.local/eval_hf_model.py` — avalia modelo `transformers` (base ou base+adaptador LoRA) contra
  o BR-Agent-Bench real, reusando `build_messages`/`parse_action`/`grade` do harness principal.
  Salva trajetórias completas, não só o veredicto — foi inspecionando essas trajetórias que o
  exploit apareceu.

## [0.3.3] — 2026-08-17 — `/think` fecha em 96/96: fecha `G-116` e `G-118`

`G-118` (Smart App Control bloqueando `llama-server.exe`) foi decisão do usuário desativar a
política — ação que está fora do que este agente executa por conta própria (mexer em
configuração de segurança do sistema é regra dura, não julgamento de caso). Depois disso, mais
uma trava: contenção de RAM com outro processo do usuário, resolvida esperando ele terminar.
Com as duas fora do caminho, a suíte terminou: **96/96 tarefas, zero erro de infraestrutura**.

### Números finais, pareados contra `/no_think` publicado

| | `/no_think` | `/think`, 71/96 (interino) | `/think`, **96/96** |
|---|---:|---:|---:|
| agregado | 10,4 % | 21,1 % | **25,0 %** |
| chamadas de ferramenta | 78 | 35/71 | **66/96** |
| `tool_selection` | 0,0 % | — | **75,0 %** |
| `hallucination` | 0,0 % | 83,3 % | **83,3 %** |
| `arguments` | 50,0 % | 41,7 % | **41,7 %** |
| `error_recovery` | 33,3 % | 0,0 % | **0,0 %** |

A peça que só aparece nas 96 completas: `tool_selection` (0 %→75 %) é praticamente todo o
ganho agregado. A amostra de 71 não continha as últimas tarefas dessa capacidade.

### Corrigido

- Seção 11 do assessment (`o_que_nao_demonstra`) tinha texto fixo — "Não mede nenhuma
  capacidade" — que continuou aparecendo para modelos **já medidos**, contradizendo a seção 1
  do mesmo relatório. Mesma classe de defeito do `G-012` (texto fixo ao lado de número
  calculado), num lugar que nenhuma das três regras de coerência anteriores cobria. Quarta
  regra adicionada.

### Adicionado

- `C-110`: reasoning melhora o agregado mas o efeito por capacidade não é uniforme, e chamadas
  de ferramenta caem em vez de empatar. `HYPOTHESIS` — direção estável através de três amostras
  crescentes (16→71→96), mas ainda um único modelo.

### Fechado

`G-116` (medição completa de `/think`), `G-118` (bloqueio do Smart App Control).

## [0.3.2] — 2026-08-17 — `/think` chega a 71/96, retrata a conclusão da amostra de 16

A execução completa de `smollm3-3b` em `/think` avançou de 16 para 71 tarefas graduadas (73,9 %
do corpus) antes de ser interrompida em definitivo por `G-118`. O ganho de amostra mudou a
conclusão publicada.

### Retratado — `R-103`

"As chamadas de ferramenta são idênticas entre `/think` e `/no_think`" — publicado no ciclo
anterior a partir de 16 tarefas (14 chamadas em cada modo, coincidência de amostra pequena).
Com 71 tarefas: **0,81 chamada/tarefa em `/no_think` vs 0,49 em `/think`** — caem, não ficam
iguais. E o efeito por capacidade é misto, não uniformemente positivo:

| Capacidade | `/no_think` | `/think` |
|---|---:|---:|
| `hallucination` | 0,0 % | **83,3 %** |
| `arguments` | 50,0 % | **41,7 %** (piora) |
| `error_recovery` | 33,3 % | **0,0 %** (piora) |

O que sobrevive: `/no_think` continua sendo **piso**, não capacidade — o agregado pareado nas
71 tarefas ainda sobe com raciocínio (14,1 % → 21,1 %, +7,0 pontos). Só a explicação
mecanística ("mesma ação, julgamento melhor") caiu.

### Por que parou em 71/96, não 96/96

Três causas reais, nesta ordem de aparição, cada uma corrigida quando encontrada:

1. **Timeout HTTP curto demais** para respostas longas de raciocínio em CPU — corrigido
   (300s → 900s configurável).
2. **Sessão reiniciando sozinha**, matando qualquer processo filho do bash — contornado
   rodando a suíte via Agendador de Tarefas do Windows, desacoplada da árvore de processos
   da sessão. Checkpoint passou a gravar a cada tarefa, não a cada 5.
3. **`llama-server` morrendo sob carga sustentada** (`ConnectionResetError`), sem log próprio
   (rodava com `stdout`/`stderr` em `DEVNULL`) — corrigido: log do servidor capturado, e o
   harness agora detecta processo morto e reinicia sozinho antes da próxima tarefa.
4. **Bloqueio definitivo**: Smart App Control do Windows passou a recusar executar
   `llama-server.exe` depois de ~36h rodando sem problema (`G-118`, aberta). Isso não é
   contornável por código — é decisão de segurança do usuário, e a execução parou aí.

### Corrigido no processo

- `print()` derrubava o processo inteiro com `OSError: Invalid argument` ao tentar escrever um
  caractere fora de ASCII sob a página de código do Agendador de Tarefas — `stdout`/`stderr`
  reconfigurados para UTF-8 com `errors="replace"`.
- Merge de `--resume-from` duplicava o registro de uma tarefa que errasse por infraestrutura
  duas vezes seguidas (uma entrada do checkpoint antigo, outra da nova tentativa).
- Venv do projeto era **Python de 32 bits**, com endereçamento útil de ~2 GB numa máquina com
  14 GB de RAM — causou `MemoryError` ao serializar o checkpoint com dezenas de trajetórias de
  `/think` acumuladas. Reconstruído com Python 3.11 de 64 bits.

### Adicionado

- `LlamaServer.alive`, `log_path` — o servidor pode ter seu próprio log capturado, e o
  harness sabe distinguir "está vivo" de "morreu" em vez de só tentar e falhar.
- `run_bench.py --resume-from`, `--ctx`: retomada real de execução interrompida, sem perder
  tarefas já graduadas; contexto do servidor configurável (`/think` precisa de mais que 4096).
- `publish_run.py --allow-partial`: publicar uma medição incompleta exige reconhecer isso
  explicitamente — por padrão o script recusa.

`G-116` segue **PARCIAL**, com evidência bem maior que antes mas ainda não fechada — bloqueada
por `G-118`, que não é um problema de código.

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
