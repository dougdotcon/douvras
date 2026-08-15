---
artifact: DECISION_LOG
policy: append-only
---

# Registro de decisões — Model Atlas

Decisões arquiteturais detalhadas ficam em [ADRs](../06_ARCHITECTURE/ADR/); aqui fica o que não
cabe num ADR. Decisões de nível DOUVRAS, que valem para os dois eixos, ficam no
[DECISION_LOG da raiz](../../00_GOVERNANCE/DECISION_LOG.md).

| # | Data | Decisão | Justificativa | Reversível por |
|---|---|---|---|---|
| D-101 | 2026-08-14 | O corpus de tarefas é saída de gerador, não arquivo editado | Trocar um valor no template muda cem tarefas de forma auditável; editar cem JSONs não | necessidade de tarefas idiossincráticas que nenhum template cobre |
| D-102 | 2026-08-14 | O ambiente é executado, não descrito | Sem isso, quem inventa o saldo e quem consulta o saldo produzem o mesmo registro, e alucinação vira invisível | — |
| D-103 | 2026-08-14 | O veredicto é rotulado por modo de falha, não binário | `passed=False` não informa nada acionável; `FAIL_ARGUMENT` e `FAIL_RECOVERY` pedem datasets diferentes | — |
| D-104 | 2026-08-14 | A regra de acerto mora no JSON da tarefa, não em código por tarefa | Mil tarefas com grader imperativo próprio são mil oportunidades de o critério divergir do que o benchmark afirma medir | regra que nenhuma combinação declarativa expresse |
| D-105 | 2026-08-14 | Cada sonda declara o modo que promete disparar **antes** da execução | É a predição que torna `F6` falsificável em vez de descritivo | — |
| D-106 | 2026-08-14 | Manter `C-102` retratada em vez de trocar a métrica de `F3` | Redefinir o falsificador depois de vê-lo disparar é ajustar o instrumento ao resultado — mesmo motivo do `D-008` do Silicon Atlas | critério por capacidade **declarado antes** do ciclo C-003 |
| D-107 | 2026-08-14 | `probe_sensitivity` entra como diagnóstico, explicitamente não-critério | O diagnóstico é necessário para entender `CE-101`; promovê-lo a critério no mesmo ciclo em que `F3` disparou seria a manobra que `D-106` recusa | declaração prévia em C-003 |
| D-108 | 2026-08-14 | Campos que a fonte não afirma ficam nulos no corpus de modelos | `context_len` e `license` plausíveis seriam proveniência inventada, e proveniência inventada é pior que ausente | `matlas registry verify` |
| D-109 | 2026-08-14 | O CSS é implementado e exercitado sob teste mesmo sem entrada real | O `G-014` do Silicon Atlas mostrou que um caminho nunca executado atravessa um ciclo inteiro com a suíte verde | — |

## Decisões deliberadamente adiadas

| Adiada | Por quê | Reabrir quando |
|---|---|---|
| Integração com LightEval | O executor próprio é 200 linhas e o acoplamento cobra caro antes de haver modelo rodando | primeira execução real estabilizar |
| Escore ponderado por capacidade | Exige justificar o peso de cada uma, o que hoje é `A-104` e está aberto em `G-104` | `G-104` fechar |
| Treino de adapter LoRA | Fora do eixo: o Model Atlas mede, não treina | primeiro alvo de dataset decidido com critério que discrimine |
| Leaderboard público | Publicar ranking com escore cujo critério de discriminação foi reprovado seria o oposto do produto | `F3` deixar de disparar sob critério declarado antes |
