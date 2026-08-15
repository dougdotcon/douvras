---
artifact: STATUS_POLICY
version: 1.0
date: 2026-08-03
enforced_by: src/silicon_atlas/status.py
---

# Política de Status

## Regra principal

> **Nenhuma afirmação sem classificação de status.**

Nesta base de código a regra é **executável**, não editorial: todo número que sai de um motor de
análise é um `Finding`, e `Finding` não pode ser construído sem `status`. Ver
[status.py](../src/silicon_atlas/status.py).

## Escala de status

Ordenada por força epistêmica crescente. `Status.rank` implementa a ordem, e o valor inteiro do
enum **é** a força — por isso `min()` sobre um conjunto de status devolve o elo mais fraco, que é
exatamente a regra de propagação.

> A ordem abaixo é normativa e é verificada por teste contra `status.py`. O Método §3.1 lista os
> status sem declarar ordenação; a ordenação é decisão deste projeto, registrada aqui.

| # | Status | Valor | Significado | Pode sustentar decisão de tape-out? |
|---|---|---|---|---|
| 0 | `RETRACTED` | 0 | Retirado após erro ou evidência contrária | nunca |
| 1 | `OPEN_GAP` | 10 | Dependência não resolvida | não |
| 2 | `ANALOGY` | 20 | Semelhança útil, sem força de prova | não |
| 3 | `ASSUMPTION` | 30 | Premissa usada, não demonstrada | não |
| 4 | `CONJECTURE` | 35 | Plausível, não demonstrada | não |
| 5 | `DEFINITION` | 40 | Convenção adotada | n/a |
| 6 | `HYPOTHESIS` | 50 | Testável, com falsificadores declarados | não |
| 7 | `MODEL` | 55 | Representação formal do sistema | não isoladamente |
| 8 | `COMPUTATIONAL_EVIDENCE` | 60 | Saída de código sob condições declaradas | parcial |
| 9 | `PARTIAL_RESULT` | 65 | Válido em escopo limitado | parcial |
| 10 | `CONDITIONAL_RESULT` | 70 | Válido se hipóteses declaradas valerem | parcial |
| 11 | `OBSERVATION` | 75 | Medido no sistema real, sem interpretação causal | parcial |
| 12 | `EXPERIMENTAL_EVIDENCE` | 85 | Empírico, com protocolo documentado | sim |
| 13 | `ENGINEERING_DECISION` | 90 | Escolha de projeto sob trade-off | sim |
| 14 | `EXTERNALLY_VERIFIED` | 100 | Reproduzido por terceiro independente | sim |

**Por que `OBSERVATION` fica acima de `COMPUTATIONAL_EVIDENCE`**: uma medição do sistema real diz
mais sobre o sistema real do que a saída de um modelo dele, por melhor que o modelo seja. Este
projeto opera quase inteiramente abaixo dessa linha, e a ordem existe para tornar isso visível.

`CONDITIONAL_HYPOTHESIS`, usado no Método §9.1 para o ganho de 100×, **não é um status do enum**:
é a combinação de `HYPOTHESIS` com uma lista de qualificadores obrigatórios, registrada em
`CLAIM_LEDGER:C-004` no campo `required_qualifiers`. Os rótulos de §9.1
(`SUPPORTED_ENGINEERING_PRINCIPLE`, `OBSERVED_IN_INDUSTRY_DEMO`, `OVERGENERALIZATION`,
`UNSUPPORTED`) são classificações de uma tese externa naquela seção, não estados do ciclo de vida
de uma alegação deste repositório.

## Regra de propagação

> **Uma conclusão não pode ter status mais forte que a mais fraca de suas dependências.**

Implementada em `Finding.derive()`. Um break-even calculado sobre uma premissa `ASSUMPTION`
sai como `CONDITIONAL_RESULT` no máximo — nunca como `EXPERIMENTAL_EVIDENCE`. Tentar promover
levanta `StatusViolation`.

## Vocabulário proibido (§3.2 do Método)

`resolvido` · `provado` · `100% completo` · `revolucionário` · `universal` · `garantido` · `N× melhor` sem objeto/métrica/baseline/ambiente/intervalo/tipo de evidência. <!-- lint:allow -->

A linha acima carrega o marcador `<!-- lint:allow -->`: a política precisa **citar** os termos que
proíbe, e um verificador incapaz de descrever a si mesmo seria inutilizável. O marcador é a única
forma de isenção, é explícito no texto e aparece no `git diff` de quem o usar.

O verificador `atlas lint <caminho>` varre relatórios gerados e artefatos Markdown em busca desses
termos e sai com código 1 quando encontra um deles sem qualificação adjacente.

## Portão de emissão

Nenhum relatório é emitido sem as seções obrigatórias (§3.3):
pergunta principal · afirmação principal · hipóteses numeradas · dependências · critérios de falha ·
resultados · limitações · **o que este resultado não demonstra**.

[`assessment.Assessment.render()`](../src/silicon_atlas/assessment.py) recusa emitir se qualquer
uma faltar, se a análise de sensibilidade não tiver sido executada, se o texto contiver vocabulário
proibido, ou se algum `Finding` numérico for não-finito.

A última condição foi acrescentada depois que um `NaN` atravessou o pipeline até a afirmação
principal de quatro relatórios ([R-003](RETRACTIONS_AND_CORRECTIONS.md)). O portão vigia o
contrato; não vigiava a **aritmética** do que passava por ele.
