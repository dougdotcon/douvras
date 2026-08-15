---
artifact: RUNBOOK
id: RB-001
title: Chegou uma nova versão de um modelo acompanhado
audience: analista do Silicon Atlas
---

# RB-001 — Nova versão de modelo

Este é o procedimento recorrente do produto (Método §17.2). Tempo estimado: 15 minutos, dos quais
o cálculo leva segundos.

## 1. Registrar a versão

Crie `corpus/models/<id>.json` com dois blocos: `douvras` (metadados) e `config` (o `config.json`
publicado, copiado sem alteração).

```json
{
  "douvras": {
    "id": "<familia>-<versao>",
    "family": "<familia>",
    "version_label": "<versao>",
    "release_date": "AAAA-MM-DD",
    "license": "<licenca>",
    "published_params": <inteiro ou null>,
    "hf_repo": "<org/nome>",
    "source_url": "https://huggingface.co/<org/nome>/resolve/main/config.json",
    "provenance": "TRANSCRITO_UNVERIFIED",
    "sha256": null,
    "note": "<o que muda em relacao a versao anterior>"
  },
  "config": { }
}
```

**Se a arquitetura não for suportada**, o registro falha alto com `UnsupportedArchitecture`. Isso
é o comportamento correto — não contorne. Escrever um construtor de IR para a nova arquitetura é
trabalho de engenharia, e um grafo silenciosamente errado é pior que um erro.

## 2. Verificar a transcrição

```bash
PYTHONPATH=src python -m silicon_atlas.cli registry verify <id> --repo <org/nome>
```

Divergência em qualquer campo → corrija o corpus antes de continuar. Sem rede, pule esta etapa e
confie na verificação indireta da etapa 3, sabendo que `G-008` permanece aberta para este modelo.

## 3. Conferir a integridade

```bash
PYTHONPATH=src python -m silicon_atlas.cli registry list
```

O erro máximo de contagem de parâmetros deve permanecer abaixo de 0,5 %. Se subir, ou o
`published_params` está errado, ou algum campo do config foi transcrito errado, ou a IR não cobre
essa arquitetura corretamente. **Pare aqui** — nada a jusante vale.

## 4. Ver o que mudou

```bash
PYTHONPATH=src python -m silicon_atlas.cli diff <versao-anterior> <nova>
```

Leia nesta ordem:

1. **`stability.exact`** — caiu? A vida útil de qualquer circuito derivado caiu junto.
2. **`configuracao alterada`** — quais campos mudaram? Mudança em `hidden_size`,
   `intermediate_size`, `num_key_value_heads` ou `head_dim` força re-síntese.
3. **`mudancas de assinatura`** — quais papéis mudaram de shape.

## 5. Reexecutar o ciclo

```bash
python scripts/run_cycle.py --models <nova>
```

Observe no resumo:

- **fração endurecível** mudou de faixa?
- **teto de Amdahl** mudou?
- **quais falsificadores** passaram a disparar (ou deixaram de disparar)?
- a **banda do SRS** mudou?

## 6. Decidir

| Observação | Ação |
|---|---|
| estabilidade exata = 1,00 e nada mais mudou | nota ao cliente; nenhuma decisão nova |
| estabilidade caiu, mas a banda não mudou | atualizar o relatório; sem reabrir conversa comercial |
| a banda do SRS mudou | **reabrir a conversa**: a recomendação anterior não vale mais |
| um falsificador passou a disparar | registrar em `RETRACTIONS_AND_CORRECTIONS.md`; verificar o que dependia daquela alegação |
| a região fixa deixou de ser vazia | verificar `git diff config/` **antes de comemorar** — pode ser afrouxamento de limiar, não descoberta |

A última linha existe porque é o modo de falha mais provável sob pressão comercial.

## 7. Registrar

- mudanças de decisão → `00_GOVERNANCE/DECISION_LOG.md`
- retratações → `00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md`
- alterações de código ou de prior → `07_SYSTEMATIZATION/CHANGELOG.md`

Promoção de status de alegação **nunca** é automática. `record_run` anexa evidência e pode
retratar; promover é decisão humana registrada.

## Quando parar e escalar

- A contagem de parâmetros não bate e você não descobre por quê em 30 minutos.
- Uma arquitetura nova exige construtor de IR (trabalho de engenharia, não de operação).
- O cliente pede que o relatório seja emitido sem alguma seção obrigatória. A resposta é não; o
  portão de emissão recusa por construção.
