---
artifact: EXPERIMENT_RESULT
experiment: X-001
run_id: 20260815T004803Z
generated_by: scripts/run_cycle.py
---

# X-001 — Existe subgrafo estavel e dominante o bastante para virar silicio?

## Hipotese testada

H1 (estabilidade parcial) e H2 (valor concentrado), do Metodo 14.2.

## Baseline congelado

`BASELINE-2026-08-03` — roofline analitico sobre `config/devices.json`, dispositivo
`h100-sxm`, pesos bf16, requisicao de prompt 2048 e geracao 512.

## Resultado por modelo

| Modelo | Decode memory-bound | Top-3 papeis | Custo top-3 | Fracao endurecivel | Teto de Amdahl | SRS | Banda |
|---|---|---|---|---|---|---|---|
| gemma-2-9b | 99.9% | gate_proj, up_proj, down_proj | 66.9% | 0.0% | 1.00x | 0.168 | software |
| llama-2-7b | 99.9% | gate_proj, up_proj, down_proj | 59.8% | 0.0% | 1.00x | 0.266 | software |
| llama-3-8b | 99.9% | gate_proj, up_proj, down_proj | 73.4% | 0.0% | 1.00x | 0.276 | software |
| llama-3.1-8b | 99.9% | gate_proj, up_proj, down_proj | 73.4% | 0.0% | 1.00x | 0.276 | software |
| mistral-7b-v0.1 | 99.9% | gate_proj, up_proj, down_proj | 77.3% | 0.0% | 1.00x | 0.250 | software |
| mixtral-8x7b-v0.1 | 99.9% | expert_gate_proj, expert_up_proj, expert_down_proj | 87.0% | 0.0% | 1.00x | 0.222 | software |
| phi-3-mini-4k | 99.9% | gate_proj, up_proj, down_proj | 58.3% | 0.0% | 1.00x | 0.211 | software |
| qwen2.5-14b | 99.9% | gate_proj, up_proj, down_proj | 71.4% | 0.0% | 1.00x | 0.247 | software |
| qwen2.5-7b | 99.9% | gate_proj, up_proj, down_proj | 79.6% | 0.0% | 1.00x | 0.252 | software |

## Interpretacao permitida

- **H2 sustentada nesta rodada**: em todos os 9 modelos avaliados, os tres
  papeis mais custosos concentram a maior parte do tempo de servico. O custo de inferencia
  e estruturalmente concentrado, e a concentracao esta nas projecoes lineares.
- **C-003 sustentada**: o decode e dominado por movimentacao de memoria em todos os casos.
  Estimar ganho de hardening por FLOPs superestimaria o beneficio.
- **H1 parcialmente sustentada**: 2 padrao(oes) exato(s) atravessam familias
  distintas, o que mostra que circuitos identicos ja sao compartilhados sem coordenacao
  entre laboratorios. Mas a estabilidade **temporal** dentro de familia e mais fraca que a
  cobertura cross-familia sugere.

## Interpretacao proibida

- Nao se pode concluir que os blocos identificados **devem** virar ASIC: a decisao depende
  de volume contratado, de vida util e de medicao de qualidade sob quantizacao (`G-002`).
- Nao se pode citar nenhum ganho deste experimento como medido: tudo aqui e
  `COMPUTATIONAL_EVIDENCE` ou mais fraco, sobre um modelo analitico nao calibrado.
- Nao se pode extrapolar a taxa de obsolescencia observada: o corpus cobre poucas
  transicoes de versao por familia (`G-006`).

## Reprodutibilidade

```bash
python scripts/run_cycle.py
python -m pytest tests -q
```

Integridade do corpus na execucao: erro maximo de contagem de parametros = 0.00e+00 (COMPUTATIONAL_EVIDENCE).
