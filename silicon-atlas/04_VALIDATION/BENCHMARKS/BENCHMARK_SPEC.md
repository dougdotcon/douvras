---
artifact: BENCHMARK_SPEC
cycle: C-001
date: 2026-08-04
status: DEFINITION
---

# Especificação de benchmark

O Método §18.2 identifica "benchmarks promocionais" como risco central. A defesa não é desconfiar
de números alheios — é declarar os próprios com precisão suficiente para que alguém os derrube.

Este documento define os workloads de referência. **Nenhum número medido em hardware existe
ainda** (`G-003`); esta é a especificação contra a qual a medição futura será feita.

## Por que a especificação vem antes da medição

Um benchmark definido depois de ver o resultado seleciona a condição favorável. Definir antes
significa aceitar o número que sair.

## Workloads de referência

Cada workload declara todos os qualificadores que o `CLAIM_LEDGER:C-004` exige para qualquer
alegação de ganho.

### W-001 — Chat de latência (o caso mais citado, o pior economicamente)

| Parâmetro | Valor |
|---|---|
| prompt | 2048 tokens |
| geração | 512 tokens |
| lote | 1 |
| contexto máximo | 2560 |
| precisão de pesos | nativa do modelo (bf16) |
| precisão de ativação | bf16 |
| métrica primária | tokens gerados por segundo, fluxo único |
| métrica secundária | joules por token gerado, incluindo host e refrigeração |

É o baseline congelado. Também é o operating point onde o hardware especializado **mais** parece
vantajoso — e por isso o que exige maior ceticismo.

### W-002 — Serviço em lote (o caso econômico real)

| Parâmetro | Valor |
|---|---|
| prompt | 2048 tokens |
| geração | 512 tokens |
| lote | 64 |
| contexto máximo | 2560 |
| métrica primária | tokens por segundo agregados |
| métrica secundária | joules por token, custo por milhão de tokens |

A [TRANSFORMATION_MATRIX](../../03_UNIFICATION/TRANSFORMATION_MATRIX.md) mostra que sair de W-001
para W-002 muda a energia por token em ~19× **sem hardware novo**. Qualquer comparação que use
W-001 para a GPU e lote otimizado para o acelerador está fabricando a vantagem.

### W-003 — Contexto longo

| Parâmetro | Valor |
|---|---|
| prompt | 32768 tokens |
| geração | 512 tokens |
| lote | 1 |
| métrica primária | participação do KV cache no tráfego total |

Existe para expor o regime em que o KV cache disputa espaço com os pesos — o dimensionamento de
SRAM que um acelerador projetado para contexto curto não atende.

### W-004 — Prefill dominante (extração estruturada, classificação)

| Parâmetro | Valor |
|---|---|
| prompt | 8192 tokens |
| geração | 32 tokens |
| lote | 8 |
| métrica primária | tokens de prompt por segundo |

Único workload onde o regime é compute-bound. Recomenda hardware diferente dos outros três, e
isso é o ponto: um chip único não atende os quatro.

## Protocolo obrigatório para qualquer medição futura

Toda medição que entrar no `EVIDENCE_LEDGER` como `primary_measurement` precisa declarar:

1. modelo e revisão exata (hash do checkpoint);
2. workload completo (W-00x ou especificação equivalente);
3. software: runtime, versão, flags de compilação, kernel de atenção;
4. hardware: SKU, firmware, clock efetivo, temperatura ambiente;
5. **consumo total do servidor**, não só do acelerador;
6. número de repetições e dispersão, não apenas a melhor execução;
7. o que foi excluído da medição (aquecimento, primeira execução, outliers) e o critério;
8. quem executou e se tem interesse no resultado.

O item 8 não é burocracia. `E-002` está no ledger como `vendor_report` por causa dele.

## Baselines contra os quais comparar

| Baseline | Estado |
|---|---|
| `h100-sxm` roofline analítico | congelado, `BASELINE-2026-08-03` |
| `h100-sxm` medido | **ausente** (`G-003`) |
| `a100-sxm-80` roofline analítico | disponível |
| FPGA protótipo | ausente, previsto para C-002+ |
| Silício | ausente |

## Anti-padrões que este documento existe para impedir

- Comparar acelerador em lote grande contra GPU em lote 1.
- Comparar acelerador em INT4 contra GPU em BF16 sem reportar qualidade.
- Reportar potência do chip contra potência de servidor.
- Reportar prefill quando o custo está em decode, ou vice-versa.
- Reportar a melhor execução de N sem a dispersão.
- Omitir o comprimento de contexto.

Os seis já apareceram em material público do setor. Nenhum deles é fraude; todos produzem números
verdadeiros e conclusões falsas.
