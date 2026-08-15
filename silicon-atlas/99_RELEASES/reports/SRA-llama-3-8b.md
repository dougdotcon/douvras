---
artifact: SILICON_READINESS_ASSESSMENT
model: llama-3-8b
run_id: 20260815T004804Z
generated_at: 2026-08-15T00:48:04+00:00
method: DOUVRAS 2.0
cycle: C-001
weakest_status: ASSUMPTION
recommendation: software
decidable: False
---

# Silicon Readiness Assessment — llama-3-8b

> Emitido pelo DOUVRAS Silicon Atlas. Todo numero deste documento carrega status epistemico.
> Nenhum resultado e mais forte que sua dependencia mais fraca: **ASSUMPTION**.

## 1. Pergunta principal

Quais subgrafos de inferencia de **llama-3-8b** sao simultaneamente estaveis, dominantes em custo e tolerantes a baixa precisao o suficiente para justificar especializacao em hardware — e a partir de qual volume isso se paga?

## 2. Afirmacao principal

Sob as condicoes declaradas, a regiao endurecivel de **llama-3-8b** cobre **0.0%** do custo de servico, o que limita o ganho de sistema a **1.00x** numa arquitetura hibrida. Nao existe break-even a reportar: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular, de modo que nenhum acelerador foi dimensionado para 1e+13 tokens/ano.

**Recomendacao: manter em software; nenhuma especializacao se justifica com a evidencia atual.**

Status da afirmacao: `ASSUMPTION` (elo mais fraco da cadeia de evidencia).

**Ressalvas que qualificam esta recomendacao:**

1. **100% do custo** esta em operadores regulares e quantizaveis, barrados *apenas pela estabilidade*. Acao util: prototipar em FPGA para medir o ganho real antes de qualquer compromisso de mascara.
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

Lacunas abertas que limitam o status de tudo acima: `G-001`, `G-002`, `G-003`, `G-004`, `G-006`, `G-008`, `G-009`

## 5. Criterios de falha (declarados antes da execucao)

- **F1** — nenhum padrao com cobertura >= 0.80 entre versoes da familia  
  observado: estabilidade exata entre versoes = 0.50; alcance cross-familia do melhor padrao = 0.33  
  **DISPARADO**
- **F2** — o padrao mais custoso muda de identidade entre versoes  
  observado: bloco mais custoso 'mlp' (papel gate_proj, 24.5% do custo): E = 0.48  
  **DISPARADO**
- **F3** — top-1 do ranking troca sob perturbacao de +-20% dos pesos, ou vence por margem menor que o ruido (criterio reforcado apos CE-001)  
  observado: estabilidade do top-1 = 0.961 (limite 0.95); margem = 0.0067 contra ruido 0.0282  
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
| tokens/s | 34,808 | 174.7 |
| intensidade aritmetica (FLOP/byte) | 624.7 | 1.06 |
| ponto de inflexao do dispositivo | 253 | 92 |
| tempo limitado por memoria | 15.0% | 99.9% |
| energia por token | 32.58 mJ | 6490.9 mJ |

O decode consome 98.0% do tempo da requisicao. Toda decisao de
hardening abaixo e ponderada por essa mistura, nao por FLOPs isolados.

### Onde o custo esta

| Papel | Participacao na requisicao |
|---|---|
| gate_proj | 24.46% |
| up_proj | 24.46% |
| down_proj | 24.46% |
| q_proj | 6.99% |
| o_proj | 6.99% |
| lm_head | 6.73% |
| kv_read | 1.93% |
| k_proj | 1.75% |

### Candidatos a endurecimento (LHS)

| Papel | Bloco | Custo | Instancias/token | Precisao | LHS |
|---|---|---|---|---|---|
| gate_proj | mlp | 24.5% | 32 | int4 | 0.587 |
| up_proj | mlp | 24.5% | 32 | int4 | 0.587 |
| q_proj | attention | 7.0% | 32 | int8 | 0.580 |
| v_proj | attention | 1.7% | 32 | int8 | 0.572 |
| down_proj | mlp | 24.5% | 32 | int4 | 0.572 |
| k_proj | attention | 1.7% | 32 | int8 | 0.565 |
| o_proj | attention | 7.0% | 32 | int4 | 0.543 |
| lm_head | head | 6.7% | 1 | int8 | 0.490 |

