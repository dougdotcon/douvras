---
artifact: FAILURE_MAP
run_id: 20260815T113727Z
generated_by: scripts/run_model_cycle.py
status: COMPUTATIONAL_EVIDENCE
---

# Mapa de falhas

> Arquivo **gerado**. Editar a mao apaga a rastreabilidade. Para mudar o conteudo,
> mude os templates de tarefa ou as sondas e reexecute `python scripts/run_model_cycle.py`.

Corpus: 96 tarefas em 8 capacidades.
Estas taxas descrevem as **sondas de calibracao**, nao um modelo: elas mostram que a
taxonomia esta viva, ou seja, que cada celula preenchida corresponde a um modo que o
grader consegue detectar quando ele acontece.

## Cobertura por capacidade

| Capacidade | Tarefas | Contraexemplos |
|---|---:|---:|
| `arguments` | 12 | 24 |
| `error_recovery` | 12 | 12 |
| `hallucination` | 12 | 12 |
| `planning` | 12 | 12 |
| `pt_br_numeracy` | 12 | 12 |
| `safety_refusal` | 12 | 12 |
| `structured_output` | 12 | 24 |
| `tool_selection` | 12 | 24 |

## Celulas da taxonomia

```text
FONTE  sondas de calibracao  (sintetica)
│
├── ARGUMENTS
│   ├── tool_selection      25.0%
│   └── argument            12.5%
│
├── ERROR_RECOVERY
│   ├── recovery            43.8%
│   ├── tool_selection      12.5%
│   └── hallucination        6.2%
│
├── HALLUCINATION
│   ├── tool_selection      12.5%
│   └── hallucination       12.5%
│
├── PLANNING
│   ├── planning            18.8%
│   ├── tool_selection      12.5%
│   └── argument             6.2%
│
├── PT_BR_NUMERACY
│   ├── planning            37.5%
│   ├── tool_selection      25.0%
│   └── argument             4.2%
│
├── SAFETY_REFUSAL
│   ├── safety              50.0%
│   └── tool_selection      25.0%
│
├── STRUCTURED_OUTPUT
│   ├── format              37.5%
│   └── tool_selection      12.5%
│
└── TOOL_SELECTION
    ├── tool_selection      25.0%
    └── hallucination       25.0%

Estas taxas descrevem as sondas de calibracao, nao um modelo. Elas mostram que
a taxonomia esta viva — cada celula preenchida e um modo que o grader consegue
detectar quando acontece.
```

## Modos que atravessam mais de uma capacidade

| Modo | Capacidades em que aparece |
|---|---|
| `FAIL_ARGUMENT` | `arguments`, `planning`, `pt_br_numeracy` |
| `FAIL_FORMAT` | `structured_output` |
| `FAIL_HALLUCINATION` | `error_recovery`, `hallucination`, `tool_selection` |
| `FAIL_PLANNING` | `planning`, `pt_br_numeracy` |
| `FAIL_RECOVERY` | `error_recovery` |
| `FAIL_SAFETY` | `safety_refusal` |
| `FAIL_TOOL_SELECTION` | `arguments`, `error_recovery`, `hallucination`, `planning`, `pt_br_numeracy`, `safety_refusal`, `structured_output`, `tool_selection` |

**4 modo(s)** aparecem em mais de uma capacidade. Um modo que atravessa
capacidades e candidato a dataset transversal: corrigi-lo move mais de uma medida.

## Modos sem sonda

Nenhum. Todo modo declarado no corpus e disparado por ao menos uma sonda, portanto
e detectavel quando ocorre **na forma em que a sonda o produz** (`A-106`). Isto nao
e o mesmo que cobrir as formas em que um modelo real erra — ver `G-110`.

## Casos que nao se encaixam

Preservados em vez de suavizados (Metodo, portao U2):

- `FAIL_NO_ANSWER` existe como regra do grader e e exercitado por contraexemplo, mas
  nenhuma tarefa o declara em `failure_modes` — nenhuma sonda termina sem responder.
- `plano-invertido` cai apenas 0.250
  dentro do proprio alvo declarado: o alvo e definido pelos modos da tarefa, mais grosso
  que o que a sonda de fato ataca (`G-111`).
- As tarefas de `planning` misturam dois contratos distintos — ordem de operacoes e
  pergunta ante ambiguidade — e nenhuma sonda ataca os dois.
