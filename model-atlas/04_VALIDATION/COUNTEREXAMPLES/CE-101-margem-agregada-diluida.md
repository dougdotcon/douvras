---
artifact: COUNTEREXAMPLE
id: CE-101
cycle: C-002
date: 2026-08-14
claim: C-102
status: PRESERVADO
---

# CE-101 — a margem agregada é diluída pelo tamanho da família atacada

## O que caiu

`C-102`: *"o escore agregado do BR-Agent-Bench separa um respondente correto de um respondente
degenerado por margem maior que 0,20."*

Falsificador **F3 disparado**. Margem medida: **0,062**, contra o limiar declarado de 0,20.

## O número

| Sonda | Escore agregado | Tarefas no alvo | % do corpus | Queda no alvo | Queda agregada |
|---|---:|---:|---:|---:|---:|
| `oraculo` | 1,000 | — | — | — | — |
| `resposta-direta` | 0,000 | 36 | 37,5 % | 1,000 | 1,000 |
| `ferramenta-errada` | 0,438 | 36 | 37,5 % | 0,667 | 0,562 |
| `impulsivo` | 0,562 | 24 | 25,0 % | 0,250 | 0,438 |
| `argumento-errado` | 0,688 | 30 | 31,2 % | 1,000 | 0,312 |
| `json-quebrado` | 0,688 | 12 | 12,5 % | 1,000 | 0,312 |
| `desiste-no-erro` | 0,875 | 12 | 12,5 % | 1,000 | 0,125 |
| `plano-invertido` | **0,938** | 24 | 25,0 % | 0,250 | **0,062** |

A margem agregada é `1,000 − 0,938 = 0,062`, definida pela sonda que menos derruba o agregado.

## O diagnóstico

Cada sonda ataca **uma** família de tarefas. O escore agregado divide o dano pelo corpus
inteiro, então a margem observada é aproximadamente

```text
queda_no_alvo × (tarefas_no_alvo / tarefas_no_corpus)
```

`desiste-no-erro` é o caso mais nítido: ele destrói **100 %** das tarefas que ataca e mesmo
assim move o agregado em apenas 0,125, porque essas tarefas são 12,5 % do corpus. Um instrumento
lido pelo agregado chamaria isso de "respondente com 87,5 % de acerto".

Ou seja: **o escore agregado não é uma medida ruim de uma capacidade — é uma medida boa de
nada em particular.** É a mesma estrutura do [`CE-001`](../../../silicon-atlas/04_VALIDATION/COUNTEREXAMPLES/CE-001-lhs-nao-discrimina.md)
do Silicon Atlas, onde 70 % do peso do LHS era idêntico entre os candidatos e o líder vencia
por menos que o ruído dos próprios pesos. Lá o problema era peso inerte; aqui é massa inerte
de tarefas. O efeito é o mesmo: um número bem-comportado que não decide nada.

## O que **não** foi feito

Não se trocou a métrica de `F3`. O falsificador foi declarado sobre a margem agregada antes da
execução, e redefini-lo depois de vê-lo disparar seria ajustar o instrumento ao resultado — a
manobra proibida pelo [`D-008`](../../../silicon-atlas/00_GOVERNANCE/DECISION_LOG.md) do
Silicon Atlas. `C-102` fica **retratada** ([R-101](../../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)),
e o portão V3 fica bloqueado.

## Segundo achado, menor e também preservado

`plano-invertido` cai apenas 0,250 **dentro do próprio alvo**. Investigando: seu conjunto-alvo
é definido pelos modos declarados da tarefa (`FAIL_PLANNING`), que cobre 24 tarefas — as 6 de
ordem, as 12 de pergunta e 6 de numeracia. Inverter a ordem das chamadas só quebra as 6 de
ordem. O conjunto-alvo declarado é mais grosso que o que a sonda de fato ataca.

Registrado como `G-111`. Não invalida o diagnóstico principal: torna a coluna "queda no alvo"
um limite inferior, o que só reforça a conclusão.

## O que fecharia isto

1. **Escore por capacidade como criterio declarado** — em vez do agregado. Precisa ser
   declarado antes do ciclo C-003, com limiar próprio, sem olhar este resultado antes.
2. **Ponderação por família** — exige justificar o peso de cada capacidade, o que hoje é
   `A-104` e está aberto em `G-104`.
3. **Rotulagem por passo deformado** (`G-111`) — mede o alvo real de cada sonda.

Nenhuma das três é feita neste ciclo. `C-102` permanece retratada até uma delas existir com
critério declarado antes.