### Particao recomendada

```text
FPGA/eFPGA: 97.6% do custo
  ├── gate_proj             24.5%  regular e quantizavel, porem E=0.48 < 0.6: prototipar antes de fixar
  ├── up_proj               24.5%  regular e quantizavel, porem E=0.48 < 0.6: prototipar antes de fixar
  ├── down_proj             24.5%  regular e quantizavel, porem E=0.48 < 0.6: prototipar antes de fixar
  ├── q_proj                 7.0%  regular e quantizavel, porem E=0.48 < 0.6: prototipar antes de fixar
  ├── o_proj                 7.0%  regular e quantizavel, porem LHS=0.54 < 0.55; E=0.48 < 0.6: prototipar antes de fixar
  ├── lm_head                6.7%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.52 < 0.6: prototipar antes de fixar
  ├── v_proj                 1.7%  regular e quantizavel, porem E=0.48 < 0.6: prototipar antes de fixar
  └── k_proj                 1.7%  regular e quantizavel, porem E=0.48 < 0.6: prototipar antes de fixar
CPU/GPU: 1.9% do custo
  └── kv_read                1.9%  LHS=0.44 < 0.55; E=0.48 < 0.6; Q=0.00 < 0.6
```

Nivel de especializacao implicado: **3 — acelerador por arquitetura**.
Regiao fixa cobre **0.0%** do custo da requisicao.

**Teto de Amdahl da particao: 1.00x.**
Um ganho de 100x e inalcancavel nesta particao mesmo com aceleracao infinita na regiao fixa: exigiria mover tambem a regiao programavel (100.0% do custo) para o mesmo silicio.

### Quantizacao

Plano por sensibilidade reduz o **trafego de leitura de pesos por passo** em
**50.0%** (15.01 GB para
7.51 GB por passo de decode), com aceleracao estimada de
1.96x. O **footprint residente** e grandeza distinta:
16.06 GB, contra
80 GB de capacidade
(cabe,
folga +79.9%).

A perda de qualidade correspondente **nao foi medida** (`G-002`).

### PPA e economia — distribuicoes, nao pontos

A regiao fixa ficou **vazia** sob a politica de particionamento vigente: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular. Nenhum acelerador foi dimensionado, nenhum NRE foi estimado, e nao existe break-even — nem finito, nem infinito: nao ha objeto a amortizar.

Consequencia registrada: os fatores **P** (ganho por watt), **R** (receita) e **N** (risco de NRE) do SRS entram como **zero declarado**, e o falsificador **F4** fica *nao avaliavel*. Publicar percentis de area, NRE ou break-even aqui seria descrever um objeto inexistente — foi exatamente o defeito retratado em `R-002`.

Isto **e** o resultado: para llama-3-8b, o bloco que domina o custo (mlp, 24.5% do tempo) tem estabilidade estrutural E = 0.48, abaixo do limite da politica. O gasto em mascara nao tem o que financiar. A decisao economica so passa a existir se essa estabilidade subir — por escopo declarado mais estreito, por observacao de mais versoes, ou por calibracao da politica contra casos reais (`G-011`).

### Silicon Readiness Score

**SRS = 0.276** (ASSUMPTION) -> banda **software**

| Fator | Valor | Peso | Contribuicao | Status |
|---|---|---|---|---|
| A — arch_stability | 0.500 | +0.15 | +0.0750 | `COMPUTATIONAL_EVIDENCE` |
| H — concentration | 0.196 | +0.15 | +0.0294 | `CONDITIONAL_RESULT` |
| T — throughput | 0.667 | +0.15 | +0.1000 | `ASSUMPTION` |
| P — perf_per_watt | 0.000 | +0.15 | +0.0000 | `CONDITIONAL_RESULT` |
| Q — low_precision | 0.684 | +0.10 | +0.0684 | `ASSUMPTION` |
| D — data_availability | 0.500 | +0.10 | +0.0500 | `ASSUMPTION` |
| C — codesign | 1.000 | +0.10 | +0.1000 | `MODEL` |
| R — revenue_potential | 0.000 | +0.10 | +0.0000 | `CONDITIONAL_RESULT` |
| O — obsolescence_risk | 0.981 | -0.15 | -0.1471 | `CONDITIONAL_RESULT` |
| N — nre_risk | 0.000 | -0.10 | -0.0000 | `CONDITIONAL_RESULT` |

