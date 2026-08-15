---
artifact: RUNBOOK
id: RB-101
cycle: C-002
---

# RB-101 — entrada de um modelo novo no corpus

## Quando usar

Um laboratório publica um modelo pequeno relevante para português ou para uso agêntico, e ele
deve entrar no corpus do Model Atlas.

## Passos

### 1. Registrar a ficha

Crie `model-atlas/corpus/models/<id>.json`. Campos que a fonte **não afirma** ficam `null` —
`context_len` e `license` plausíveis seriam proveniência inventada (`D-108`).

```json
{
  "douvras": {
    "id": "...", "repo": "org/nome", "family": "...",
    "params_b": null, "context_len": null, "license": "",
    "quantizations": ["f16", "q8", "q4"],
    "weights_local": false,
    "provenance": "DOCUMENT_SECONDARY",
    "source": "<onde foi lido, com seção>"
  }
}
```

### 2. Conferir contra a fonte

```bash
PYTHONPATH=src python -m model_atlas.cli registry verify <id>
```

Exige rede e o extra `[run]`. Se conferir, mude `provenance` para `UPSTREAM_VERIFIED` — é o que
move `G-108`.

### 3. Ver o que a aritmética já responde

```bash
PYTHONPATH=src python -m model_atlas.cli profile <id> --ram 16
```

Se nenhuma quantização couber na máquina de referência, decida agora: ou o modelo entra apenas
como referência de porte, ou o corpus precisa de outra máquina.

### 4. Ciclo completo

```bash
python scripts/run_model_cycle.py
```

## O que observar, nessa ordem

1. **A ficha tem `params_b`?** Sem ela, o orçamento de memória sai como ausência declarada, e o
   assessment perde a única seção que hoje tem número.
2. **A proveniência é `DOCUMENT_SECONDARY`?** Então `G-108` continua aberta e todo derivado para
   em `CONDITIONAL_RESULT`.
3. **Há pesos locais?** Se não, o assessment sai concluindo "não dá para saber ainda". É o
   comportamento correto, não um defeito a contornar.
4. **O modelo mudou o veredicto de algum portão?** Só `O1` depende do tamanho do corpus de
   modelos (mínimo três). Se passou de dois para três, registre no `DECISION_LOG`.

## O que **não** fazer

- Não preencha `params_b` "por analogia com o irmão de mesmo porte". A analogia entra como
  `ANALOGY` no contrato de status, que é mais fraco que `ASSUMPTION` — e aqui viraria um número
  sem rótulo.
- Não marque `weights_local: true` antes de os pesos existirem no disco. É esse campo que
  autoriza o sistema a produzir capacidade medida.
