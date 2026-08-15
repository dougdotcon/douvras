---
artifact: SILICON_READINESS_ASSESSMENT
model: qwen2.5-7b
run_id: 20260815T000033Z
generated_at: 2026-08-15T00:00:33+00:00
method: DOUVRAS 2.0
cycle: C-001
weakest_status: OPEN_GAP
recommendation: software
decidable: False
---

# Silicon Readiness Assessment — qwen2.5-7b

> Emitido pelo DOUVRAS Silicon Atlas. Todo numero deste documento carrega status epistemico.
> Nenhum resultado e mais forte que sua dependencia mais fraca: **OPEN_GAP**.

## 1. Pergunta principal

Quais subgrafos de inferencia de **qwen2.5-7b** sao simultaneamente estaveis, dominantes em custo e tolerantes a baixa precisao o suficiente para justificar especializacao em hardware — e a partir de qual volume isso se paga?

## 2. Afirmacao principal

Sob as condicoes declaradas, a regiao endurecivel de **qwen2.5-7b** cobre **0.0%** do custo de servico, o que limita o ganho de sistema a **1.00x** numa arquitetura hibrida. Nao existe break-even a reportar: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular, de modo que nenhum acelerador foi dimensionado para 1e+13 tokens/ano.

**Recomendacao: manter em software; nenhuma especializacao se justifica com a evidencia atual.**

Status da afirmacao: `OPEN_GAP` (elo mais fraco da cadeia de evidencia).

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
  observado: familia sem transicao temporal no corpus (2 versao(oes)): nao avaliavel  
  **nao disparado**
- **F2** — o padrao mais custoso muda de identidade entre versoes  
  observado: bloco mais custoso 'mlp' (papel gate_proj, 26.5% do custo): E = 0.09  
  **DISPARADO**
- **F3** — top-1 do ranking troca sob perturbacao de +-20% dos pesos, ou vence por margem menor que o ruido (criterio reforcado apos CE-001)  
  observado: estabilidade do top-1 = 1.000 (limite 0.95); margem = 0.0128 contra ruido 0.0262  
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
| tokens/s | 37,175 | 187.4 |
| intensidade aritmetica (FLOP/byte) | 608.7 | 1.06 |
| ponto de inflexao do dispositivo | 253 | 92 |
| tempo limitado por memoria | 15.7% | 99.9% |
| energia por token | 30.50 mJ | 6050.1 mJ |

O decode consome 98.0% do tempo da requisicao. Toda decisao de
hardening abaixo e ponderada por essa mistura, nao por FLOPs isolados.

### Onde o custo esta

| Papel | Participacao na requisicao |
|---|---|
| gate_proj | 26.55% |
| up_proj | 26.55% |
| down_proj | 26.55% |
| lm_head | 7.49% |
| q_proj | 5.02% |
| o_proj | 5.02% |
| kv_read | 0.91% |
| k_proj | 0.72% |

### Candidatos a endurecimento (LHS)

| Papel | Bloco | Custo | Instancias/token | Precisao | LHS |
|---|---|---|---|---|---|
| gate_proj | mlp | 26.5% | 28 | int4 | 0.507 |
| up_proj | mlp | 26.5% | 28 | int4 | 0.507 |
| q_proj | attention | 5.0% | 28 | int8 | 0.494 |
| down_proj | mlp | 26.5% | 28 | int4 | 0.492 |
| v_proj | attention | 0.7% | 28 | int8 | 0.487 |
| k_proj | attention | 0.7% | 28 | int8 | 0.480 |
| o_proj | attention | 5.0% | 28 | int4 | 0.456 |
| lm_head | head | 7.5% | 1 | int8 | 0.403 |

### Particao recomendada

```text
FPGA/eFPGA: 98.6% do custo
  ├── gate_proj             26.5%  regular e quantizavel, porem LHS=0.51 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  ├── up_proj               26.5%  regular e quantizavel, porem LHS=0.51 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  ├── down_proj             26.5%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  ├── lm_head                7.5%  regular e quantizavel, porem LHS=0.40 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  ├── q_proj                 5.0%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  ├── o_proj                 5.0%  regular e quantizavel, porem LHS=0.46 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  ├── v_proj                 0.7%  regular e quantizavel, porem LHS=0.49 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
  └── k_proj                 0.7%  regular e quantizavel, porem LHS=0.48 < 0.55; E=0.09 < 0.6: prototipar antes de fixar
CPU/GPU: 0.9% do custo
  └── kv_read                0.9%  LHS=0.36 < 0.55; E=0.09 < 0.6; Q=0.00 < 0.6
```

