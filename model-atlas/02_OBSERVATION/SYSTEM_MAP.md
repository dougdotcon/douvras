---
artifact: SYSTEM_MAP
cycle: C-002
date: 2026-08-14
---

# Mapa do sistema

Descrição do sistema **antes** de tentar explicá-lo. Linguagem descritiva, sem hipótese.

## O que é observado

Um agente de LLM em turno curto executando uma tarefa com ferramentas nomeadas. O objeto de
observação não é o texto que o modelo produz — é a **sequência de ações** que ele toma e o que
o ambiente devolve a cada uma.

```text
enunciado + ferramentas
        │
        ▼
   respondente  ──propõe──►  passo (chamada | pergunta | resposta | desistência)
        ▲                          │
        │                          ▼
        └──observação──────    ambiente determinístico
                                   │
                                   ▼
                             trajetória completa
                                   │
                                   ▼
                        grader (regra declarada)
                                   │
                                   ▼
                     veredicto rotulado por modo de falha
```

## Onde o custo está, na operação real deste laboratório

| Etapa | Custo dominante | Precisa de GPU? |
|---|---|---|
| escrever templates de tarefa | tempo de autoria | não |
| gerar o corpus | segundos de CPU | não |
| verificar o instrumento | segundos de CPU | não |
| executar um modelo pequeno quantizado | minutos a horas de CPU | não, mas é o gargalo |
| treinar adapter LoRA | horas de GPU | sim |

O ciclo C-002 cobre as três primeiras linhas inteiras. A quarta está travada por `G-101` e é a
próxima fronteira; a quinta está fora do escopo do eixo.

## Estados que o ambiente pode assumir

Seis tipos de ferramenta, escolhidos por serem os que aparecem nas famílias de tarefa do
Documento 1: `read`, `lookup`, `debit`, `write`, `ack`, `error`. `error` aceita `recover_after`,
o que torna "falha transitória" e "falha permanente" dois ambientes distintos — e portanto
"tentar de novo" e "desistir explicitamente" duas respostas corretas diferentes.

## O que muda entre modelos, e o que não muda

| Não muda | Muda |
|---|---|
| o corpus de tarefas | a trajetória produzida |
| o ambiente e suas observações | os modos de falha disparados |
| a regra de acerto | o escore por capacidade |
| a taxonomia de falhas | a distribuição dentro dela |

Essa separação é o que permite comparar modelos sem reescrever nada — e é também o que torna o
corpus um ativo, no sentido do Documento 1: o código que o gerou pode ser descartado; o corpus
e os vereditos que ele produz, não.

## O que este mapa deliberadamente não cobre

Diálogo multi-turno com estado implícito, ferramentas cujo efeito depende de tempo real,
concorrência entre agentes, e qualquer tarefa cuja resposta correta seja questão de julgamento.
Todas existem em produção; nenhuma é observável por este instrumento.
