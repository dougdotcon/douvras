---
artifact: RETRACTIONS_AND_CORRECTIONS
cycle: C-002
policy: a retratação precede a correção (Método §4.7)
---

# Retratações e correções — Model Atlas

Uma afirmação publicada que não sobrevive ao próprio critério é **retirada antes** de qualquer
tentativa de consertar o que a produziu. A ordem importa: corrigir primeiro e retratar depois
transforma retratação em nota de rodapé de um resultado novo.

## R-101 — `C-102` retratada: o escore agregado não discrimina

**O que se afirmava.** Que o escore agregado do BR-Agent-Bench separaria um respondente correto
de um degenerado por margem maior que 0,20.

**O que derrubou.** O falsificador `F3`, declarado na [PROBLEM_CHARTER](../01_DELIMITATION/PROBLEM_CHARTER.md)
antes da primeira execução do ciclo. Margem medida: **0,062**.

**Diagnóstico.** [CE-101](../04_VALIDATION/COUNTEREXAMPLES/CE-101-margem-agregada-diluida.md).
Cada sonda ataca uma família; o agregado divide o dano pelo corpus inteiro. `desiste-no-erro`
destrói 100 % das tarefas que ataca e move o agregado em 0,125.

**O que sobrevive.** `C-101` (o grader aceita gabarito e rejeita contraexemplo com rótulo
correto), `C-103` (toda tarefa avaliável, cobertura mínima atendida), `C-104` (nenhum modo de
falha morto) e `C-105` (determinismo) são independentes e continuam de pé, medidos em 100 %.
A conclusão que cai é sobre o **escore agregado**, não sobre o instrumento.

**O que não foi feito.** A métrica de `F3` não foi trocada. Trocar a definição de um
falsificador depois de vê-lo disparar é ajustar o instrumento ao resultado. O diagnóstico por
sonda (`probe_sensitivity`) foi acrescentado como *medida auxiliar declarada como diagnóstico*,
e está explicitamente marcado no código e no relatório como não sendo critério.

**Consequência aplicada.** Portão V3 bloqueado. Nenhum relatório deste ciclo apresenta escore
agregado como decisão.

---

## R-102 — `C-108` retratada: modelos de 2B a 3B **sim** chamam ferramentas

**O que se afirmava.** Que modelos instruídos de porte 2B a 3B não instanciam um protocolo de
chamada de ferramenta em português sem fine-tuning específico — que reconheceriam a forma do
contrato e devolveriam o schema com valores de exemplo.

**O que derrubou.** O primeiro dos falsificadores declarados junto com a alegação: *"qualquer
modelo dessa faixa emitir chamada de ferramenta válida em mais de 10 % das tarefas, com prompt
declarado antes"*. `smollm3-3b` (3,08 B, Q4_K_M, mesmo prompt `agent-ptbr-v2`, mesma máquina)
executado nas mesmas 96 tarefas:

| | `tucano-2b4-instruct` | `smollm3-3b` |
|---|---:|---:|
| chamadas de ferramenta | **0** | **78** |
| passos totais | 96 | 205 |
| passos numa mesma tarefa | sempre 1 | até 6 |
| tipos de ação emitidos | só `responder` | as quatro |
| escore geral | 0,0 % | 10,4 % |

Não é margem apertada: são 78 chamadas contra zero. `C-108` cai por contraexemplo direto.

**Diagnóstico.** A alegação generalizava **uma** observação para uma faixa inteira de tamanho.
O que o Tucano mostrou era verdade sobre o Tucano; a ponte para "modelos de 2B a 3B" foi feita
por analogia de porte, e porte não é a variável que decide. A alegação nasceu marcada como
`CONJECTURE` justamente por isso, e o falsificador que a derrubou foi escrito antes da execução
que a derrubou — o que funcionou como devia.

**O que sobrevive.** A medição do Tucano continua íntegra: 0,0 % com zero chamadas, sob os
qualificadores declarados. O que cai é a **generalização**, não a observação. Também sobrevive,
e fica mais forte, `G-114`: o defeito do template é específico daquele GGUF, e o SmolLM3 —
cujo template foi verificado pelo `RB-102` e está correto — mostra que rodar modelo local não
é intrinsecamente frágil.

**O que a retratação abre.** Se o porte não explica, o que explica? Fica registrado como `G-115`,
sem resposta neste ciclo. Candidatos não testados: a composição do corpus de instrução, a
presença de dados de chamada de ferramenta no treino, e a perda de quantização (`G-113`, agora
mais urgente porque os dois modelos foram medidos só em Q4).

**Consequência aplicada.** `C-108` marcada `RETRACTED` no ledger antes de qualquer outra
mudança neste ciclo. Nenhum relatório apresenta a generalização por porte.

---

