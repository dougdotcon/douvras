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
