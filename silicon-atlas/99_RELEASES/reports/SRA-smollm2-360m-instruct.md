---
artifact: SILICON_READINESS_ASSESSMENT
model: smollm2-360m-instruct
run_id: 20260820T015324Z
generated_at: 2026-08-20T01:53:24+00:00
method: DOUVRAS 2.0
cycle: C-001
weakest_status: OPEN_GAP
recommendation: software
decidable: False
---

# Silicon Readiness Assessment — smollm2-360m-instruct

> Emitido pelo DOUVRAS Silicon Atlas. Todo numero deste documento carrega status epistemico.
> Nenhum resultado e mais forte que sua dependencia mais fraca: **OPEN_GAP**.

## 1. Pergunta principal

Quais subgrafos de inferencia de **smollm2-360m-instruct** sao simultaneamente estaveis, dominantes em custo e tolerantes a baixa precisao o suficiente para justificar especializacao em hardware — e a partir de qual volume isso se paga?

## 2. Afirmacao principal

Sob as condicoes declaradas, a regiao endurecivel de **smollm2-360m-instruct** cobre **0.0%** do custo de servico, o que limita o ganho de sistema a **1.00x** numa arquitetura hibrida. Nao existe break-even a reportar: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular, de modo que nenhum acelerador foi dimensionado para 1e+13 tokens/ano.

**Recomendacao: manter em software; nenhuma especializacao se justifica com a evidencia atual.**

Status da afirmacao: `OPEN_GAP` (elo mais fraco da cadeia de evidencia).

**Ressalvas que qualificam esta recomendacao:**

1. **98% do custo** esta em operadores regulares e quantizaveis, barrados *apenas pela estabilidade*. Acao util: prototipar em FPGA para medir o ganho real antes de qualquer compromisso de mascara.
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
  observado: familia sem transicao temporal no corpus (1 versao(oes)): nao avaliavel  
  **nao disparado**
- **F2** — o padrao mais custoso muda de identidade entre versoes  
  observado: bloco mais custoso 'mlp' (papel gate_proj, 18.9% do custo): E = 0.10  
  **DISPARADO**
- **F3** — top-1 do ranking troca sob perturbacao de +-20% dos pesos, ou vence por margem menor que o ruido (criterio reforcado apos CE-001)  
  observado: estabilidade do top-1 = 0.715 (limite 0.95); margem = 0.0018 contra ruido 0.0263  
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
| tokens/s | 466,205 | 3,251.3 |
| intensidade aritmetica (FLOP/byte) | 207.4 | 1.23 |
| ponto de inflexao do dispositivo | 253 | 92 |
| tempo limitado por memoria | 43.8% | 99.6% |
| energia por token | 2.43 mJ | 348.8 mJ |

O decode consome 97.3% do tempo da requisicao. Toda decisao de
hardening abaixo e ponderada por essa mistura, nao por FLOPs isolados.

### Onde o custo esta

| Papel | Participacao na requisicao |
|---|---|
| gate_proj | 18.93% |
| up_proj | 18.93% |
| down_proj | 18.93% |
| lm_head | 11.17% |
| kv_read | 11.16% |
| q_proj | 7.10% |
| o_proj | 7.10% |
| k_proj | 2.38% |

### Candidatos a endurecimento (LHS)

| Papel | Bloco | Custo | Instancias/token | Precisao | LHS |
|---|---|---|---|---|---|
| q_proj | attention | 7.1% | 32 | int8 | 0.503 |
| gate_proj | mlp | 18.9% | 32 | int4 | 0.501 |
| up_proj | mlp | 18.9% | 32 | int4 | 0.501 |
| v_proj | attention | 2.4% | 32 | int8 | 0.496 |
| k_proj | attention | 2.4% | 32 | int8 | 0.488 |
| down_proj | mlp | 18.9% | 32 | int4 | 0.486 |
| o_proj | attention | 7.1% | 32 | int4 | 0.465 |
| lm_head | head | 11.2% | 1 | int8 | 0.411 |

### Particao recomendada

```text
FPGA/eFPGA: 86.9% do custo
  ├── gate_proj             18.9%  regular e quantizavel, porem LHS=0.50 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  ├── up_proj               18.9%  regular e quantizavel, porem LHS=0.50 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  ├── down_proj             18.9%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  ├── lm_head               11.2%  regular e quantizavel, porem LHS=0.41 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  ├── q_proj                 7.1%  regular e quantizavel, porem LHS=0.50 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  ├── o_proj                 7.1%  regular e quantizavel, porem LHS=0.47 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  ├── v_proj                 2.4%  regular e quantizavel, porem LHS=0.50 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
  └── k_proj                 2.4%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.10 < 0.6: prototipar antes de fixar
CPU/GPU: 11.2% do custo
  └── kv_read               11.2%  LHS=0.38 < 0.55; E=0.10 < 0.6; Q=0.00 < 0.6
```