## R-103 — "as chamadas de ferramenta são idênticas entre `/think` e `/no_think`" retratada

**O que se afirmava.** Que raciocinar não muda o que o modelo *faz* — só a *escolha*. A base era
uma amostra pareada de 16 tarefas (2 por capacidade) do `smollm3-3b`, onde as duas execuções
produziram exatamente 14 chamadas de ferramenta cada. Publicado no changelog, no README e no
commit `2fbac50` como conclusão.

**O que derrubou.** A execução completa das 96 tarefas em `/think` — interrompida por `G-118`
antes de terminar, mas chegando a **71/96** tarefas graduadas antes disso, mais de quatro vezes
a amostra original. Nas mesmas 71 tarefas:

| | `/no_think` (publicado) | `/think` |
|---|---:|---:|
| chamadas de ferramenta por tarefa | 0,81 (78/96) | **0,49** (35/71) |
| `hallucination` | 0,0 % | **83,3 %** |
| `arguments` | 50,0 % | **41,7 %** |
| `error_recovery` | 33,3 % | **0,0 %** |

As chamadas de ferramenta **caem** com raciocínio ligado, não ficam iguais. E o efeito por
capacidade não é uniformemente positivo: `hallucination` melhora muito, `arguments` e
`error_recovery` **pioram**. "Mesma ação, julgamento melhor" era uma leitura limpa demais para
uma amostra de 16 tarefas — 2 por capacidade é o suficiente para detectar direção, não para
caracterizar o efeito.

