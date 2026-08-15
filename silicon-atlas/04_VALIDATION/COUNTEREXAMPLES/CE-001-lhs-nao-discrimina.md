---
artifact: COUNTEREXAMPLE
id: CE-001
date: 2026-08-04
cycle: C-001
affects: [C-006, LHS, config/readiness_weights.v1.json]
status: CONFIRMED
severity: alta
---

# CE-001 — O LHS não discrimina candidatos dentro de um mesmo modelo

## O que aconteceu

Ao rodar o ciclo sobre os 9 modelos do corpus, o falsificador **F3** disparou em 4 deles
(`gemma-2-9b`, `phi-3-mini-4k`, `mixtral-8x7b-v0.1`, `qwen2.5-14b`, `llama-2-7b`): o candidato
top-1 do ranking LHS troca sob perturbação de ±20 % nos pesos.

O `CLAIM_LEDGER` retratou automaticamente a alegação **C-006** — comportamento correto do laço
adversarial, não defeito.

## Diagnóstico

A instabilidade **não** vem de empate entre candidatos equivalentes — empates exatos (`gate_proj`
e `up_proj` têm vetores de fatores idênticos) são agrupados antes da medição. Vem da estrutura da
fórmula.

Medição em `gemma-2-9b`:

| Papel | Custo | LHS | E | F | R | Q | V | M | L |
|---|---|---|---|---|---|---|---|---|---|
| gate_proj | 22,3 % | 0,515431 | 0,111 | 0,223 | 1,000 | 0,720 | 0,678 | 1,000 | 0,000 |
| up_proj | 22,3 % | 0,515431 | 0,111 | 0,223 | 1,000 | 0,720 | 0,678 | 1,000 | 0,000 |
| q_proj | 6,4 % | 0,511028 | 0,111 | 0,064 | 1,000 | 0,850 | 0,678 | 1,000 | 0,000 |
| down_proj | 22,3 % | 0,500431 | 0,111 | 0,223 | 1,000 | 0,620 | 0,678 | 1,000 | 0,000 |

Entre os candidatos que disputam a primeira posição, cinco dos sete fatores — `E`, `R`, `V`, `M`,
`L` — são **idênticos**. São propriedades do modelo e do bloco, não do papel individual.
**0,70 do peso do LHS é inerte para esta decisão**: gasta peso sem separar nada.

Restam `F` (peso 0,15) e `Q` (peso 0,15), que se cancelam parcialmente, porque existe correlação
negativa real entre custo e tolerância à quantização: as projeções do MLP dominam o custo mas têm
prior de quantização menor que as projeções de atenção.

```text
vantagem de gate_proj sobre q_proj em F:  0,15 × (0,223 − 0,064) = +0,0239
desvantagem em Q:                          0,15 × (0,720 − 0,850) = −0,0195
diferença líquida (margem):                                         +0,0044
```

Uma margem de 0,0044 não sobrevive a uma perturbação de ±20 % em pesos da ordem de 0,15.

### Medição em todo o corpus

Margem sobre o primeiro concorrente distinto, contra a largura do ruído induzido pela
perturbação dos pesos:

| Modelo | Estabilidade top-1 | Margem | Ruído | Peso inerte entre concorrentes | Discrimina? |
|---|---|---|---|---|---|
| llama-3.1-8b | 0,961 | 0,0067 | 0,0282 | 70 % | **não** |
| gemma-2-9b | 0,876 | 0,0044 | 0,0267 | 70 % | não |
| qwen2.5-14b | 0,790 | 0,0030 | 0,0268 | 70 % | não |
| phi-3-mini-4k | 0,681 | 0,0015 | 0,0264 | 70 % | não |
| mixtral-8x7b-v0.1 | 0,643 | 0,0063 | 0,0266 | 35 % | não |

Em **todos** os casos a margem fica entre 4× e 18× **abaixo** do ruído.

### O achado sobre o próprio falsificador

`llama-3.1-8b` passou no F3 como especificado — 0,961 de estabilidade top-1, acima do limite de
0,95 — e mesmo assim não discrimina. A estabilidade de ranking dava **falsa confiança**: ela mede
com que frequência o mesmo nome aparece em primeiro lugar, não se esse primeiro lugar significa
alguma coisa.

Um falsificador declarado antes do experimento pode, ele próprio, ser fraco demais. Este era.

## Por que isso importa

O LHS foi especificado no Método 12.6 para responder "qual camada ou subgrafo está mais pronto
para virar silício". A medição mostra que, com os pesos propostos, ele **não responde essa
pergunta dentro de um modelo** — a margem entre candidatos é menor que a incerteza dos próprios
pesos.

Ele continua servindo para comparar **casos entre si** (modelos ou famílias diferentes), porque
aí `E`, `V` e `L` variam de verdade. A falha é específica do uso intra-modelo.

## O que NÃO se conclui

- Não se conclui que a fórmula está errada. Conclui-se que ela é **subdeterminada** para este uso,
  e que os pesos nunca foram calibrados (`readiness_weights.v1.json` declara `UNCALIBRATED`).
- Não se conclui que `gate_proj` não é o melhor candidato. Provavelmente é — mas o LHS não é o
  instrumento que sustenta essa afirmação; a participação de custo bruta sustenta melhor.

## Correção adotada

1. `SensitivityResult` passa a reportar **discriminação**, não só estabilidade de ranking:
   margem sobre o primeiro concorrente distinto, largura do ruído, peso inerte entre os
   concorrentes e quais fatores efetivamente variam. Empates exatos são agrupados, de modo que
   equivalência genuína deixa de ser confundida com fórmula cega.
2. O falsificador F3 passa a exigir **as duas** condições: ranking estável **e** margem acima do
   ruído. A versão original, só com estabilidade de ranking, aprovava `llama-3.1-8b`
   indevidamente.
3. O relatório passa a explicar a causa em vez de exibir apenas "F3 disparado".
4. `C-006` permanece **RETRACTED** até haver calibração — agora para **todos** os modelos do
   corpus, não apenas os cinco em que o teste original disparava. Nenhuma recomendação de
   priorização entre papéis dentro de um modelo pode citar o LHS como fundamento neste ciclo.

## Correção NÃO adotada, e por quê

Rejeitado: reponderar os fatores até o ranking estabilizar. Isso ajustaria o instrumento ao
resultado desejado — exatamente o "mecanismo que só funciona porque o teste foi adaptado ao
resultado" listado na auditoria adversarial do Método 4.4.

## Evidência necessária para fechar

Calibração dos pesos contra pelo menos três casos com desfecho conhecido (bloco endurecido em
FPGA ou silício, com ganho medido). Sem isso, o LHS ordena, mas não decide.
Novo gap: **G-011**.
