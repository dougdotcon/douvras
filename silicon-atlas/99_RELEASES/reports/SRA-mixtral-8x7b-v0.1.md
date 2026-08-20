---
artifact: SILICON_READINESS_ASSESSMENT
model: mixtral-8x7b-v0.1
run_id: 20260820T015322Z
generated_at: 2026-08-20T01:53:22+00:00
method: DOUVRAS 2.0
cycle: C-001
weakest_status: ASSUMPTION
recommendation: software
decidable: False
---

# Silicon Readiness Assessment — mixtral-8x7b-v0.1

> Emitido pelo DOUVRAS Silicon Atlas. Todo numero deste documento carrega status epistemico.
> Nenhum resultado e mais forte que sua dependencia mais fraca: **ASSUMPTION**.

## 1. Pergunta principal

Quais subgrafos de inferencia de **mixtral-8x7b-v0.1** sao simultaneamente estaveis, dominantes em custo e tolerantes a baixa precisao o suficiente para justificar especializacao em hardware — e a partir de qual volume isso se paga?

## 2. Afirmacao principal

Sob as condicoes declaradas, a regiao endurecivel de **mixtral-8x7b-v0.1** cobre **0.0%** do custo de servico, o que limita o ganho de sistema a **1.00x** numa arquitetura hibrida. Nao existe break-even a reportar: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular, de modo que nenhum acelerador foi dimensionado para 1e+13 tokens/ano.

**Recomendacao: manter em software; nenhuma especializacao se justifica com a evidencia atual.**

Status da afirmacao: `ASSUMPTION` (elo mais fraco da cadeia de evidencia).

**Ressalvas que qualificam esta recomendacao:**

1. **87% do custo** esta em operadores *irregulares* (enderecamento dependente de dado). Nenhuma quantidade de observacao de versoes os torna endureciveis: exigem reprojeto do operador, nao espera.
2. O ranking de candidatos nao sobreviveu a perturbacao de 20% nos pesos (**F3 disparado**). Tratar a ordem como indicacao, nao como recomendacao — ver CE-001.
3. Sem regiao fixa nao ha projeto: os fatores P, R e N do SRS entram como zero declarado e **F4 fica nao avaliavel**. Nenhum numero de PPA ou break-even e emitido.

## 3. Hipoteses

1. **H1 — Estabilidade parcial**: blocos do caminho dominante permanecem estruturalmente estaveis entre versoes.
2. **H2 — Valor concentrado**: poucos padroes concentram a maior parte do custo.
3. **H3 — Hibrido domina**: fixar apenas o estavel supera fixar tudo, ajustado ao risco.
4. **H4 — Baixa precisao viabiliza**: tolerancia a INT4/ternario amplia o candidato.

## 4. Dependencias

- `A-001` — a IR e derivada de configuracao, nao tracada do modelo real (ADR-0001)
- `A-002/A-005` — roofline analitico com eficiencia assumida, nao calibrada
- `A-003` — energia por byte e por FLOP em ordem de grandeza
- `A-004` — tolerancia a quantizacao e prior de literatura, nao medicao
- `A-006/A-008` — custos de mascara, wafer e densidade de area sao faixas publicas
- `A-007` — taxa de mudanca futura extrapola o historico curto do corpus

Lacunas abertas que limitam o status de tudo acima: `G-001`, `G-002`, `G-003`, `G-004`, `G-006`, `G-009`

## 5. Criterios de falha (declarados antes da execucao)

- **F1** — nenhum padrao com cobertura >= 0.80 entre versoes da familia  
  observado: estabilidade exata entre versoes = 0.00; alcance cross-familia do melhor padrao = 0.30  
  **DISPARADO**
- **F2** — o padrao mais custoso muda de identidade entre versoes  
  observado: bloco mais custoso 'moe' (papel expert_gate_proj, 29.0% do custo): E = 0.10  
  **DISPARADO**
- **F3** — top-1 do ranking troca sob perturbacao de +-20% dos pesos, ou vence por margem menor que o ruido (criterio reforcado apos CE-001)  
  observado: estabilidade do top-1 = 0.660 (limite 0.95); margem = 0.0071 contra ruido 0.0266  
  **DISPARADO**