### Efeito do escopo de comparacao

A estabilidade estrutural depende de quais versoes entram na comparacao — e essa escolha e do
analista, nao do dado.

| Escopo | Estabilidade exata |
|---|---|
| media sobre 2 transicao(oes) da familia `llama` | 0.50 |
| apenas a transicao mais recente (llama-3-8b -> llama-3.1-8b) | 1.00 |

Diferenca: +0.50. O escopo **muda a decisao**: os dois numeros ficam em lados opostos do limite de estabilidade da politica de particionamento.

Os scores deste relatorio usam a **media da familia** — a leitura conservadora. Um cliente cujo
compromisso e apenas com a linha mais recente deve reexecutar declarando esse escopo, e o
relatorio resultante sera outro documento, com outra recomendacao.

### Alcance cross-familia

Blocos deste modelo cujo circuito **exato** ja serve outra familia — o que define o mercado
enderecavel de um bloco de IP, e nao se confunde com estabilidade temporal:

| Bloco | Cobertura do corpus | Modelos atendidos |
|---|---|---|
| attention | 0.33 | llama-3-8b, llama-3.1-8b, mixtral-8x7b-v0.1 |
| mlp | 0.33 | llama-3-8b, llama-3.1-8b, mistral-7b-v0.1 |

Alcance maximo: **33%** de um corpus de 9 modelos. Um bloco
estavel no tempo e util a um cliente; um bloco com alcance cross-familia e util a um mercado.
As duas propriedades sao independentes e ambas precisam ser verdadeiras para justificar IP.

### Estabilidade do proprio score

Perturbando os pesos em +-20% (2,000 amostras):
top-1 estavel em **96.1%** das amostras, top-3 em
94.8%, banda de decisao do SRS estavel em
80.3%. Fator dominante: `R`.

Dispersao dos scores: 0.1418. Largura do ruido induzido pelos pesos:
0.0282. **Diagnostico: top-1 estavel, mas a margem sobre o concorrente (0.0067) nao supera o ruido dos pesos (0.0282): a ordem pode ser artefato.**

Disputam a primeira posicao, dentro do ruido: `gate_proj`, `up_proj`, `q_proj`, `v_proj`, `down_proj`, `k_proj`. Entre eles, **70% do peso do LHS esta em fatores identicos** — estabilidade, regularidade, previsibilidade de memoria, volume e vida util sao os mesmos para toda projecao linear do mesmo modelo. Sobre o conjunto completo de candidatos o peso inerte e 35%.