**Diagnóstico.** Clássico erro de amostra pequena: 14 chamadas em 16 tarefas e 14 em 16 tarefas
é uma coincidência plausível em amostra desse tamanho, não uma lei do comportamento do modelo.
O texto generalizou uma coincidência numérica em afirmação mecanística ("raciocinar não faz o
modelo agir mais") sem testar se ela sobrevivia a mais dados. A tabela do assessment que gera
esse número (`assessment.py`, seção "O que este número não mede") sempre foi derivada da
contagem real — o defeito não estava no código, estava na prosa escrita por cima dele num
commit anterior, que não foi atualizada quando a amostra cresceu.

**O que sobrevive.** O achado principal do `R-101`/commit `2fbac50` continua de pé: o escore
publicado em `/no_think` é **piso, não capacidade** — `/think` ainda vence no agregado pareado.
O que cai é só a explicação mecanística de *por que*.

**Atualização com as 96/96 completas (fecha `G-116` e `G-118`).** `G-118` — bloqueio do Smart
App Control do Windows contra `llama-server.exe` — o usuário desativou a política, decisão
dele, não minha (mexer em configuração de segurança do sistema está fora do que eu posso
fazer). Com isso a suite terminou: **96/96 tarefas, zero erro de infraestrutura**.

| | `/no_think` (publicado) | `/think`, 71/96 (interino) | `/think`, **96/96 (final)** |
|---|---:|---:|---:|
| escore agregado | 10,4 % | 21,1 % | **25,0 %** |
| chamadas de ferramenta | 78 | 35/71 (0,49/tarefa) | **66/96** (0,69/tarefa) |
| `tool_selection` | 0,0 % | — | **75,0 %** |
| `hallucination` | 0,0 % | 83,3 % | **83,3 %** |
| `arguments` | 50,0 % | 41,7 % | **41,7 %** |
| `error_recovery` | 33,3 % | 0,0 % | **0,0 %** |

O número de 71 tarefas já apontava a direção certa (efeito misto, chamadas caem em vez de
ficarem iguais) — não é uma segunda retratação, é a mesma correção com a amostra completa. A
peça que a amostra de 71 não continha: `tool_selection` sozinho explica boa parte do ganho
agregado (+75 pontos), e isso só aparece quando as últimas 12 tarefas dessa capacidade entram
na conta.

**Consequência aplicada.** `G-116` **FECHADA**. `G-118` **FECHADA**. Medição publicada em
[`RUN-smollm3-3b-think-agent-ptbr-v2.json`](../99_RELEASES/runs/RUN-smollm3-3b-think-agent-ptbr-v2.json),
substituindo a versão de 71 tarefas. `G-117` permanece `OPEN` com o número final (+14,6 pontos):
o problema que ela nomeia — nenhum modelo comparado sob orçamento de tempo igual — continua sem
evidência que o feche; terminar a suite só tornou o número mais preciso.

---

## O que a segunda medição **não** desfez

Com dois modelos reais medidos, a tentação óbvia era reabrir `C-102` — a alegação de que o
escore agregado discrimina, retratada em `R-101` por margem de 0,062. A tentação foi verificada
e recusada pelos próprios números:

> margem agregada entre `smollm3-3b` e `tucano-2b4-instruct`: **0,104**

Ainda **abaixo** do limiar declarado de 0,20, entre um modelo que nunca chama ferramenta e um
que chama 78 vezes. A segunda medição portanto **reforça** `R-101` em vez de enfraquecê-la.

O perfil **por capacidade**, no mesmo par, separa com folga onde o agregado não separa:

| Capacidade | `tucano` | `smollm3` | margem |
|---|---:|---:|---:|
| `arguments` | 0,0 % | 50,0 % | **+0,500** |
| `error_recovery` | 0,0 % | 33,3 % | **+0,333** |
| as outras seis | 0,0 % | 0,0 % | 0,000 |

É exatamente o diagnóstico de [CE-101](../04_VALIDATION/COUNTEREXAMPLES/CE-101-margem-agregada-diluida.md):
a agregação divide o sinal pelo corpus inteiro. Duas capacidades com diferença enorme viram
0,104 quando somadas a seis empatadas em zero.

Isso não ressuscita `C-102`, e a distinção importa: `C-102` falava de separar um respondente
correto de um **degenerado**, e `F3` mede aquilo. Que dois modelos reais se separem por
capacidade é outra afirmação, e está registrada como `C-109` — nova, com falsificador próprio.
Desretratar trocando o significado da frase seria o defeito que este documento existe para
impedir.

---

## COR-101 e COR-102 — duas fichas do corpus estavam erradas

Encontradas ao fechar `G-108` em 2026-08-15, pela primeira execução de
`matlas registry verify` contra o Hub. As duas passaram despercebidas por transcrição de
documento secundário, e nenhuma delas seria detectável offline.

| # | Modelo | Campo | Ficha transcrita | Fonte | Efeito |
|---|---|---|---|---|---|
| **COR-101** | `tucano2-0.5b` | `architecture` | `Qwen2ForCausalLM` | `Qwen3ForCausalLM` | inferido do nome do repositório, não lido do checkpoint |
| **COR-101** | `tucano2-0.5b` | `params_b` | 0,5 | 0,4908 | dentro da tolerância; corrigido para o valor exato |
| **COR-102** | `qwen3.5-0.8b` | `params_b` | 0,8 | **0,8734** | erro de **8,4 %**, acima da tolerância de 5 % |

**Por que `COR-102` importa.** `0,8B` é o nome comercial; o checkpoint tem 873 438 784
parâmetros. O orçamento de memória multiplica essa contagem por bytes-por-parâmetro, então o
footprint publicado estava 8,4 % abaixo do real em toda quantização — para menos, que é a
direção perigosa quando a pergunta é *"cabe em 16 GB?"*.

**O que a verificação também descobriu.** Campos que a ficha deixava nulos por honestidade
(`D-108`) agora vêm da fonte: `license` nos três, `context_len` em `tucano2-0.5b` (4096) e
`smollm3-3b` (65536), e a arquitetura de `qwen3.5-0.8b` —
`Qwen3_5ForConditionalGeneration`, que não é uma classe puramente causal e merece atenção
antes de ser tratada como baseline de agente de texto.

**Consequência aplicada.** `params_b` conferido deixa de carregar `A-101`: o `Finding`
`parametros` sai como `OBSERVATION` em vez de `ASSUMPTION` para modelo verificado, e a dívida
de evidência do assessment cai. `G-108` fechada; a linha correspondente na dívida de evidência
foi quitada.

---

## Correções de percurso

Duas coisas foram corrigidas durante o ciclo, antes de qualquer publicação. Ficam registradas
porque erro corrigido em silêncio vira erro repetido.

- **Verificação vazia no core.** `check_status_floor` verificava `weakest > teto and open_gaps`
  — condição inalcançável, porque um `Finding` com lacuna não consegue nascer acima de
  `CONDITIONAL_RESULT` (o construtor levanta `StatusViolation`). Era um teste que nunca podia
  falhar, exatamente a classe de defeito que o Silicon Atlas encontrou nos testes de partição.
  Substituída por `check_no_hand_promotion`, que verifica algo alcançável: um `Finding`
  construído à mão com status acima do mais fraco dos pais que ele mesmo declara.

- **Primeiro diagnóstico de `CE-101` também estava confundido.** A tentativa inicial comparava
  o oráculo com a *melhor* sonda dentro de cada capacidade, e devolvia 0,000 em todas — porque
  para toda capacidade existe alguma sonda que não a ataca. A comparação que informa é a de
  cada sonda contra o oráculo no alvo que ela própria declarou. O primeiro número não chegou a
  ser publicado, mas chegou a ser calculado, e a diferença entre as duas leituras é a mesma que
  separa uma métrica de uma métrica confundida.

---

## Modelo para novas entradas

```markdown
## R-1XX — <afirmação> retratada

**O que se afirmava.**
**O que derrubou.**
**Diagnóstico.**
**O que sobrevive.**
**Consequência aplicada.**
```