Nivel de especializacao implicado: **3 — acelerador por arquitetura**.
Regiao fixa cobre **0.0%** do custo da requisicao.

**Teto de Amdahl da particao: 1.00x.**
Um ganho de 100x e inalcancavel nesta particao mesmo com aceleracao infinita na regiao fixa: exigiria mover tambem a regiao programavel (100.0% do custo) para o mesmo silicio.

### Quantizacao

Plano por sensibilidade reduz o **trafego de leitura de pesos por passo** em
**50.0%** (14.14 GB para
7.07 GB por passo de decode), com aceleracao estimada de
1.98x. O **footprint residente** e grandeza distinta:
15.23 GB, contra
80 GB de capacidade
(cabe,
folga +81.0%).

A perda de qualidade correspondente **nao foi medida** (`G-002`).

### PPA e economia — distribuicoes, nao pontos

A regiao fixa ficou **vazia** sob a politica de particionamento vigente: regiao fixa vazia (nenhum FLOP endurecido e nenhum peso a fixar): nao ha ponto de projeto a simular. Nenhum acelerador foi dimensionado, nenhum NRE foi estimado, e nao existe break-even — nem finito, nem infinito: nao ha objeto a amortizar.

Consequencia registrada: os fatores **P** (ganho por watt), **R** (receita) e **N** (risco de NRE) do SRS entram como **zero declarado**, e o falsificador **F4** fica *nao avaliavel*. Publicar percentis de area, NRE ou break-even aqui seria descrever um objeto inexistente — foi exatamente o defeito retratado em `R-002`.

Isto **e** o resultado: para qwen2.5-7b, o bloco que domina o custo (mlp, 26.5% do tempo) tem estabilidade estrutural E = 0.09, abaixo do limite da politica. O gasto em mascara nao tem o que financiar. A decisao economica so passa a existir se essa estabilidade subir — por escopo declarado mais estreito, por observacao de mais versoes, ou por calibracao da politica contra casos reais (`G-011`).

### Silicon Readiness Score

**SRS = 0.227** (OPEN_GAP) -> banda **software**

| Fator | Valor | Peso | Contribuicao | Status |
|---|---|---|---|---|
| A — arch_stability | 0.000 | +0.15 | +0.0000 | `OPEN_GAP` |
| H — concentration | 0.223 | +0.15 | +0.0335 | `CONDITIONAL_RESULT` |
| T — throughput | 0.667 | +0.15 | +0.1000 | `ASSUMPTION` |
| P — perf_per_watt | 0.000 | +0.15 | +0.0000 | `CONDITIONAL_RESULT` |
| Q — low_precision | 0.687 | +0.10 | +0.0687 | `ASSUMPTION` |
| D — data_availability | 0.750 | +0.10 | +0.0750 | `ASSUMPTION` |
| C — codesign | 1.000 | +0.10 | +0.1000 | `MODEL` |
| R — revenue_potential | 0.000 | +0.10 | +0.0000 | `CONDITIONAL_RESULT` |
| O — obsolescence_risk | 1.000 | -0.15 | -0.1500 | `OPEN_GAP` |
| N — nre_risk | 0.000 | -0.10 | -0.0000 | `CONDITIONAL_RESULT` |

### Efeito do escopo de comparacao

_Familia sem transicao temporal no corpus (2 versao(oes)): o efeito de escopo nao pode ser medido, e a estabilidade estrutural entra como lacuna aberta (`G-006`), nao como valor otimista._

### Alcance cross-familia

Nenhum bloco exato deste modelo reaparece em outra familia do corpus (alcance maximo 0.11). Um bloco de IP construido a partir dele atende, hoje, um unico modelo.

### Estabilidade do proprio score

Perturbando os pesos em +-20% (2,000 amostras):
top-1 estavel em **100.0%** das amostras, top-3 em
65.9%, banda de decisao do SRS estavel em
99.9%. Fator dominante: `R`.

Dispersao dos scores: 0.1465. Largura do ruido induzido pelos pesos:
0.0262. **Diagnostico: top-1 estavel, mas a margem sobre o concorrente (0.0128) nao supera o ruido dos pesos (0.0262): a ordem pode ser artefato.**

