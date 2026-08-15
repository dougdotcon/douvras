---
artifact: OBSERVABILITY
cycle: C-002
---

# Observabilidade

O que se mede a cada ciclo para saber se o projeto está progredindo ou apenas acumulando
modelagem.

## Dívida de evidência (Método §6.3)

Fração dos resultados apoiados em premissa não demonstrada. Medida, não estimada — sai de
`FindingSet.evidence_debt()`.

Se a dívida **subir** entre ciclos, o sistema está acumulando modelagem mais rápido que
evidência. É o modo de falha mais provável deste tipo de projeto e o mais difícil de perceber
de dentro, porque cada passo isolado parece progresso.

## Distribuição de status dos `Finding` emitidos

Um assessment do ciclo C-002 emite predominantemente `OPEN_GAP` — por construção, já que
nenhuma capacidade foi medida. Isso **não** é sinal de fraqueza do sistema: é a diferença entre
declarar honestamente o que falta e preencher com número plausível.

O sinal a vigiar é o oposto: um ciclo em que a fração de `OPEN_GAP` caia sem que nenhuma lacuna
do `GAP_REGISTER` tenha sido fechada significa que algum motor passou a emitir número onde antes
declarava ausência.

## Indicadores do instrumento

| Indicador | Alvo | O que significa cair |
|---|---|---|
| aceitação do gabarito | 1,000 | a regra e o próprio exemplo de acerto divergiram |
| rejeição de contraexemplo | 1,000 | o grader deixa passar erro conhecido |
| precisão do rótulo | 1,000 | reprova pelo motivo errado — manda construir o dataset errado |
| modos sem sonda | vazio | a taxonomia ganhou célula morta |
| determinismo | idêntico | o resultado deixou de ser auditável |

## Indicadores de cobertura

| Indicador | Alvo |
|---|---|
| tarefas por capacidade | ≥ 8 |
| contraexemplos por tarefa | ≥ 1 |
| fichas de modelo verificadas no upstream | hoje 0/3 — `G-108` |
| modelos com pesos locais | hoje 0/3 — `G-101` |

Os dois últimos são os números que devem envergonhar o próximo ciclo até subirem.

## Portões

`matlas gates` a cada execução. Um portão que passa de aberto para fechado entre ciclos é
evento, não estatística: exige entrada no `DECISION_LOG`.