- **F4** — break-even P50 posterior a vida economica  
  observado: nao avaliavel: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular  
  **nao disparado**
- **F5** — erro de contagem de parametros acima de 5%  
  observado: erro = 0.0000%  
  **nao disparado**

## 6. Resultados

### Perfil de execucao — NVIDIA H100 SXM 80GB

Requisicao de referencia: prompt 2048, geracao 512,
lote 1, contexto 2304, pesos bf16.

| Metrica | Prefill | Decode |
|---|---|---|
| tokens/s | 19,557 | 103.7 |
| intensidade aritmetica (FLOP/byte) | 664.1 | 1.03 |
| ponto de inflexao do dispositivo | 253 | 92 |
| tempo limitado por memoria | 15.1% | 99.9% |
| energia por token | 57.98 mJ | 10933.0 mJ |

O decode consome 97.9% do tempo da requisicao. Toda decisao de
hardening abaixo e ponderada por essa mistura, nao por FLOPs isolados.

### Onde o custo esta

| Papel | Participacao na requisicao |
|---|---|
| expert_gate_proj | 29.01% |
| expert_up_proj | 29.01% |
| expert_down_proj | 29.01% |
| q_proj | 4.14% |
| o_proj | 4.14% |
| kv_read | 1.15% |
| k_proj | 1.04% |
| v_proj | 1.04% |

### Candidatos a endurecimento (LHS)

| Papel | Bloco | Custo | Instancias/token | Precisao | LHS |
|---|---|---|---|---|---|
| lm_head | head | 1.0% | 1 | int8 | 0.509 |
| o_proj | attention | 4.1% | 32 | int8 | 0.502 |
| q_proj | attention | 4.1% | 32 | int8 | 0.498 |
| v_proj | attention | 1.0% | 32 | int8 | 0.493 |
| k_proj | attention | 1.0% | 32 | int8 | 0.486 |
| expert_gate_proj | moe | 29.0% | 64 | int8 | 0.445 |
| expert_up_proj | moe | 29.0% | 64 | int8 | 0.445 |
| expert_down_proj | moe | 29.0% | 64 | int8 | 0.440 |

### Particao recomendada

```text
FPGA/eFPGA: 98.4% do custo
  ├── expert_gate_proj      29.0%  irregular (R=1.00, M=0.00): operador emergente ou roteamento
  ├── expert_up_proj        29.0%  irregular (R=1.00, M=0.00): operador emergente ou roteamento
  ├── expert_down_proj      29.0%  irregular (R=1.00, M=0.00): operador emergente ou roteamento
  ├── o_proj                 4.1%  regular e quantizavel, porem LHS=0.50 < 0.55; E=0.16 < 0.6: prototipar antes de fixar
  ├── q_proj                 4.1%  regular e quantizavel, porem LHS=0.50 < 0.55; E=0.16 < 0.6: prototipar antes de fixar
  ├── v_proj                 1.0%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.16 < 0.6: prototipar antes de fixar
  ├── k_proj                 1.0%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.16 < 0.6: prototipar antes de fixar
  └── lm_head                1.0%  regular e quantizavel, porem LHS=0.51 < 0.55: prototipar antes de fixar
CPU/GPU: 1.1% do custo
  └── kv_read                1.1%  LHS=0.38 < 0.55; E=0.16 < 0.6; Q=0.00 < 0.6
```

Nivel de especializacao implicado: **3 — acelerador por arquitetura**.
Regiao fixa cobre **0.0%** do custo da requisicao.

**Teto de Amdahl da particao: 1.00x.**
Um ganho de 100x e inalcancavel nesta particao mesmo com aceleracao infinita na regiao fixa: exigiria mover tambem a regiao programavel (100.0% do custo) para o mesmo silicio.

### Quantizacao

Plano por sensibilidade reduz o **trafego de leitura de pesos por passo** em
**0.5%** (25.50 GB para
25.37 GB por passo de decode), com aceleracao estimada de
1.01x. O **footprint residente** e grandeza distinta:
93.41 GB, contra
80 GB de capacidade
(**NAO cabe**,
folga -16.8%).

A perda de qualidade correspondente **nao foi medida** (`G-002`).

### PPA e economia — distribuicoes, nao pontos

