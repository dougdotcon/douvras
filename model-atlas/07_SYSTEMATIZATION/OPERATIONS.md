---
artifact: OPERATIONS
cycle: C-002
gate: S6
---

# Operação

## O ciclo é uma execução, não um projeto

```bash
python scripts/run_model_cycle.py
```

Regenera o mapa de falhas, o resultado do experimento, os assessments e a evidência no claim
ledger. Roda em segundos sobre o corpus inteiro. Um ciclo que exige uma semana de trabalho
manual não é executado — e um que não é executado não produz memória.

## Rotina de entrada de modelo novo no corpus

Ver [RB-101](RUNBOOKS/RB-101-novo-modelo-no-corpus.md).

## Rotina de mudança no corpus de tarefas

O corpus é saída. A sequência correta é:

```bash
# 1. editar o TEMPLATE em scripts/build_task_corpus.py, nunca o JSON
# 2. regerar
python scripts/build_task_corpus.py
# 3. o gabarito ainda passa? o contraexemplo ainda falha pelo motivo certo?
PYTHONPATH=src python -m model_atlas.cli instrument
# 4. ciclo completo
python scripts/run_model_cycle.py
```

O que se observa, nessa ordem:

1. **`F1` ou `F2` passou a disparar?** A regra e o exemplo divergiram. Pare aqui.
2. **Alguma capacidade caiu abaixo de 8 tarefas?** `F5` dispara e a cobertura declarada virou
   falsa.
3. **Algum modo ficou sem sonda?** `F6` dispara: a taxonomia ganhou célula morta.
4. **O baseline mudou?** Se sim, congele um novo e registre no `DECISION_LOG` — senão a próxima
   comparação entre ciclos não significa nada.

## Política de status em operação

Promover status é **decisão humana registrada**, nunca efeito colateral de execução.
`ClaimLedger.record_run` anexa evidência e pode retratar, mas jamais promove.

Para promover:

1. fechar a lacuna correspondente no `GAP_REGISTER` com evidência anexada;
2. registrar a decisão no `DECISION_LOG`;
3. editar o status no `CLAIM_LEDGER`;
4. reexecutar o ciclo e confirmar que os relatórios refletem o novo status.

## Critérios de encerramento (Método §6.4)

O eixo de capacidade é encerrado se, após três ciclos:

- o instrumento não discriminar em nenhum recorte declarado antes; **ou**
- nenhum modelo do corpus for executável na máquina de referência; **ou**
- o escore no corpus não correlacionar com desempenho em traços reais quando `G-107` fechar;
  **ou**
- nenhuma capacidade apresentar déficit que um dataset de porte viável consiga mover.

Encerrar por critério pré-definido é governança, não fracasso. Nesse cenário o trabalho
sobrevive como corpus público e como o Failure Atlas — que são úteis mesmo sem a camada de
score.

## Estado dos portões

```bash
PYTHONPATH=src python -m model_atlas.cli gates
```

| Portão | Estado ao fim de C-002 | O que falta |
|---|---|---|
| D0 — identidade do problema | **aberto** | — |
| O1 — cobertura observacional | **aberto** | — |
| U2 — estrutura candidata | **aberto** | — |
| V3 — sobrevivência mínima | **fechado** | `F3` disparado (`CE-101`) e revisão externa (`G-110`) |
| R4 — estrutura mínima operável | **aberto** | — |
| A5 — protótipo verificável | **aberto** | — |
| S6 — operação cumulativa | **aberto** | — |

## Riscos operacionais monitorados

| Risco | Sinal de alerta | Ação |
|---|---|---|
| Corpus editado à mão | `corpus/tasks/*.json` mudou sem `build_task_corpus.py` mudar | regerar e conferir o diff |
| Sonda ajustada para caber no grader | `runner.PROBES` mudou junto com `graders.py` no mesmo commit | revisar: sonda existe para atacar, não para concordar |
| Número sintético virando resultado | qualquer `Finding` de capacidade com `value` não nulo sem pesos locais | `ADR-0007`; o portão de emissão recusa |
| Limiar afrouxado sob pressão | `MIN_DISCRIMINATION_MARGIN` alterado | é a manobra mais provável depois de `F3` disparar; exige `DECISION_LOG` |
