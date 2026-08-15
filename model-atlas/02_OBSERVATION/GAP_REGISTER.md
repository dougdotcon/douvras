---
artifact: GAP_REGISTER
cycle: C-002
date: 2026-08-14
---

# Registro de lacunas — Model Atlas

Lacuna aberta não impede o ciclo — impede que o resultado seja promovido acima de
`CONDITIONAL_RESULT`. Ver [STATUS_POLICY](../../00_GOVERNANCE/STATUS_POLICY.md).

A numeração começa em `G-101` para não colidir com o `GAP_REGISTER` do Silicon Atlas, que
ocupa `G-001`..`G-014`. Os dois eixos compartilham o core, não o registro de lacunas: uma
lacuna é sempre lacuna *de alguma coisa*.

| Gap | Por que importa | Evidência necessária | Bloqueia | Status |
|---|---|---|---|---|
| G-101 | Nenhum modelo real foi executado: todas as capacidades são ausência declarada | Pesos locais + suíte executada com o extra `[run]` | qualquer afirmação sobre capacidade de modelo; CSS | OPEN |
| G-102 | Sem telemetria: TTFT, tokens/s e RAM de pico não foram observados | Execução instrumentada em quantização declarada | recomendação de quantização operacional | OPEN |
| G-103 | Precision cliff não medido: a coluna Qualidade da tabela de quantização está vazia | Perplexidade ou escore de capacidade por precisão, na mesma suíte | escolha de quantização; fecha junto com G-101 | OPEN |
| G-104 | Priors de capacidade (tratabilidade, valor, custo, estabilidade) nunca calibrados | Três casos com desfecho conhecido: medir, construir dataset, medir de novo | fator do CSS; qualquer alvo de especialização | OPEN |
| G-105 | O limiar de discriminação de 0,20 do `F3` não tem base empírica | Replicação contra benchmarks públicos de agente com desfecho conhecido | veredicto de `F3`; portão V3 | OPEN |
| G-106 | Dificuldade das tarefas é declarada por autoria, não calibrada por desempenho | Curva de acerto por dificuldade com ao menos três modelos reais | qualquer leitura de "tarefa difícil" | OPEN |
| G-107 | O corpus é sintético: nenhuma tarefa veio de tráfego real de agente em produção | Traços de workload de cliente, anonimizados | validade externa do benchmark inteiro | OPEN |
| G-108 | Fichas do corpus de modelos foram transcritas de documento secundário, não da fonte | `matlas registry verify` contra o Hub, com revisão fixada | `A-101`; todo número derivado de contagem de parâmetros | OPEN |
| G-109 | O alvo do subconjunto ótimo das tarefas de numeracia é calculado pelo mesmo autor do grader | Verificação independente do ótimo declarado em amostra | tarefas `BRAB-NUM-*` | OPEN |
| G-110 | Sem revisão adversarial externa (§6.7): autor e auditor são o mesmo agente | Revisão por pessoa que não construiu o artefato | Portão V3 | OPEN |
| G-111 | O conjunto-alvo de cada sonda é definido pelos modos declarados da tarefa, mais grosso que o que a sonda de fato ataca | Rotular por passo deformado, não por modo declarado | leitura de `probe_sensitivity`; diagnóstico de `CE-101` | OPEN |

## Dívida de evidência (§6.3)

| Decisão | Evidência atual | Risco | Evidência pendente | Data limite |
|---|---|---|---|---|
| Corpus sintético gerado por template | A-103 | **Alto**: mede o gerador, não o mundo | G-107 | ciclo C-003 |
| Priors de capacidade fixos | A-104 | **Alto**: entram direto no alvo de dataset | G-104 | ciclo C-003 |
| Contagem de parâmetros aproximada | A-101 | Médio: desloca o orçamento de memória | G-108 | ciclo C-003 |
| Bytes por parâmetro por quantização | A-102 | Médio: desloca o "cabe?" | G-102 | ciclo C-003 |
| Limiar de discriminação de 0,20 | A-105 | **Alto**: decide o veredicto de F3 | G-105 | ciclo C-003 |