A regiao fixa ficou **vazia** sob a politica de particionamento vigente: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular. Nenhum acelerador foi dimensionado, nenhum NRE foi estimado, e nao existe break-even — nem finito, nem infinito: nao ha objeto a amortizar.

Consequencia registrada: os fatores **P** (ganho por watt), **R** (receita) e **N** (risco de NRE) do SRS entram como **zero declarado**, e o falsificador **F4** fica *nao avaliavel*. Publicar percentis de area, NRE ou break-even aqui seria descrever um objeto inexistente — foi exatamente o defeito retratado em `R-002`.

Isto **e** o resultado: para mixtral-8x7b-v0.1, o bloco que domina o custo (moe, 29.0% do tempo) tem estabilidade estrutural E = 0.10, abaixo do limite da politica. O gasto em mascara nao tem o que financiar. A decisao economica so passa a existir se essa estabilidade subir — por escopo declarado mais estreito, por observacao de mais versoes, ou por calibracao da politica contra casos reais (`G-011`).

### Silicon Readiness Score

**SRS = 0.222** (ASSUMPTION) -> banda **software**

| Fator | Valor | Peso | Contribuicao | Status |
|---|---|---|---|---|
| A — arch_stability | 0.000 | +0.15 | +0.0000 | `COMPUTATIONAL_EVIDENCE` |
| H — concentration | 0.258 | +0.15 | +0.0387 | `CONDITIONAL_RESULT` |
| T — throughput | 0.667 | +0.15 | +0.1000 | `ASSUMPTION` |
| P — perf_per_watt | 0.000 | +0.15 | +0.0000 | `CONDITIONAL_RESULT` |
| Q — low_precision | 0.769 | +0.10 | +0.0769 | `ASSUMPTION` |
| D — data_availability | 1.000 | +0.10 | +0.1000 | `OBSERVATION` |
| C — codesign | 0.563 | +0.10 | +0.0563 | `MODEL` |
| R — revenue_potential | 0.000 | +0.10 | +0.0000 | `CONDITIONAL_RESULT` |
| O — obsolescence_risk | 1.000 | -0.15 | -0.1500 | `CONDITIONAL_RESULT` |
| N — nre_risk | 0.000 | -0.10 | -0.0000 | `CONDITIONAL_RESULT` |

### Efeito do escopo de comparacao

A estabilidade estrutural depende de quais versoes entram na comparacao — e essa escolha e do
analista, nao do dado.

| Escopo | Estabilidade exata |
|---|---|
| media sobre 1 transicao(oes) da familia `mistral` | 0.00 |
| apenas a transicao mais recente (mistral-7b-v0.1 -> mixtral-8x7b-v0.1) | 0.00 |

Diferenca: +0.00. O escopo desloca o numero, mas nao atravessa o limite da politica.

Os scores deste relatorio usam a **media da familia** — a leitura conservadora. Um cliente cujo
compromisso e apenas com a linha mais recente deve reexecutar declarando esse escopo, e o
relatorio resultante sera outro documento, com outra recomendacao.

### Alcance cross-familia

Blocos deste modelo cujo circuito **exato** ja serve outra familia — o que define o mercado
enderecavel de um bloco de IP, e nao se confunde com estabilidade temporal:

| Bloco | Cobertura do corpus | Modelos atendidos |
|---|---|---|
| attention | 0.30 | llama-3-8b, llama-3.1-8b, mixtral-8x7b-v0.1 |

Alcance maximo: **30%** de um corpus de 10 modelos. Um bloco
estavel no tempo e util a um cliente; um bloco com alcance cross-familia e util a um mercado.
As duas propriedades sao independentes e ambas precisam ser verdadeiras para justificar IP.

### Estabilidade do proprio score

Perturbando os pesos em +-20% (2,000 amostras):
top-1 estavel em **66.0%** das amostras, top-3 em
83.4%, banda de decisao do SRS estavel em
100.0%. Fator dominante: `R`.

Dispersao dos scores: 0.1304. Largura do ruido induzido pelos pesos:
0.0266. **Diagnostico: score NAO discrimina: entre os 5 candidatos que disputam a primeira posicao, 35% do peso esta em fatores identicos; a margem (0.0071) e menor que o ruido (0.0266).**

