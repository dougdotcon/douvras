---
artifact: EXPERIMENT_RESULT
id: X-002
run_id: 20260815T024411Z
generated_by: scripts/run_model_cycle.py
cycle: C-002
---

# X-002 — resultado

> Arquivo **gerado**. O protocolo esta em [X-002.md](X-002.md) e foi escrito antes.

## Medidas

| Símbolo | Medida | Valor | Alvo |
|---|---|---:|---:|
| M1 | aceitacao do gabarito | 1.000 | 1,000 |
| M2 | rejeicao de contraexemplo | 1.000 | 1,000 |
| M3 | precisao do rotulo | 1.000 | 1,000 |
| M4 | determinismo | identico | identico |
| M5 | cobertura minima por capacidade | 12 | ≥ 8 |
| M6 | margem de discriminacao agregada | 0.062 | ≥ 0,200 |
| M7 | modos sem sonda | 0 | 0 |

## Falsificadores

| # | Criterio | Estado | Medido |
|---|---|---|---|
| F1 | o grader aceita alguma trajetoria declarada como errada | nao disparado | `1.0` |
| F2 | o grader rejeita a trajetoria de referencia de alguma tarefa | nao disparado | `1.0` |
| F3 | o escore separa o oraculo da melhor sonda degenerada por menos de 0.20 | **DISPARADO** | `0.0625` |
| F4 | duas execucoes da mesma suite produzem resultados diferentes | nao disparado | `True` |
| F5 | alguma tarefa nao e avaliavel, ou alguma capacidade tem menos de 8 tarefas | nao disparado | `{'sem_grader': [], 'cobertura_fina': []}` |
| F6 | algum modo de falha declarado nunca e disparado por nenhuma sonda | nao disparado | `[]` |

## Sondas: prometido contra observado

A promessa de cada sonda foi declarada em `runner.PROBES` antes da execucao.

| Sonda | Escore | Prometido | Cumpriu | Observado |
|---|---:|---|:---:|---|
| `oraculo` | 1.000 | — | sim | — |
| `resposta-direta` | 0.000 | `FAIL_TOOL_SELECTION` | sim | `FAIL_FORMAT`, `FAIL_HALLUCINATION`, `FAIL_PLANNING`, `FAIL_RECOVERY`, `FAIL_SAFETY`, `FAIL_TOOL_SELECTION` |
| `ferramenta-errada` | 0.438 | `FAIL_TOOL_SELECTION` | sim | `FAIL_HALLUCINATION`, `FAIL_PLANNING`, `FAIL_SAFETY`, `FAIL_TOOL_SELECTION` |
| `argumento-errado` | 0.688 | `FAIL_ARGUMENT` | sim | `FAIL_ARGUMENT`, `FAIL_PLANNING` |
| `json-quebrado` | 0.688 | `FAIL_FORMAT` | sim | `FAIL_FORMAT`, `FAIL_RECOVERY`, `FAIL_SAFETY` |
| `desiste-no-erro` | 0.875 | `FAIL_RECOVERY` | sim | `FAIL_RECOVERY` |
| `impulsivo` | 0.562 | `FAIL_PLANNING` | sim | `FAIL_FORMAT`, `FAIL_PLANNING`, `FAIL_RECOVERY`, `FAIL_SAFETY` |
| `plano-invertido` | 0.938 | `FAIL_PLANNING` | sim | `FAIL_PLANNING` |

## Sensibilidade por sonda

Diagnostico de [CE-101](../COUNTEREXAMPLES/CE-101-margem-agregada-diluida.md), **nao**
criterio: `F3` foi declarado sobre a margem agregada e permanece como estava.

| Sonda | Tarefas no alvo | % do corpus | Queda no alvo | Queda agregada |
|---|---:|---:|---:|---:|
| `resposta-direta` | 36 | 37.5% | 1.000 | 1.000 |
| `argumento-errado` | 30 | 31.2% | 1.000 | 0.312 |
| `json-quebrado` | 12 | 12.5% | 1.000 | 0.312 |
| `desiste-no-erro` | 12 | 12.5% | 1.000 | 0.125 |
| `ferramenta-errada` | 36 | 37.5% | 0.667 | 0.562 |
| `impulsivo` | 24 | 25.0% | 0.250 | 0.438 |
| `plano-invertido` | 24 | 25.0% | 0.250 | 0.062 |

## Interpretacao

**1 de 6 falsificadores dispararam** (F3).

O escore agregado nao separa respondente correto de degenerado pela margem
declarada. `C-102` foi retratada em
[R-101](../../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) e o portao V3 esta
bloqueado. A metrica **nao** foi trocada: redefinir um falsificador depois de
ve-lo disparar seria ajustar o instrumento ao resultado.

O que sobrevive: o grader aceita todo gabarito, rejeita todo contraexemplo com o
rotulo correto, a suite e deterministica e nenhum modo declarado ficou sem sonda.
Sao afirmacoes sobre **o instrumento**, e e tudo o que este ciclo autoriza dizer.

## Interpretacao proibida

Qualquer frase sobre a capacidade de qualquer modelo. Nenhum modelo foi executado.