Disputam a primeira posicao, dentro do ruido: `gate_proj`, `up_proj`, `q_proj`, `down_proj`, `v_proj`. Entre eles, **70% do peso do LHS esta em fatores identicos** — estabilidade, regularidade, previsibilidade de memoria, volume e vida util sao os mesmos para toda projecao linear do mesmo modelo. Sobre o conjunto completo de candidatos o peso inerte e 55%.

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
  "model": "qwen2.5-7b",
  "family": "qwen",
  "version": "2.5-7B",
  "release_date": "2024-09-19",
  "architecture_class": "decoder_transformer",
  "attention": "gqa",
  "gqa_ratio": 7,
  "head_dim": 128,
  "layers": 28,
  "hidden_size": 3584,
  "intermediate_size": 18944,
  "mlp": "swiglu",
  "mlp_ratio": 5.2857,
  "normalization": "rmsnorm",
  "norms_per_layer": 2,
  "position": "rope",
  "rope_theta": 1000000.0,
  "routing": "dense",
  "vocab_size": 152064,
  "tied_embeddings": false,
  "sliding_window": 131072,
  "params": 7615616512,
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

## Anexo B — Estabilidade da familia `qwen`

Versoes comparadas: qwen2.5-7b -> qwen2.5-14b

Transicoes temporais observadas: **0** · pares de escala (mesma data, tamanhos diferentes) ignorados: qwen2.5-7b vs qwen2.5-14b

| Nivel de identidade | Estabilidade media |
|---|---|
| topologia | nao observada (`G-006`) |
| padrao (proporcoes) | nao observada (`G-006`) |
| exato (mesmo circuito) | nao observada (`G-006`) |

Taxa de mudanca estrutural observada: nao estimavel: sem transicao temporal no corpus (`G-006`)

_Sem transicoes de versao no corpus para esta familia._

## Anexo C — Proveniencia

- Modelo: `qwen2.5-7b`, familia `qwen`, licenca `apache-2.0`
- Fonte da configuracao: https://huggingface.co/Qwen/Qwen2.5-7B/resolve/main/config.json
- Status de proveniencia: `TRANSCRIBED_UNVERIFIED` (lacuna G-008 aberta)
- Parametros derivados da IR: 7,615,616,512 | publicados: 7,615,616,512
- Baseline de hardware: `h100-sxm` — picos densos de datasheet do fabricante; eficiencia e custo assumidos
- Pesos de score: v1.0 (UNCALIBRATED — nenhum caso real de tape-out alimentou estes pesos ainda)
- Priors de quantizacao: v1.0

## Anexo D — Todas as afirmacoes emitidas

| Afirmacao | Valor | Status | Lacunas |
|---|---|---|---|
| `qwen2.5-7b.params` | 7615616512 params | `ASSUMPTION` | G-001, G-008 |
| `qwen2.5-7b.serving.decode_time_share` | 0.9802 fracao do tempo de requisicao | `CONDITIONAL_RESULT` | G-003, G-009 |
| `qwen2.5-7b.serving.energy_per_token` | 6.172 J/token gerado | `CONDITIONAL_RESULT` | G-003, G-004, G-009 |
| `qwen2.5-7b.decode.tokens_per_s` | 187.4 tok/s | `CONDITIONAL_RESULT` | G-003 |
| `qwen2.5-7b.decode.memory_bound_share` | 0.9993 fracao do tempo | `CONDITIONAL_RESULT` | G-003 |
| `qwen2.5-7b.decode.arith_intensity` | 1.055 FLOP/byte | `CONDITIONAL_RESULT` | G-003 |
| `qwen2.5-7b.decode.energy_per_token` | 6.05 J/token | `CONDITIONAL_RESULT` | G-003, G-004 |
| `quant.sensitivity.memory_reduction` | 0.5 fracao | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.speedup` | 1.978 x sobre baseline | `CONDITIONAL_RESULT` | G-002, G-003 |
| `quant.sensitivity.quality_delta` | — perplexidade / acuracia | `OPEN_GAP` | G-002 |
| `quant.reachable_cost_share.int4` | 0.8483 fracao do tempo | `CONDITIONAL_RESULT` | G-002, G-003 |
| `qwen2.5-7b.partition.hardened_share` | 0 fracao do tempo | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `qwen2.5-7b.partition.amdahl_ceiling` | 1 x sobre baseline | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `partition.claim_check` | 1 x (teto do sistema) | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `economics.breakeven_years.p50` | — anos | `OPEN_GAP` | G-001 |
| `economics.p_breakeven_before_obsolescence` | — probabilidade | `OPEN_GAP` | G-001 |
| `economics.die_area_mm2.p50` | — mm2 | `OPEN_GAP` | G-001 |
| `SRS.qwen2.5-7b` | 0.2272 score SRS | `OPEN_GAP` | G-001, G-002, G-003, G-006, G-008, G-009 |
| `readiness.rank_stability` | 1 fracao das amostras com mesmo top-1 | `OPEN_GAP` | G-001, G-002, G-003, G-006 |
| `stability.qwen.exact` | — fracao de blocos preservados | `OPEN_GAP` | G-006 |

---

_DOUVRAS Labs — Muitas formas. Uma estrutura._
