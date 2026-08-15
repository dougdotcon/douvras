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
