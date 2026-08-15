---
artifact: REPRODUCIBILITY
cycle: C-002
---

# Reprodutibilidade

O portão A5 exige que o protótipo possa ser reproduzido **por outra pessoa**. Este documento é
o contrato dessa reprodução.

## Ambiente mínimo

- Python ≥ 3.11
- `numpy` ≥ 1.26, `pyyaml` ≥ 6.0, `pytest` ≥ 8.0
- Sem GPU, sem pesos de modelo, sem rede, sem `torch`

> **Nota de ambiente.** Em Python 3.14 de 32 bits no Windows, `pyyaml` 6.0.3 não tem *wheel*
> publicada e a instalação tenta compilar a extensão C, exigindo MSVC. Alternativas: usar um
> interpretador de 64 bits, ou instalar a versão pura-Python do `pyyaml`. Registrado aqui porque
> foi encontrado na prática ao reproduzir este repositório do zero.

## Reproduzir o ciclo inteiro

```bash
pip install -e ".[dev]"
python scripts/build_task_corpus.py
python -m pytest tests
python scripts/run_model_cycle.py
```

A segunda execução deve produzir arquivos **idênticos** à primeira, exceto `run_id` e
timestamps.

## Fontes de aleatoriedade

| Fonte | Semente | Onde |
|---|---|---|
| perturbação de pesos do CSS | `20260814` | `config/css_weights.v1.json` |

Nenhuma outra. O gerador de corpus, o ambiente, as sondas e os graders são inteiramente
determinísticos — não há RNG a semear.

## O que é entrada e o que é saída

Confundir os dois destrói a rastreabilidade.

| Entrada — edite | Saída — **não edite** |
|---|---|
| `scripts/build_task_corpus.py` (os templates) | `corpus/tasks/*.json` |
| `corpus/models/*.json` | `03_UNIFICATION/FAILURE_MAP.md` |
| `config/*.json` | `04_VALIDATION/EXPERIMENTS/X-002-RESULT.md` |
| `00_GOVERNANCE/CLAIM_LEDGER.yaml` (alegações e falsificadores) | `99_RELEASES/reports/*` |

O corpus de tarefas é **saída**. Editar um JSON à mão muda o benchmark de forma que ninguém
consegue auditar; mudar um template muda cem tarefas de forma que o diff mostra.

## Determinismo verificável

```bash
python scripts/build_task_corpus.py
sha256sum model-atlas/corpus/tasks/planning.json   # anote
python scripts/build_task_corpus.py
sha256sum model-atlas/corpus/tasks/planning.json   # deve ser igual
```

## Como derrubar este trabalho

Em ordem de custo crescente. Convite explícito, com o critério de refutação declarado.

| # | Ataque | O que cai se der certo |
|---|---|---|
| 1 | Conferir à mão o gabarito de dez tarefas contra o enunciado | `C-101` e, em `BRAB-NUM-*`, `G-109` |
| 2 | Escrever uma trajetória que erra só o argumento e ver se o rótulo é `FAIL_ARGUMENT` | a precisão de rótulo de `C-101` |
| 3 | Nomear um modo de falha real que a taxonomia não cobre | `C-104` e a cobertura declarada |
| 4 | Baixar uma ficha do Hub e comparar campo a campo | `A-101`, fecha `G-108` |
| 5 | Executar um modelo pequeno quantizado e comparar com o footprint calculado | `A-102`, fecha `G-102` |
| 6 | Correlacionar escore no corpus com desempenho em traços reais | `A-103`, fecha `G-107` — o mais caro e o mais importante |

## O que ainda impede reprodução independente completa

`G-110` — não houve revisão adversarial externa. Autor, revisor e autor das sondas que testam o
revisor são o mesmo agente. O portão V3 permanece **fechado** por esse motivo e por `F3`.