Nivel de especializacao implicado: **3 — acelerador por arquitetura**.
Regiao fixa cobre **0.0%** do custo da requisicao.

**Teto de Amdahl da particao: 1.00x.**
Um ganho de 100x e inalcancavel nesta particao mesmo com aceleracao infinita na regiao fixa: exigiria mover tambem a regiao programavel (100.0% do custo) para o mesmo silicio.

### Quantizacao

Plano por sensibilidade reduz o **trafego de leitura de pesos por passo** em
**50.0%** (0.72 GB para
0.36 GB por passo de decode), com aceleracao estimada de
1.78x. O **footprint residente** e grandeza distinta:
0.72 GB, contra
80 GB de capacidade
(cabe,
folga +99.1%).

A perda de qualidade correspondente **nao foi medida** (`G-002`).

### PPA e economia — distribuicoes, nao pontos

A regiao fixa ficou **vazia** sob a politica de particionamento vigente: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular. Nenhum acelerador foi dimensionado, nenhum NRE foi estimado, e nao existe break-even — nem finito, nem infinito: nao ha objeto a amortizar.

Consequencia registrada: os fatores **P** (ganho por watt), **R** (receita) e **N** (risco de NRE) do SRS entram como **zero declarado**, e o falsificador **F4** fica *nao avaliavel*. Publicar percentis de area, NRE ou break-even aqui seria descrever um objeto inexistente — foi exatamente o defeito retratado em `R-002`.

Isto **e** o resultado: para smollm2-360m-instruct, o bloco que domina o custo (mlp, 18.9% do tempo) tem estabilidade estrutural E = 0.10, abaixo do limite da politica. O gasto em mascara nao tem o que financiar. A decisao economica so passa a existir se essa estabilidade subir — por escopo declarado mais estreito, por observacao de mais versoes, ou por calibracao da politica contra casos reais (`G-011`).

### Silicon Readiness Score

**SRS = 0.209** (OPEN_GAP) -> banda **software**

| Fator | Valor | Peso | Contribuicao | Status |
|---|---|---|---|---|
| A — arch_stability | 0.000 | +0.15 | +0.0000 | `OPEN_GAP` |
| H — concentration | 0.147 | +0.15 | +0.0221 | `CONDITIONAL_RESULT` |
| T — throughput | 0.667 | +0.15 | +0.1000 | `ASSUMPTION` |
| P — perf_per_watt | 0.000 | +0.15 | +0.0000 | `CONDITIONAL_RESULT` |
| Q — low_precision | 0.622 | +0.10 | +0.0622 | `ASSUMPTION` |
| D — data_availability | 0.750 | +0.10 | +0.0750 | `OBSERVATION` |
| C — codesign | 1.000 | +0.10 | +0.1000 | `MODEL` |
| R — revenue_potential | 0.000 | +0.10 | +0.0000 | `CONDITIONAL_RESULT` |
| O — obsolescence_risk | 1.000 | -0.15 | -0.1500 | `OPEN_GAP` |
| N — nre_risk | 0.000 | -0.10 | -0.0000 | `CONDITIONAL_RESULT` |

### Efeito do escopo de comparacao

_Familia sem transicao temporal no corpus (1 versao(oes)): o efeito de escopo nao pode ser medido, e a estabilidade estrutural entra como lacuna aberta (`G-006`), nao como valor otimista._

### Alcance cross-familia

Nenhum bloco exato deste modelo reaparece em outra familia do corpus (alcance maximo 0.10). Um bloco de IP construido a partir dele atende, hoje, um unico modelo.

### Estabilidade do proprio score

Perturbando os pesos em +-20% (2,000 amostras):
top-1 estavel em **71.5%** das amostras, top-3 em
92.1%, banda de decisao do SRS estavel em
100.0%. Fator dominante: `R`.

Dispersao dos scores: 0.1214. Largura do ruido induzido pelos pesos:
0.0263. **Diagnostico: score NAO discrimina: entre os 6 candidatos que disputam a primeira posicao, 70% do peso esta em fatores identicos; a margem (0.0018) e menor que o ruido (0.0263).**

Disputam a primeira posicao, dentro do ruido: `q_proj`, `gate_proj`, `up_proj`, `v_proj`, `k_proj`, `down_proj`. Entre eles, **70% do peso do LHS esta em fatores identicos** — estabilidade, regularidade, previsibilidade de memoria, volume e vida util sao os mesmos para toda projecao linear do mesmo modelo. Sobre o conjunto completo de candidatos o peso inerte e 55%.

