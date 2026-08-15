---
artifact: PROBLEM_CHARTER
project: DOUVRAS Silicon Atlas
cycle: C-001
date: 2026-08-03
gate: D0
status: ACTIVE
---

# Carta do Problema — Ciclo C-001

## Pergunta principal

> Dado um modelo de IA aberto e seu histórico de versões, quais subgrafos de inferência são
> simultaneamente **estruturalmente estáveis**, **dominantes em custo** e **tolerantes a baixa
> precisão** o suficiente para justificar especialização em hardware — e a partir de qual volume
> de tokens essa especialização se paga?

Uma frase: **quanto de um modelo deve ser fixado em silício, e a partir de quando isso se paga?**

## Afirmação principal do ciclo

`HYPOTHESIS` — Uma minoria de padrões computacionais (projeções lineares quantizáveis) concentra a
maior parte do custo de inferência e permanece estável entre versões e famílias, enquanto controle,
roteamento e operadores emergentes não permanecem.

## Usuário / sistema afetado

Equipe que precisa decidir, **antes do tape-out**, o nível de especialização (Nível 0–6 da escada
§6.5) de um caminho de inferência. Perde milhões se fixar cedo demais; perde eficiência se nunca fixar.

## Estado atual

A decisão é tomada por analogia ("Transformer é estável"), por número de fabricante
(`OBSERVED_IN_INDUSTRY_DEMO`, não reproduzido) ou por contagem de FLOPs — que ignora movimentação
de memória, a variável que domina o decode.

## Estado desejado

Uma decisão auditável: para cada subgrafo, um score reprodutível, com premissas explícitas,
falsificadores declarados, análise de sensibilidade dos pesos e break-even com incerteza propagada.

## Unidade de análise

O **padrão de subgrafo** (`pattern_hash`) — não o modelo inteiro, não a camada individual.
Justificativa: silício é fabricado por padrão repetido, não por camada nomeada.

## Restrições

- R1 — O MVP não pode exigir GPU, pesos baixados nem `torch` para rodar o caminho principal.
- R2 — Nenhum número pode ser emitido sem `Status` (§3.1 do Método).
- R3 — Pesos de modelo de cliente não saem do ambiente do cliente (§13.6).
- R4 — Ferramenta aberta (Sky130/OpenROAD) é ambiente de aprendizado, não previsão de produção (§18.5).

## Não objetivos (fora de escopo neste ciclo)

- Fabricar, empacotar ou fazer tape-out de qualquer chip.
- Gerar RTL sintetizável pronto para produção.
- Prever PPA de nó avançado com precisão de foundry.
- Afirmar ganho de "100×" em qualquer forma. Ver `CLAIM_LEDGER:C-004`.
- Medir acurácia real pós-quantização (exige pesos e GPU — ver `GAP_REGISTER:G-002`).

## Métricas de sucesso do ciclo

| # | Métrica | Alvo |
|---|---|---|
| M1 | Contagem de parâmetros derivada da IR vs. publicada | erro < 0,5 % em ≥ 3 famílias |
| M2 | Fingerprint invariante a renomeação/índice/batch, sensível a arquitetura | 100 % dos testes |
| M3 | Padrões estáveis detectados entre ≥ 2 versões da mesma família | ≥ 1 padrão com cobertura ≥ 0,80 |
| M4 | Perfil separa prefill/decode e reporta intensidade aritmética por nó | sim/não |
| M5 | Break-even com incerteza propagada (não ponto único) | P10/P50/P90 emitidos |
| M6 | Ranking de candidatos sobrevive a perturbação de ±20 % nos pesos do score | top-1 estável |

## Critérios de falha (declarados **antes** do experimento — §6.1)

- F1 — Nenhum padrão atinge cobertura ≥ 0,80 entre versões ⇒ H1 enfraquecida; hardening estrutural
  não se sustenta.
- F2 — O padrão mais custoso muda de identidade entre versões ⇒ H2 refutada.
- F3 — O top-1 do ranking troca sob perturbação de ±20 % dos pesos ⇒ o score não é decidível;
  `RETRACT` qualquer recomendação derivada dele.
- F4 — Break-even P50 > vida econômica assumida do chip ⇒ rota ASIC encerrada por `kill criteria`
  (§6.4) para aquele caso, mantendo FPGA/IP.
- F5 — Erro de M1 > 5 % ⇒ a IR não representa o modelo; todo resultado a jusante é inválido.

## Decisão que este ciclo deve permitir

Para um modelo dado, escolher **um** destino por subgrafo:
software · kernel otimizado · FPGA · bloco de IP · ASIC por arquitetura · pesos parcialmente fixos.

## Baseline congelado (§6.2)

`BASELINE-2026-08-03` — Llama-3.1-8B em GPU classe H100/A100, roofline analítico, INT8/BF16,
definido em [02_OBSERVATION/BASELINE/](../02_OBSERVATION/BASELINE/). Qualquer comparação posterior
exige re-execução deste baseline no mesmo ambiente.

## Portão D0 — verificação

- [x] pergunta cabe em uma frase;
- [x] termos definidos em [DEFINITIONS.md](DEFINITIONS.md);
- [x] baseline identificado e congelado;
- [x] o que não conta como solução está escrito (Não objetivos);
- [x] existe pelo menos um critério de falha (F1–F5).
