---
artifact: TRADEOFFS
cycle: C-001
date: 2026-08-04
---

# Trade-offs da redução

Toda redução compra algo e paga algo. Este documento registra o preço de cada uma, para que a
decisão possa ser revertida com conhecimento de causa e não por preferência.

## Regra que governa todos eles

> **Cada camada adicional de modelagem acrescenta premissas e rebaixa o status máximo do
> resultado.**

Não é metáfora: é o comportamento de `Finding.derive()`. Complexidade custa confiança, e o custo
é computável.

| Camada | Premissas acrescentadas | Status máximo alcançável |
|---|---|---|
| IR + contagem de parâmetros | A-001 | `COMPUTATIONAL_EVIDENCE` |
| + roofline | A-002, A-005 | `CONDITIONAL_RESULT` (G-003) |
| + quantização | A-004 | `CONDITIONAL_RESULT` (G-002) |
| + LHS/SRS | — (mas pesos não calibrados) | `CONDITIONAL_RESULT` (G-011) |
| + PPA e economia | A-003, A-006, A-008 | `CONDITIONAL_RESULT` (G-004, G-005, G-007) |

## T-001 — IR analítica em vez de traçada

**Compra**: execução sem GPU, sem pesos, sem `torch`; assessment antes de NDA; verificação barata
contra contagem publicada; zero risco de vazamento de pesos.

**Paga**: não captura fusões de kernel, reordenações de grafo nem operadores fora do template da
família. Toda conclusão herda `A-001`.

**Ponto de virada**: se a divergência contra um grafo traçado exceder 10 % em qualquer classe com
mais de 5 % do custo, o trade-off se inverte. Ver ADR-0001.

## T-002 — Roofline sem sobreposição entre nós

**Compra**: modelo com uma linha de aritmética por nó, auditável e sem parâmetro ajustável.

**Paga**: superestima o tempo total, porque hardware real sobrepõe computação e movimentação. O
erro é sistemático e na direção conservadora — o que é aceitável para decisão de investimento e
inaceitável para dimensionamento fino.

**Consequência declarada**: o modelo acerta o **regime** (memory-bound vs compute-bound) com mais
confiança do que o valor absoluto. Os relatórios afirmam apenas o regime.

## T-003 — Atenção com tiling (scores não materializados)

**Compra**: representa a prática atual de inferência; evita explodir o tráfego em prefill longo.

**Paga**: um alvo que materialize scores seria mal modelado por ordens de grandeza. A premissa
está no atributo `materialize_scores` de cada nó, e pode ser ligada por caso.

## T-004 — Prior de quantização em vez de medição

**Compra**: o pipeline roda sem pesos e sem orçamento de avaliação; a estrutura da decisão fica
pronta antes da evidência cara.

**Paga**: `G-002`, a lacuna mais cara do projeto. O ganho estimado (bytes, tempo) é aritmética
exata; a perda estimada (qualidade) é **não medida**. O código separa os dois e recusa combiná-los
num único número de benefício.

**Por que não foi combinado**: um "score de benefício líquido" misturando aritmética exata com
prior de literatura pareceria mais decidível do que é. Seria o cherry-picking que a auditoria
adversarial procura.

## T-005 — Score composto (LHS/SRS) em vez de participação de custo bruta

**Compra**: uma única grandeza comparável entre casos, com fatores explícitos e auditáveis.

**Paga**: [CE-001](../04_VALIDATION/COUNTEREXAMPLES/CE-001-lhs-nao-discrimina.md) — dentro de um
modelo, 70 % do peso está em fatores idênticos entre candidatos, e a margem do líder fica abaixo
do ruído dos próprios pesos.

**Estado**: o trade-off **não compensou** no uso intra-modelo. A participação de custo bruta
decide melhor e com menos premissas. O LHS permanece útil apenas entre casos.

**Correção rejeitada**: reponderar até estabilizar. Ajustaria o instrumento ao resultado.

## T-006 — Monte Carlo em vez de ponto único

**Compra**: a incerteza fica visível, a decomposição de sensibilidade vira plano de pesquisa, e a
métrica de decisão passa a ser `P(amortizar antes da obsolescência)` — a pergunta real.

**Paga**: cada premissa econômica precisa declarar uma distribuição, não um valor; e o resultado
é mais difícil de vender que um número redondo.

**Aceito deliberadamente**: o produto vende auditabilidade. Um número redondo que o cliente leva
ao comitê como se fosse medição é o dano que o projeto existe para evitar.

## T-007 — Corpus transcrito em vez de baixado

**Compra**: ciclo executável offline, sem depender de rede nem de disponibilidade de repositório.

**Paga**: `G-008`. Mitigado pela verificação indireta: os 9 modelos batem a contagem publicada ao
parâmetro, o que um campo transcrito errado quebraria.

**Residual**: um erro que se cancelasse entre dois campos passaria. `atlas registry verify` fecha.

## T-008 — Expandir todas as camadas do grafo

**Compra**: hotspots por camada, janelas alternadas (Gemma-2) e diffs posicionais ficam explícitos.

**Paga**: 644 a 971 nós por modelo em vez de ~20. Irrelevante nesta escala (segundos por ciclo),
relevante se o corpus crescer para milhares de modelos ou se a IR passar a carregar tensores.

## O trade-off que não foi feito

Não foi trocada **honestidade por vendabilidade** em nenhum ponto. Os relatórios do ciclo C-001
concluem, nos 9 modelos, que não há caso para máscara — e essa conclusão foi emitida como está.
O sistema que recomendasse fabricar seria mais fácil de vender e destruiria o único ativo que o
produto tem.
