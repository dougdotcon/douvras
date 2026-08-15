---
artifact: RETRACTIONS_AND_CORRECTIONS
policy: append-only
---

# Retratações e correções

Este arquivo é **append-only**. Uma retratação nunca é apagada: ela é o registro de que a
evidência derrubou uma afirmação, e é patrimônio intelectual tanto quanto um resultado positivo
(Método §2).

Toda entrada declara: o que foi afirmado, o que a derrubou, o que muda em consequência, e o que
**não** muda.

---

## R-001 — C-006 retratada: o ranking do LHS não sobrevive à perturbação dos pesos

- **Data**: 2026-08-04 · **Ciclo**: C-001 · **Execução**: `RUN:20260804T031734Z`
- **Afirmação retratada**: *"O ranking de candidatos a hardening produzido pelo SRS é estável
  sob perturbação de ±20 % nos pesos do score."* (`CLAIM_LEDGER:C-006`)
- **Status anterior**: `HYPOTHESIS` → **atual**: `RETRACTED`
- **O que derrubou**: o falsificador F3, declarado na `PROBLEM_CHARTER` **antes** da execução,
  disparou em 5 dos 9 modelos do corpus. Diagnóstico completo em
  [CE-001](../04_VALIDATION/COUNTEREXAMPLES/CE-001-lhs-nao-discrimina.md).
- **Quem detectou**: o próprio pipeline (`scripts/run_cycle.py` → `ClaimLedger.record_run`),
  sem intervenção humana.

### O que muda

- Nenhuma recomendação de **priorização entre papéis dentro de um modelo** pode citar o LHS
  como fundamento neste ciclo. Os relatórios já emitidos continuam válidos como registro, mas a
  seção de candidatos deve ser lida como ordenação por participação de custo, não por prontidão.
- Novo gap `G-011` aberto: calibração dos pesos contra casos com desfecho conhecido.
- `SensitivityResult` passou a reportar discriminação, não apenas estabilidade de ranking.

### O que NÃO muda

- A partição, o teto de Amdahl e a economia **não dependem do ranking do LHS**: dependem da
  participação de custo medida e dos limiares de política. Continuam válidos com o status que
  já carregavam.
- A conclusão de que o decode é dominado por memória (`C-003`) é independente e permanece.
- A contagem de parâmetros da IR (`C-007`) é independente e permanece.

### O que teria acontecido sem o falsificador declarado antes

O relatório teria apresentado `gate_proj` como candidato número um com um score de três casas
decimais, e ninguém saberia que `q_proj` assume a primeira posição em 12 % das ponderações
igualmente defensáveis. A recomendação pareceria mais firme do que a evidência permite — que é
precisamente a falha que o Método §6.1 (critério de falha antes do experimento) existe para
impedir.

---

## R-002 — A banda de recomendação de 8 dos 9 relatórios do ciclo C-001 é retirada

- **Data**: 2026-08-04 · **Ciclo**: C-001 · **Execução afetada**: `RUN:20260804T0*`
- **Afirmação retratada**: a recomendação `optimized_kernel` publicada em
  `99_RELEASES/reports/SRA-*.md` para gemma-2-9b, llama-2-7b, llama-3-8b, llama-3.1-8b,
  mistral-7b-v0.1, phi-3-mini-4k, qwen2.5-7b e qwen2.5-14b.
- **O que derrubou**: revisão adversarial externa ao autor (13 agentes, 6 dimensões, verificação
  cética por dimensão), confirmada por medição independente.

### O defeito

O fator `P — perf_per_watt` do SRS valia **1,000** (contribuição +0,15) nos nove modelos. Esse
valor vinha de `energy_gain` entre 2.181× e 25.532×, calculado sobre um acelerador que o **mesmo
relatório**, na seção 6, declara inexistente: *"A região fixa ficou vazia... Nenhum acelerador foi
dimensionado, nenhum NRE foi estimado."*

Dois `np.maximum` transformavam indefinido em finito: `macs_needed` recebia piso de 1 MAC e
`flops_tok` recebia piso de 1 FLOP, produzindo `asic_tokens_per_second ≈ 1,89 × 10⁹` — idêntico
do phi-3 de 3,8 B ao mixtral de 46,7 B, o que já denunciava a fabricação.

### Efeito medido na conclusão

| modelo | SRS publicado | SRS sem o fator fantasma | banda publicada | banda correta |
|---|---|---|---|---|
| phi-3-mini-4k | 0,4148 | 0,2648 | `optimized_kernel` | **`software`** |
| gemma-2-9b | 0,3975 | 0,2475 | `optimized_kernel` | **`software`** |
| llama-3-8b | 0,3553 | 0,2053 | `optimized_kernel` | **`software`** |
| llama-3.1-8b | 0,3553 | 0,2053 | `optimized_kernel` | **`software`** |
| llama-2-7b | 0,3419 | 0,1919 | `optimized_kernel` | **`software`** |
| qwen2.5-7b | 0,3069 | 0,1569 | `optimized_kernel` | **`software`** |
| mistral-7b-v0.1 | 0,3049 | 0,1549 | `optimized_kernel` | **`software`** |
| qwen2.5-14b | 0,3020 | 0,1520 | `optimized_kernel` | **`software`** |
| mixtral-8x7b-v0.1 | 0,2765 | 0,1265 | `software` | `software` (inalterada) |

