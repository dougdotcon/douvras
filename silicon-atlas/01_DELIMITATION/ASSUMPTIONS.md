---
artifact: ASSUMPTIONS
status: ASSUMPTION
date: 2026-08-03
---

# Premissas do ciclo C-001

Toda premissa aqui tem status `ASSUMPTION`: usada, **não demonstrada** neste projeto.
Cada uma declara como seria refutada e onde entra no código.

| # | Premissa | Onde entra | Como seria refutada | Dívida |
|---|---|---|---|---|
| A-001 | A topologia derivada de `config.json` representa a computação real do modelo | `ir.builder` | Traçar o modelo real (torch.export) e achar operador ausente na IR | G-001 |
| A-002 | Roofline `max(compute, memória)` aproxima o tempo dentro de ±2× em decode | `profiler` | Medir latência real por camada em GPU e comparar | G-003 |
| A-003 | Energia ≈ `flops·E_flop + bytes·E_byte`, com `E_byte >> E_flop` | `hardware.EnergyModel` | Medir energia por token com telemetria de potência | G-004 |
| A-004 | Tolerância à quantização é prior por classe de operador | `quantization.PRIORS` | Medir perplexidade pós-quantização por camada | G-002 |
| A-005 | Eficiência efetiva de pico (η) de GPU é 0,35–0,70 conforme fase | `hardware.Device.efficiency` | Benchmark de GEMM/attention nos shapes reais | G-003 |
| A-006 | Custo de máscara e projeto por nó tecnológico segue faixas públicas | `economics.NRE_PRIORS` | Cotação real de foundry / design house | G-005 |
| A-007 | Taxa de mudança estrutural futura ≈ taxa observada no corpus histórico | `economics.obsolescence_risk` | Ruptura arquitetural (ex.: substituição de atenção quadrática) | G-006 |
| A-008 | Densidade de MAC e de SRAM por nó segue constantes declaradas | `economics.AreaModel` | Síntese real (OpenROAD/PDK) do bloco | G-007 |
| A-009 | Configs transcritas no corpus correspondem às publicadas | `corpus/models/*.json` | `atlas registry verify` contra a fonte upstream | G-008 |

## Premissa estrutural do produto

`ENGINEERING_DECISION` — O valor do Silicon Atlas não depende de nenhum ganho de hardware ser
grande. Ele depende de a **decisão** ser auditável. Um resultado negativo bem sustentado
("este modelo não deve virar ASIC, e aqui está o volume que mudaria isso") é entregável vendável
(§14.6 do Método).
