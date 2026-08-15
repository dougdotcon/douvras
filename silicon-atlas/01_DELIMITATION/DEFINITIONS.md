---
artifact: DEFINITIONS
status: DEFINITION
date: 2026-08-03
---

# Definições operacionais

Todo termo abaixo tem status `DEFINITION`: é convenção adotada para tornar o problema operacional,
não descoberta. Cada definição aponta para o símbolo correspondente no código.

| Termo | Definição operacional | Implementação |
|---|---|---|
| **Subgrafo** | Conjunto conexo de nós da DOUVRAS IR com fronteira de entrada/saída declarada | `ir.graph.Graph.subgraph` |
| **Padrão** | Classe de equivalência de subgrafos sob renomeação, índice de camada e batch | `fingerprint.pattern_hash` |
| **Estabilidade estrutural (E)** | Fração das versões comparadas em que o `pattern_hash` reaparece com a mesma aridade | `invariants.pattern_coverage` |
| **Estabilidade exata** | Idem, exigindo shapes idênticos (não só proporções) | `invariants.exact_coverage` |
| **Fração de custo (F)** | Participação do padrão no tempo total roofline da fase declarada | `profiler.PhaseProfile.share` |
| **Regularidade (R)** | 1 − (fração de nós com controle dinâmico ou shape dependente de dado) | `readiness.regularity` |
| **Tolerância à quantização (Q)** | Prior por classe de operador, sobrescrito por medição quando houver | `quantization.tolerance` |
| **Volume (V)** | Tokens/ano do workload declarado, normalizado em escala log | `readiness.volume_factor` |
| **Previsibilidade de memória (M)** | 1 − (fração de bytes com endereçamento dependente de dado) | `readiness.memory_predictability` |
| **Vida útil (L)** | Meses até a probabilidade de sobrevivência estrutural cair abaixo de 0,5 | `economics.survival_months` |
| **Hardening** | Substituição de execução programável por circuito fixo ou memória somente leitura | conceito |
| **Nível de especialização** | Escada 0–6 do Método §6.5, declarada por partição | `partition.Level` |
| **Prefill** | Fase que processa `S` tokens de prompt em paralelo; compute-bound | `profiler.Phase.PREFILL` |
| **Decode** | Fase que gera 1 token com contexto `T`; memory-bound | `profiler.Phase.DECODE` |
| **Intensidade aritmética** | FLOPs ÷ bytes movidos, por nó | `profiler.NodeCost.intensity` |
| **Roofline** | `t = max(flops / (peak·η), bytes / bw)` | `profiler.roofline_time` |
| **NRE** | Custo não recorrente: máscaras, projeto, verificação, bring-up | `economics.NRECost` |
| **Break-even** | Tokens até NRE ser amortizado pela diferença de custo por token | `economics.break_even_tokens` |
| **UMI** | Unidade Mínima Invariante: menor subgrafo que preserva o valor medido | `05_REDUCTION/MINIMAL_STRUCTURE.md` |
| **Risco de obsolescência (O)** | 1 − P(estrutura sobrevive à vida econômica), da taxa de mudança observada | `economics.obsolescence_risk` |

## Convenções de símbolos

```text
B  batch                     P  parâmetros
S  comprimento de prompt     d  hidden_size
T  comprimento de contexto   h  cabeças de atenção
L  camadas                   g  cabeças KV (GQA)
I  intermediate_size         V  vocabulário
```

## O que este documento NÃO define

Não define "estável" em sentido semântico (comportamento do modelo), apenas estrutural (topologia
do grafo). A estabilidade de **pesos** e de **acurácia** é `OPEN_GAP` — ver `GAP_REGISTER:G-002`.