A ordem acaba decidida apenas por `F`, `Q`, `V`, que se cancelam parcialmente: o papel com mais custo tende a ter tolerancia a quantizacao menor.

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
- A taxa de obsolescencia extrapola 1 versao(oes) de uma familia
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
  "model": "smollm2-360m-instruct",
  "family": "smollm",
  "version": "2.0",
  "release_date": "2024-11-01",
  "architecture_class": "decoder_transformer",
  "attention": "gqa",
  "gqa_ratio": 3,
  "head_dim": 64,
  "layers": 32,
  "hidden_size": 960,
  "intermediate_size": 2560,
  "mlp": "swiglu",
  "mlp_ratio": 2.6667,
  "normalization": "rmsnorm",
  "norms_per_layer": 2,
  "position": "rope",
  "rope_theta": 100000.0,
  "routing": "dense",
  "vocab_size": 49152,
  "tied_embeddings": true,
  "sliding_window": null,
  "params": 361821120,
  "quantization_candidates": [
    "int8",
    "ternary"
  ],
  "dynamic_regions": [
    "head"
  ],
  "distinct_layer_patterns": 2
}
```

## Anexo B — Estabilidade da familia `smollm`

Versoes comparadas: smollm2-360m-instruct

Transicoes temporais observadas: **0**

| Nivel de identidade | Estabilidade media |
|---|---|
| topologia | nao observada (`G-006`) |
| padrao (proporcoes) | nao observada (`G-006`) |
| exato (mesmo circuito) | nao observada (`G-006`) |

Taxa de mudanca estrutural observada: nao estimavel: sem transicao temporal no corpus (`G-006`)

_Sem transicoes de versao no corpus para esta familia._

## Anexo C — Proveniencia

- Modelo: `smollm2-360m-instruct`, familia `smollm`, licenca `apache-2.0`
- Fonte da configuracao: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct/resolve/main/config.json
- Status de proveniencia: `FETCHED`
- Parametros derivados da IR: 361,821,120 | publicados: 361,821,120
- Baseline de hardware: `h100-sxm` — picos densos de datasheet do fabricante; eficiencia e custo assumidos
- Pesos de score: v1.0 (UNCALIBRATED — nenhum caso real de tape-out alimentou estes pesos ainda)
- Priors de quantizacao: v1.0

## Anexo D — Todas as afirmacoes emitidas

| Afirmacao | Valor | Status | Lacunas |
|---|---|---|---|
| `smollm2-360m-instruct.params` | 361821120 params | `MODEL` | G-001 |
| `smollm2-360m-instruct.serving.decode_time_share` | 0.9729 fracao do tempo de requisicao | `CONDITIONAL_RESULT` | G-003, G-009 |
| `smollm2-360m-instruct.serving.energy_per_token` | 0.3585 J/token gerado | `CONDITIONAL_RESULT` | G-003, G-004, G-009 |
| `smollm2-360m-instruct.decode.tokens_per_s` | 3,251 tok/s | `CONDITIONAL_RESULT` | G-003 |
| `smollm2-360m-instruct.decode.memory_bound_share` | 0.9963 fracao do tempo | `CONDITIONAL_RESULT` | G-003 |
| `smollm2-360m-instruct.decode.arith_intensity` | 1.234 FLOP/byte | `CONDITIONAL_RESULT` | G-003 |
| `smollm2-360m-instruct.decode.energy_per_token` | 0.3488 J/token | `CONDITIONAL_RESULT` | G-003, G-004 |
| `quant.sensitivity.memory_reduction` | 0.4999 fracao | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.speedup` | 1.782 x sobre baseline | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.quality_delta` | — perplexidade / acuracia | `OPEN_GAP` | G-002 |
| `quant.reachable_cost_share.int4` | 0.645 fracao do tempo | `CONDITIONAL_RESULT` | G-002, G-003 |
| `smollm2-360m-instruct.partition.hardened_share` | 0 fracao do tempo | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `smollm2-360m-instruct.partition.amdahl_ceiling` | 1 x sobre baseline | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `partition.claim_check` | 1 x (teto do sistema) | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `economics.breakeven_years.p50` | — anos | `OPEN_GAP` | G-001 |
| `economics.p_breakeven_before_obsolescence` | — probabilidade | `OPEN_GAP` | G-001 |
| `economics.die_area_mm2.p50` | — mm2 | `OPEN_GAP` | G-001 |
| `SRS.smollm2-360m-instruct` | 0.2093 score SRS | `OPEN_GAP` | G-001, G-002, G-003, G-006, G-009 |
| `readiness.rank_stability` | 0.715 fracao das amostras com mesmo top-1 | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `stability.smollm.exact` | — fracao de blocos preservados | `OPEN_GAP` | G-006 |

---

_DOUVRAS Labs — Muitas formas. Uma estrutura._
