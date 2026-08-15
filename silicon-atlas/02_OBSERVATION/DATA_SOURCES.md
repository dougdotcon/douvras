---
artifact: DATA_SOURCES
cycle: C-001
---

# Fontes de dados

Cada fonte declara **tipo de evidência** (Método §4.2). As categorias não se misturam.

## Corpus de modelos — `corpus/models/*.json`

| Modelo | Família | Release | Licença | Origem | Proveniência |
|---|---|---|---|---|---|
| llama-2-7b | llama | 2023-07-18 | llama2 | HF `meta-llama/Llama-2-7b-hf` | transcrito |
| llama-3-8b | llama | 2024-04-18 | llama3 | HF `meta-llama/Meta-Llama-3-8B` | transcrito |
| llama-3.1-8b | llama | 2024-07-23 | llama3.1 | HF `meta-llama/Llama-3.1-8B` | transcrito |
| mistral-7b-v0.1 | mistral | 2023-09-27 | apache-2.0 | HF `mistralai/Mistral-7B-v0.1` | transcrito |
| mixtral-8x7b-v0.1 | mistral | 2023-12-11 | apache-2.0 | HF `mistralai/Mixtral-8x7B-v0.1` | transcrito |
| qwen2.5-7b | qwen | 2024-09-19 | apache-2.0 | HF `Qwen/Qwen2.5-7B` | transcrito |
| qwen2.5-14b | qwen | 2024-09-19 | apache-2.0 | HF `Qwen/Qwen2.5-14B` | transcrito |
| phi-3-mini-4k | phi | 2024-04-23 | mit | HF `microsoft/Phi-3-mini-4k-instruct` | transcrito |
| gemma-2-9b | gemma | 2024-06-27 | gemma | HF `google/gemma-2-9b` | transcrito |

**Tipo**: `secondary_analysis` — configurações transcritas de publicação, **não baixadas** nesta
execução. Lacuna `G-008`, fechável com `atlas registry verify <modelo> --repo <org/nome>`.

### Verificação indireta já realizada

A contagem de parâmetros derivada analiticamente de cada configuração é comparada com o valor
publicado pelos autores. Os 9 modelos batem **ao parâmetro** (erro 0,00 %). Um campo transcrito
errado — largura, número de camadas, cabeças KV, viés, amarração de embeddings — quebraria a
igualdade exata.

Isso é evidência forte de fidelidade da transcrição, e **não substitui** a verificação de hash
upstream: um erro que se cancelasse entre dois campos passaria despercebido.

## Baselines de hardware — `config/devices.json`

**Tipo**: `vendor_report` para picos e banda; `ASSUMPTION` para eficiências e custo horário.
Congelado como `BASELINE-2026-08-03` (Método §6.2). Alterar exige nova comparação.

## Priors de quantização — `config/quantization_priors.v1.json`

**Tipo**: `ASSUMPTION` derivada de consenso de literatura. **Nenhuma medição própria.**
Lacuna `G-002`, a mais cara do projeto porque entra direto no score de decisão.

## Priors econômicos — `config/economics_priors.v1.json`

**Tipo**: `ASSUMPTION` — faixas públicas de custo de máscara, wafer, densidade e empacotamento,
expressas como distribuições p10/p90. Lacunas `G-005` e `G-007`.

## Literatura e relato de fabricante

Registrados em [EVIDENCE_LEDGER](../00_GOVERNANCE/EVIDENCE_LEDGER.yaml) como `E-002`
(demonstrador Taalas HC1 — `vendor_report`, não reproduzido), `E-003` e `E-005` (`literature`).

Regra de uso declarada no próprio ledger: `E-002` pode ser citado como **demonstração de
existência**, nunca como **medida de ganho**.

## Ausência de evidência declarada

`E-004` registra que não existe, no início do ciclo, corpus público normalizado de evolução
estrutural de modelos abertos. A construção desse corpus é entregável do ciclo — e ausência de
evidência não é evidência de ausência.
