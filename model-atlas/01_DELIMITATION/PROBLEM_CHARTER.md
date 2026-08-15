---
artifact: PROBLEM_CHARTER
cycle: C-002
date: 2026-08-14
gate: D0
---

# Carta do problema — DOUVRAS Model Atlas

Escrita **antes** da execução do ciclo. Os critérios de falha desta carta são avaliados por
código em `model_atlas.instrument`, não por leitura.

## Pergunta principal

> **Um benchmark de agentes em português brasileiro consegue medir, com rótulo acionável, em
> qual capacidade um modelo pequeno falha — e o instrumento que faz essa medida pode ser
> verificado antes de existir qualquer modelo para medir?**

A segunda metade da pergunta é a que este ciclo responde. A primeira depende de pesos locais e
está travada por `G-101`.

## Usuário, sistema ou fenômeno afetado

Quem precisa decidir onde investir esforço de dados: um laboratório independente com CPU e
16 GB de RAM, e uma empresa que já opera um agente e não sabe onde ele quebra. Os dois recebem
hoje a mesma coisa do mercado — um número agregado que não diz o que fazer na segunda-feira.

## Estado atual

Benchmarks de agente publicam escore agregado. Escore agregado não distingue *escolheu a
ferramenta errada* de *escolheu a certa e errou o argumento*, e as duas correções são datasets
diferentes. Pior: quase nenhum benchmark publica evidência de que o próprio grader aceita o
gabarito e rejeita o erro pelo motivo certo.

## Estado desejado

Um instrumento cuja acurácia é medida antes de ele medir alguém, com falha rotulada por
capacidade, ambiente executado (não descrito) e resultado reproduzível byte a byte.

## Restrições

- **R1** — o caminho principal roda sem GPU, sem pesos de modelo e sem rede (ADR-0006).
- **R2** — nenhuma afirmação sobre modelo pode nascer de execução sintética (ADR-0007).
- **R3** — o corpus de tarefas é saída de gerador determinístico, não arquivo editado à mão.
- **R4** — arquitetura de cliente e trajetórias privadas não saem da máquina.

## Não objetivos

- **Não** é objetivo deste ciclo produzir ranking de modelos.
- **Não** é objetivo treinar, ajustar ou quantizar qualquer modelo.
- **Não** é objetivo cobrir o espaço de falhas reais de agentes em produção — o corpus cobre
  os modos **declarados**, que é coisa diferente e menor.
- **Não** é objetivo substituir avaliação humana de qualidade de resposta.

## Baseline congelado

`BASELINE-2026-08-14`: 96 tarefas em 8 capacidades, 132 contraexemplos rotulados, 8 sondas de
calibração, priors de capacidade `v1` e pesos de CSS `v1`. Alterar qualquer um exige nova
comparação e entrada no `DECISION_LOG`.

## Métricas de sucesso

| # | Métrica | Alvo declarado |
|---|---|---|
| M1 | aceitação do gabarito | 100 % |
| M2 | rejeição de contraexemplo | 100 % |
| M3 | precisão do rótulo | 100 % |
| M4 | determinismo entre execuções | idêntico |
| M5 | cobertura mínima por capacidade | ≥ 8 tarefas |

## Critérios de falha

Declarados antes da execução (Método §6.1). Cada um é uma função em
`InstrumentReport.falsifiers()`.

| # | Critério | Consequência se disparar |
|---|---|---|
| **F1** | o grader aceita alguma trajetória declarada como errada | o benchmark não mede o que afirma; nenhum escore pode ser publicado |
| **F2** | o grader rejeita a trajetória de referência de alguma tarefa | o critério de acerto contradiz o próprio exemplo de acerto |
| **F3** | o escore separa o oráculo da melhor sonda degenerada por menos de 0,20 | o escore agregado não decide nada; `C-102` é retratada |
| **F4** | duas execuções da mesma suíte produzem resultados diferentes | o resultado não é auditável |
| **F5** | alguma tarefa não é avaliável, ou alguma capacidade tem menos de 8 tarefas | a cobertura declarada é falsa |
| **F6** | algum modo de falha declarado nunca é disparado por nenhuma sonda | a taxonomia tem célula morta |

O limiar de `F3` (0,20) **não tem base empírica** e está registrado como `G-105`. É a primeira
coisa que um revisor externo deveria atacar.

## Decisão que o estudo deverá permitir

Se vale investir tempo em construir dataset dirigido a uma capacidade específica — e, antes
disso, se o instrumento que vai medir o ganho é confiável o bastante para que o ganho medido
signifique alguma coisa.
