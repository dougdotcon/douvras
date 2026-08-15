---
artifact: INVARIANT_MAP
run_id: 20260815T004803Z
generated_by: scripts/run_cycle.py
status: COMPUTATIONAL_EVIDENCE
---

# Mapa de invariantes

> Arquivo **gerado**. Editar a mao apaga a rastreabilidade. Para mudar o conteudo,
> mude o corpus ou o criterio e reexecute `python scripts/run_cycle.py`.

Corpus: 9 modelos — gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b

Tres niveis de identidade (ADR-0003). A mesma estrutura pode ser invariante num nivel
e variavel no seguinte; e a distincao entre reusar um *projeto* e reusar um *circuito*.

## Nivel `topology` — Topologia

_mesmo datapath, qualquer escala_

- padroes distintos: **5**
- compartilhados por mais de um modelo: **2**
- que atravessam familias: **2**

| Candidato a invariante | Modelos | Cobertura | Instancias | Custo medio | Falhas conhecidas | Status |
|---|---|---|---|---|---|---|
| attention [topology] 1b843e6d | 8 | 0.89 | 268 | 29.7% | gemma-2-9b | HYPOTHESIS |
| mlp [topology] 0c8cab6e | 7 | 0.78 | 236 | 64.4% | gemma-2-9b, mixtral-8x7b-v0.1 | HYPOTHESIS |
| moe [topology] 0bf1e11f | 1 | 0.11 | 32 | 81.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [topology] 9dbd8b8d | 1 | 0.11 | 42 | 60.7% | llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [topology] 334da477 | 1 | 0.11 | 42 | 30.6% | llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |

## Nivel `pattern` — Padrao

_mesmas proporcoes de shape, outra escala_

- padroes distintos: **15**
- compartilhados por mais de um modelo: **2**
- que atravessam familias: **2**

| Candidato a invariante | Modelos | Cobertura | Instancias | Custo medio | Falhas conhecidas | Status |
|---|---|---|---|---|---|---|
| mlp [pattern] 322fb3ea | 3 | 0.33 | 96 | 66.7% | gemma-2-9b, llama-2-7b, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [pattern] 410efbb6 | 3 | 0.33 | 96 | 24.7% | gemma-2-9b, llama-2-7b, mistral-7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| moe [pattern] 16fefe36 | 1 | 0.11 | 32 | 81.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [pattern] 10a85f9e | 1 | 0.11 | 28 | 72.2% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b | HYPOTHESIS |
| mlp [pattern] 167dabef | 1 | 0.11 | 48 | 63.6% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-7b | HYPOTHESIS |
| mlp [pattern] 6615ec81 | 1 | 0.11 | 42 | 60.7% | llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [pattern] 803150f1 | 1 | 0.11 | 32 | 58.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [pattern] c9eb791d | 1 | 0.11 | 32 | 56.3% | gemma-2-9b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [pattern] bde81064 | 1 | 0.11 | 32 | 42.0% | gemma-2-9b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [pattern] 9b8711e0 | 1 | 0.11 | 32 | 39.1% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [pattern] 599d73a3 | 1 | 0.11 | 48 | 31.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-7b | HYPOTHESIS |
| attention [pattern] 7ff12282 | 1 | 0.11 | 32 | 29.6% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |

## Nivel `exact` — Exato

_mesmo circuito, sem re-sintese_

- padroes distintos: **15**
- compartilhados por mais de um modelo: **2**
- que atravessam familias: **2**

| Candidato a invariante | Modelos | Cobertura | Instancias | Custo medio | Falhas conhecidas | Status |
|---|---|---|---|---|---|---|
| mlp [exact] 77aa0322 | 3 | 0.33 | 96 | 66.7% | gemma-2-9b, llama-2-7b, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [exact] da9fee83 | 3 | 0.33 | 96 | 24.7% | gemma-2-9b, llama-2-7b, mistral-7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| moe [exact] d2089986 | 1 | 0.11 | 32 | 81.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [exact] 6ab254d6 | 1 | 0.11 | 28 | 72.2% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b | HYPOTHESIS |
| mlp [exact] ba062ab2 | 1 | 0.11 | 48 | 63.6% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-7b | HYPOTHESIS |
| mlp [exact] 2bb8250f | 1 | 0.11 | 42 | 60.7% | llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [exact] 39fd2e0e | 1 | 0.11 | 32 | 58.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| mlp [exact] 3c85c1d8 | 1 | 0.11 | 32 | 56.3% | gemma-2-9b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [exact] 585d965c | 1 | 0.11 | 32 | 42.0% | gemma-2-9b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [exact] c5f04d71 | 1 | 0.11 | 32 | 39.1% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |
| attention [exact] 9189ec0f | 1 | 0.11 | 48 | 31.5% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mistral-7b-v0.1, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-7b | HYPOTHESIS |
| attention [exact] 5702f295 | 1 | 0.11 | 32 | 29.6% | gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b, mixtral-8x7b-v0.1, phi-3-mini-4k, qwen2.5-14b, qwen2.5-7b | HYPOTHESIS |

## Leitura

A cobertura cai monotonicamente de `topology` para `exact`, e a distancia entre os dois
extremos e exatamente o risco que um projeto de silicio assume. Um roadmap que cita
estabilidade no nivel de topologia para justificar mascara esta usando a evidencia errada.

Casos que nao se encaixam permanecem listados na coluna de falhas conhecidas. Eles nao
sao ruido: cada um delimita a fronteira de validade do candidato (Metodo 4.4).