Disputam a primeira posicao, dentro do ruido: `lm_head`, `o_proj`, `q_proj`, `v_proj`, `k_proj`. Entre eles, **35% do peso do LHS esta em fatores identicos** — estabilidade, regularidade, previsibilidade de memoria, volume e vida util sao os mesmos para toda projecao linear do mesmo modelo. Sobre o conjunto completo de candidatos o peso inerte e 25%.

A ordem acaba decidida apenas por `E`, `F`, `Q`, `V`, `M`, que se cancelam parcialmente: o papel com mais custo tende a ter tolerancia a quantizacao menor.

Consequencia pratica: o LHS, com os pesos do Metodo, ordena candidatos **dentro de um modelo** com margem menor que o proprio ruido dos pesos. Ele continua util para comparar casos entre si (onde E, V e L de fato variam), mas nao para escolher qual projecao endurecer primeiro. Registrado como contraexemplo CE-001; a correcao exige calibracao dos pesos contra casos reais, nao ajuste ad hoc.

## 7. Limitacoes

- A IR nao foi confrontada com um tracado real do modelo (`G-001`). Operadores fundidos,
  kernels reais e reordenacoes de grafo nao aparecem aqui.
- O roofline nao foi calibrado contra latencia medida (`G-003`). Ele acerta o **regime**
  (compute-bound vs memory-bound) com mais confianca do que acerta o valor absoluto.
- A tolerancia a quantizacao e prior de literatura (`G-002`). Nenhuma perplexidade foi medida.
- Energia de GPU vem de TDP e overhead assumidos; energia do alvo especializado vem de um
  modelo analitico (`G-004`). Comparar os dois favorece estruturalmente o alvo — o numero de
  ganho de energia deve ser lido como teto otimista, nao como previsao.
- Custos de mascara, wafer, densidade e empacotamento sao faixas publicas, nao cotacoes
  (`G-005`, `G-007`).
- A taxa de obsolescencia extrapola 2 versao(oes) de uma familia
  (`G-006`). Uma ruptura arquitetural invalida a extrapolacao inteira.
- Nao houve revisao adversarial externa (`G-010`): autor e auditor sao o mesmo agente.
- Pesos do LHS e do SRS estao **UNCALIBRATED — nenhum caso real de tape-out alimentou estes pesos ainda**.

## 8. O que este resultado NAO demonstra

Este relatorio **nao** demonstra:

1. Que o modelo mantem qualidade sob a quantizacao proposta. Nenhuma acuracia foi medida.
2. Que o acelerador descrito e fabricavel. Nao houve sintese, floorplan, timing closure nem
   analise de potencia fisica.
3. Que os ganhos de energia se realizam. Eles saem de constantes de ordem de grandeza
   comparadas com um TDP de GPU — assimetria declarada em `A-003`.
4. Que a estrutura do modelo sobrevive ao horizonte assumido. A taxa de mudanca e extrapolacao.
5. Que 100x e alcancavel. Um ganho de 100x e inalcancavel nesta particao mesmo com aceleracao infinita na regiao fixa: exigiria mover tambem a regiao programavel (100.0% do custo) para o mesmo silicio.
6. Que os numeros do unico demonstrador publico comparavel (`E-002`) sao reproduziveis: sao
   declarados pelo fabricante e nao foram verificados de forma independente.
7. Que o SRS mede prontidao real. Os pesos nunca foram calibrados contra um tape-out concluido;
   ate que sejam, o score ordena candidatos, nao prediz sucesso.

---

## Anexo A — Fingerprint arquitetural

```json
{
  "model": "mixtral-8x7b-v0.1",
  "family": "mistral",
  "version": "moe-0.1",
  "release_date": "2023-12-11",
  "architecture_class": "decoder_transformer",
  "attention": "gqa",
  "gqa_ratio": 4,
  "head_dim": 128,
  "layers": 32,
  "hidden_size": 4096,
  "intermediate_size": 14336,
  "mlp": "swiglu",
  "mlp_ratio": 3.5,
  "normalization": "rmsnorm",
  "norms_per_layer": 2,
  "position": "rope",
  "rope_theta": 1000000.0,
  "routing": "sparse_moe",
  "vocab_size": 32000,
  "tied_embeddings": false,
  "sliding_window": null,
  "params": 46702792704,
  "quantization_candidates": [
    "int8",
    "int4"
  ],
  "dynamic_regions": [
    "head",
    "moe"
  ],
  "distinct_layer_patterns": 2
}
```