### O que muda

- As oito bandas acima ficam **retiradas**. Banda vigente até a reexecução: `software`.
- `simulate()` passa a recusar dimensionar acelerador sem ponto de projeto, em vez de fabricar um.
- Os fatores P, R e N passam a valer 0 com nota explícita quando não há projeto — que é o valor
  semanticamente correto: sem projeto não há ganho, não há receita e não há NRE.

### O que NÃO muda

A conclusão de engenharia é a **mesma, e mais forte**: não há caso para máscara em nenhum dos
nove modelos. O erro tornou a recomendação um degrau mais permissiva do que a evidência sustenta,
não menos. A partição, o teto de Amdahl, o perfil roofline e a contagem de parâmetros não dependem
do fator P e permanecem.

### O que este episódio demonstra

O defeito atravessou 102 testes e um portão de emissão que verifica seções obrigatórias,
vocabulário proibido e execução de sensibilidade — porque **nenhum deles verificava coerência
entre seções do mesmo documento**. A seção 6 dizia "nada foi dimensionado" e o Anexo D publicava
área de die e NRE, no mesmo arquivo, no mesmo `run_id`.

Nenhum falsificador declarado cobria essa classe de erro. F1 a F5 vigiam a *conclusão*; nada
vigiava a *consistência interna*. Registrado como `G-012`.

---

## R-003 — "Nenhum NRE foi estimado" era factualmente falso no mesmo `run_id`

- **Data**: 2026-08-04 · **Ciclo**: C-001
- **Afirmação retratada**: a frase da seção 6 dos relatórios com região fixa vazia, e
  simultaneamente os números que ela nega.

`SRA-llama-3.1-8b.md` afirmava que nada fora dimensionado, enquanto `SRA-llama-3.1-8b.json` do
mesmo run publicava `nre_usd.p50 = 55.581.096`, `die_area_mm2.p50 = 149,64`,
`asic_tokens_per_second.p50 = 1,886 × 10⁹` e `energy_gain.p50 = 12.082×`.

O Markdown suprimia; o JSON não. Um consumidor de máquina recebia PPA que o documento humano
negava — a pior combinação possível, porque quem lê o JSON não vê a ressalva.

### Consequência sobre governança já registrada

`01_DELIMITATION/SUCCESS_AND_FAILURE.md` registrava "F4 disparado em 9 de 9 → rota ASIC não
financiável". F4 compara break-even com vida econômica; com região fixa vazia não há break-even a
comparar. **A conclusão continua correta, mas o falsificador que a sustentava disparou sobre um
objeto inexistente.** F4 passa a devolver "não avaliável" nesse caso, e o registro foi corrigido.

---

## R-004 — Estabilidade estrutural 1,000 atribuída a famílias sem nenhuma transição observada

- **Data**: 2026-08-04 · **Ciclo**: C-001

`family_stability` devolvia `1.0` quando a lista de diffs estava vazia. Publicado em
`SRA-gemma-2-9b.md`, Anexo B: *"exato (mesmo circuito) | 1.000"* — na mesma página que declara
*"Sem transições de versão no corpus para esta família"*.

Enquanto isso, mistral e qwen, que **têm** transição medida, recebiam 0,000. O sistema premiava a
ausência de dado e punia a presença.

Agravante: a docstring de `block_role_stability` declarava por escrito a política oposta —
*"o Finding sai com lacuna G-006 aberta em vez de um número otimista"*. O código contradizia a
própria documentação, no mesmo arquivo.

**Defeito conexo**: `qwen2.5-7b` e `qwen2.5-14b` têm a mesma data de release. A ordenação por data
os tratava como transição de versão, publicando `"Versões comparadas: qwen2.5-14b -> qwen2.5-7b"`
— uma comparação de **escala** rotulada como evolução temporal, exatamente o que o ADR-0003
distingue. Corrigido: empate de data não conta como transição.

---

## R-005 — Três afirmações do README não sustentadas pelos artefatos

- **Data**: 2026-08-04

| Afirmação publicada | Realidade medida |
|---|---|
| "77 testes, 5 arquivos" | 102 testes em 6 arquivos no momento da revisão |
| margem do líder "4× a 18× abaixo do ruído" | **1,8× (mistral) a 39,2× (llama-2-7b)** |
| recomendação `optimized_kernel` nos assessments | ver R-002 |

A segunda estava na seção "O que o ciclo C-001 encontrou", apresentada como resultado medido.
Dois modelos ficavam abaixo do piso citado e um acima do dobro do teto. Não é arredondamento: é
um intervalo escrito de memória em vez de calculado.

A conclusão qualitativa — *o LHS não discrimina em nenhum modelo do corpus* — permanece verdadeira
e está agora sustentada pelo intervalo correto.

---

## Modelo de entrada para as próximas

```markdown
## R-XXX — <afirmação> retratada/corrigida

- **Data** · **Ciclo** · **Execução**
- **Afirmação**: <texto original e id no ledger>
- **Status anterior** → **atual**
- **O que derrubou**: <evidência, falsificador, contraexemplo>
- **Quem detectou**: <pipeline, revisor interno, revisor externo>

### O que muda
### O que NÃO muda
```