A ordem acaba decidida apenas por `E`, `F`, `Q`, `V`, que se cancelam parcialmente: o papel com mais custo tende a ter tolerancia a quantizacao menor.

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
- A taxa de obsolescencia extrapola 3 versao(oes) de uma familia
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
  "model": "llama-3-8b",
  "family": "llama",
  "version": "3.0",
  "release_date": "2024-04-18",
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
  "rope_theta": 500000.0,
  "routing": "dense",
  "vocab_size": 128256,
  "tied_embeddings": false,
  "sliding_window": null,
  "params": 8030261248,
  "quantization_candidates": [
    "int8",
    "int4",
    "ternary"
  ],
  "dynamic_regions": [
    "head"
  ],
  "distinct_layer_patterns": 2
}
```

## Anexo B — Estabilidade da familia `llama`

Versoes comparadas: llama-2-7b -> llama-3-8b -> llama-3.1-8b

Transicoes temporais observadas: **2**

| Nivel de identidade | Estabilidade media |
|---|---|
| topologia | 1.000 |
| padrao (proporcoes) | 0.500 |
| exato (mesmo circuito) | 0.500 |

Taxa de mudanca estrutural observada: 0.98 por ano

**llama-2-7b -> llama-3-8b** (275 dias) — estabilidade exata 0.00, padrao 0.00, topologia 1.00
  - `intermediate_size`: 11008 -> 14336
  - `num_key_value_heads`: 32 -> 8
  - `vocab_size`: 32000 -> 128256
  - `max_position_embeddings`: 4096 -> 8192
  - `rope_theta`: 10000.0 -> 500000.0

**llama-3-8b -> llama-3.1-8b** (96 dias) — estabilidade exata 1.00, padrao 1.00, topologia 1.00
  - `max_position_embeddings`: 8192 -> 131072

## Anexo C — Proveniencia

- Modelo: `llama-3-8b`, familia `llama`, licenca `llama3`
- Fonte da configuracao: https://huggingface.co/meta-llama/Meta-Llama-3-8B/resolve/main/config.json
- Status de proveniencia: `TRANSCRIBED_UNVERIFIED` (lacuna G-008 aberta)
- Parametros derivados da IR: 8,030,261,248 | publicados: 8,030,261,248
- Baseline de hardware: `h100-sxm` — picos densos de datasheet do fabricante; eficiencia e custo assumidos
- Pesos de score: v1.0 (UNCALIBRATED — nenhum caso real de tape-out alimentou estes pesos ainda)
- Priors de quantizacao: v1.0

## Anexo D — Todas as afirmacoes emitidas

| Afirmacao | Valor | Status | Lacunas |
|---|---|---|---|
| `llama-3-8b.params` | 8030261248 params | `ASSUMPTION` | G-001, G-008 |
| `llama-3-8b.serving.decode_time_share` | 0.9803 fracao do tempo de requisicao | `CONDITIONAL_RESULT` | G-003, G-009 |
| `llama-3-8b.serving.energy_per_token` | 6.621 J/token gerado | `CONDITIONAL_RESULT` | G-003, G-004, G-009 |
| `llama-3-8b.decode.tokens_per_s` | 174.7 tok/s | `CONDITIONAL_RESULT` | G-003 |
| `llama-3-8b.decode.memory_bound_share` | 0.9991 fracao do tempo | `CONDITIONAL_RESULT` | G-003 |
| `llama-3-8b.decode.arith_intensity` | 1.059 FLOP/byte | `CONDITIONAL_RESULT` | G-003 |
| `llama-3-8b.decode.energy_per_token` | 6.491 J/token | `CONDITIONAL_RESULT` | G-003, G-004 |
| `quant.sensitivity.memory_reduction` | 0.5 fracao | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.speedup` | 1.958 x sobre baseline | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.quality_delta` | — perplexidade / acuracia | `OPEN_GAP` | G-002 |
| `quant.reachable_cost_share.int4` | 0.8052 fracao do tempo | `CONDITIONAL_RESULT` | G-002, G-003 |
| `llama-3-8b.partition.hardened_share` | 0 fracao do tempo | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `llama-3-8b.partition.amdahl_ceiling` | 1 x sobre baseline | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `partition.claim_check` | 1 x (teto do sistema) | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `economics.breakeven_years.p50` | — anos | `OPEN_GAP` | G-001 |
| `economics.p_breakeven_before_obsolescence` | — probabilidade | `OPEN_GAP` | G-001 |
| `economics.die_area_mm2.p50` | — mm2 | `OPEN_GAP` | G-001 |
| `SRS.llama-3-8b` | 0.2757 score SRS | `ASSUMPTION` | G-001, G-002, G-003, G-006, G-008, G-009 |
| `readiness.rank_stability` | 0.961 fracao das amostras com mesmo top-1 | `ASSUMPTION` | G-001, G-002, G-003, G-006 |
| `stability.llama.exact` | 0.5 fracao de blocos preservados | `COMPUTATIONAL_EVIDENCE` | G-001 |

---

_DOUVRAS Labs — Muitas formas. Uma estrutura._