## Anexo B — Estabilidade da familia `mistral`

Versoes comparadas: mistral-7b-v0.1 -> mixtral-8x7b-v0.1

Transicoes temporais observadas: **1**

| Nivel de identidade | Estabilidade media |
|---|---|
| topologia | 0.333 |
| padrao (proporcoes) | 0.000 |
| exato (mesmo circuito) | 0.000 |

Taxa de mudanca estrutural observada: 4.87 por ano

**mistral-7b-v0.1 -> mixtral-8x7b-v0.1** (75 dias) — estabilidade exata 0.00, padrao 0.00, topologia 0.33
  - `rope_theta`: 10000.0 -> 1000000.0
  - `sliding_window`: 4096 -> None

## Anexo C — Proveniencia

- Modelo: `mixtral-8x7b-v0.1`, familia `mistral`, licenca `apache-2.0`
- Fonte da configuracao: https://huggingface.co/mistralai/Mixtral-8x7B-v0.1/resolve/main/config.json
- Status de proveniencia: `FETCHED`
- Parametros derivados da IR: 46,702,792,704 | publicados: 46,702,792,704
- Baseline de hardware: `h100-sxm` — picos densos de datasheet do fabricante; eficiencia e custo assumidos
- Pesos de score: v1.0 (UNCALIBRATED — nenhum caso real de tape-out alimentou estes pesos ainda)
- Priors de quantizacao: v1.0

## Anexo D — Todas as afirmacoes emitidas

| Afirmacao | Valor | Status | Lacunas |
|---|---|---|---|
| `mixtral-8x7b-v0.1.params` | 46702792704 params | `MODEL` | G-001 |
| `mixtral-8x7b-v0.1.serving.decode_time_share` | 0.9792 fracao do tempo de requisicao | `CONDITIONAL_RESULT` | G-003, G-009 |
| `mixtral-8x7b-v0.1.serving.energy_per_token` | 11.16 J/token gerado | `CONDITIONAL_RESULT` | G-003, G-004, G-009 |
| `mixtral-8x7b-v0.1.decode.tokens_per_s` | 103.7 tok/s | `CONDITIONAL_RESULT` | G-003 |
| `mixtral-8x7b-v0.1.decode.memory_bound_share` | 0.9995 fracao do tempo | `CONDITIONAL_RESULT` | G-003 |
| `mixtral-8x7b-v0.1.decode.arith_intensity` | 1.035 FLOP/byte | `CONDITIONAL_RESULT` | G-003 |
| `mixtral-8x7b-v0.1.decode.energy_per_token` | 10.93 J/token | `CONDITIONAL_RESULT` | G-003, G-004 |
| `quant.sensitivity.memory_reduction` | 0.005141 fracao | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.speedup` | 1.005 x sobre baseline | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.quality_delta` | — perplexidade / acuracia | `OPEN_GAP` | G-002 |
| `quant.reachable_cost_share.int4` | 0.6235 fracao do tempo | `CONDITIONAL_RESULT` | G-002, G-003 |
| `mixtral-8x7b-v0.1.partition.hardened_share` | 0 fracao do tempo | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `mixtral-8x7b-v0.1.partition.amdahl_ceiling` | 1 x sobre baseline | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `partition.claim_check` | 1 x (teto do sistema) | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `economics.breakeven_years.p50` | — anos | `OPEN_GAP` | G-001 |
| `economics.p_breakeven_before_obsolescence` | — probabilidade | `OPEN_GAP` | G-001 |
| `economics.die_area_mm2.p50` | — mm2 | `OPEN_GAP` | G-001 |
| `SRS.mixtral-8x7b-v0.1` | 0.2218 score SRS | `ASSUMPTION` | G-001, G-002, G-003, G-006, G-009 |
| `readiness.rank_stability` | 0.66 fracao das amostras com mesmo top-1 | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `stability.mistral.exact` | 0 fracao de blocos preservados | `COMPUTATIONAL_EVIDENCE` | G-001 |

---

_DOUVRAS Labs — Muitas formas. Uma estrutura._
