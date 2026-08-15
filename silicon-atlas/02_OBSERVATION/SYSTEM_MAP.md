---
artifact: SYSTEM_MAP
cycle: C-001
gate: O1
date: 2026-08-03
---

# Mapa do sistema real

Descrição do sistema **antes** de tentar explicá-lo (Método §4.2). Linguagem descritiva, sem
adjetivo promocional.

## Atores

| Ator | O que decide | O que arrisca |
|---|---|---|
| Laboratório de modelo aberto | arquitetura, versão, licença | irrelevância se não iterar rápido |
| Provedor de inferência | hardware, batching, preço por token | margem por token |
| Startup de chip | grau de especialização, nó, volume | NRE de máscara, janela de mercado |
| Foundry | capacidade, PDK, preço de wafer | ocupação de linha |
| Cliente final | qual modelo servir e a que custo | custo unitário e latência |
| Investidor / diligência | financiar ou não o tape-out | capital inteiro |

## Fluxo real (o que acontece hoje)

```text
laboratorio publica modelo
    → provedor carrega pesos em GPU
        → prefill (compute-bound) e decode (memory-bound)
            → custo por token dominado por leitura de pesos
                → provedor compra mais GPU
                    → startup de chip propõe acelerador
                        → decisão tomada com número de fabricante e analogia
                            → tape-out ou desistência
```

O ponto de decisão sem instrumento é o penúltimo. É onde o Atlas entra.

## Onde o recurso é consumido (medido neste ciclo)

Para um modelo 8B denso, requisição de prompt 2048 e geração 512, em GPU classe H100:

| Fase | Participação do tempo | Regime | Intensidade aritmética |
|---|---|---|---|
| prefill | ~2 % | compute-bound | ~610 FLOP/byte |
| decode | ~98 % | **memory-bound** | ~1 FLOP/byte |

Ponto de inflexão do dispositivo em decode: ~92 FLOP/byte. O decode opera duas ordens de
grandeza abaixo dele.

Consequência direta: **a inferência de token único é um problema de movimentação de dados**.
Um acelerador que multiplique a capacidade aritmética sem mudar a hierarquia de memória não
muda o custo. É o que sustenta a mitigação do Método §18.3.

## Pontos de falha do sistema atual

1. Decisão de especialização tomada por analogia arquitetural ("Transformer é estável").
2. Comparação entre número analítico de ASIC e número medido de GPU — assimetria não declarada.
3. Ganho estimado por FLOPs, ignorando bytes.
4. Estabilidade estrutural avaliada no nível errado (topologia em vez de shape exato).
5. Escopo de comparação escolhido depois de ver o resultado.
6. Break-even como ponto único, sem incerteza nem risco de obsolescência.

Os seis são endereçados por construção no Atlas. Nenhum deles é eliminado por ele: são tornados
visíveis e mensuráveis.

## Interfaces externas

| Interface | Uso | Estado |
|---|---|---|
| Hugging Face `config.json` | ingestão e verificação de proveniência | implementada (`atlas registry verify`) |
| `safetensors` / checkpoints | leitura de pesos | **não usada por decisão** (ADR-0001, §13.6) |
| `torch.export` / ONNX | grafo traçado | prevista, `G-001` |
| Telemetria de produção do cliente | distribuição real de S/T/batch | prevista, `G-009` |
| Foundry / design house | cotação de NRE e wafer | ausente, `G-005` |
| Yosys / OpenROAD | síntese e área reais | ausente, `G-007` |

## Portão O1 — verificação

- [x] fatos e inferências separados (status obrigatório em toda saída);
- [x] fontes registradas ([EVIDENCE_LEDGER](../00_GOVERNANCE/EVIDENCE_LEDGER.yaml), com
      `vendor_report` e `literature` marcados como tal);
- [x] baseline reproduzível (`config/devices.json`, congelado como `BASELINE-2026-08-03`);
- [x] gaps conhecidos e registrados ([GAP_REGISTER](GAP_REGISTER.md), 11 abertos);
- [x] sistema descrito sem linguagem promocional.
