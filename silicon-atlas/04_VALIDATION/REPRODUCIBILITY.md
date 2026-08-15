---
artifact: REPRODUCIBILITY
cycle: C-001
---

# Reprodutibilidade

O portão A5 exige que o protótipo possa ser reproduzido **por outra pessoa** (Método §4.6).
Este documento é o contrato dessa reprodução.

## Ambiente mínimo

- Python ≥ 3.11 (desenvolvido em 3.14)
- `numpy` ≥ 1.26, `pyyaml` ≥ 6.0, `pytest` ≥ 8.0
- Sem GPU, sem pesos de modelo, sem rede, sem `torch`

## Reproduzir o ciclo inteiro

```bash
pip install -e ".[dev]"
python -m pytest tests -q
python scripts/run_cycle.py
```

A segunda execução deve produzir arquivos **idênticos** aos da primeira, exceto `run_id` e
timestamps. Toda fonte de aleatoriedade tem semente fixa e versionada:

| Fonte | Semente | Onde |
|---|---|---|
| perturbação de pesos (sensibilidade) | `20260803` | `config/readiness_weights.v1.json` |
| Monte Carlo econômico | `20260803` | `config/economics_priors.v1.json` |

Nenhum outro uso de aleatoriedade existe no caminho principal.

## O que é entrada e o que é saída

Confundir os dois destrói a rastreabilidade.

| Entrada — edite | Saída — **não edite** |
|---|---|
| `corpus/models/*.json` | `03_UNIFICATION/INVARIANT_MAP.md` |
| `config/*.json` | `04_VALIDATION/EXPERIMENTS/X-001-RESULT.md` |
| `00_GOVERNANCE/CLAIM_LEDGER.yaml` (alegações e falsificadores) | `99_RELEASES/reports/*` |
| documentos das fases D, O, R, A | campo `evidence:` do claim ledger (anexado por execução) |

## Determinismo verificável

```bash
python scripts/run_cycle.py --samples 8000
sha256sum 03_UNIFICATION/INVARIANT_MAP.md      # anote
python scripts/run_cycle.py --samples 8000
sha256sum 03_UNIFICATION/INVARIANT_MAP.md      # deve ser igual, exceto a linha run_id
```

## Como falsificar este trabalho

Ordem de custo crescente. Qualquer uma delas derruba parte do que está afirmado — e é isso que
se espera de quem revisar.

1. **Barato.** Baixar um `config.json` do corpus e comparar campo a campo:
   `atlas registry verify llama-3.1-8b --repo meta-llama/Llama-3.1-8B`. Divergência derruba
   `A-009` e coloca em dúvida todo número derivado.
2. **Barato.** Recalcular à mão a contagem de parâmetros de qualquer modelo do corpus e comparar
   com `atlas registry list`. Divergência dispara F5 e invalida tudo a jusante.
3. **Médio.** Medir latência por camada de um modelo 8B em GPU real e comparar com o roofline.
   Divergência acima de 2× derruba `A-002`/`A-005` e fecha `G-003` com resultado negativo.
4. **Médio.** Traçar o modelo com `torch.export` e comparar FLOPs e bytes por classe de operador
   com a IR analítica. Divergência acima de 10 % em qualquer classe com mais de 5 % do custo
   torna obrigatória a alternativa 1 do ADR-0001.
5. **Caro.** Medir perplexidade por camada sob INT8/INT4/ternário. Qualquer papel com prior
   ≥ 0,7 que degrade além do limite derruba `A-004` e fecha `G-002`.
6. **Caro.** Sintetizar um bloco candidato em PDK aberta e comparar área com a estimativa.
   Divergência derruba `A-008` e fecha `G-007`.

## Registro de execuções

Cada execução anexa `RUN:<timestamp>` ao campo `evidence` das alegações que tocou, sem promover
status. Promoção de status é decisão humana, registrada no `DECISION_LOG`.

## O que ainda impede reprodução independente completa

`G-010` — não houve revisão adversarial externa. Autor e auditor são o mesmo agente. O portão V3
permanece **fechado** por esse motivo, e nenhum documento deste repositório pode alegar
sobrevivência a revisão independente.
