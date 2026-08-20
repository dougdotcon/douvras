---
artifact: GAP_REGISTER
date: 2026-08-03
---

# Registro de lacunas

Lacuna aberta não impede o ciclo — impede que o resultado seja promovido acima de
`CONDITIONAL_RESULT`. Ver [STATUS_POLICY](../00_GOVERNANCE/STATUS_POLICY.md).

| Gap | Por que importa | Evidência necessária | Bloqueia | Status |
|---|---|---|---|---|
| G-001 | A IR é derivada de config, não traçada do modelo real; operador ausente invalida o perfil | `torch.export`/ONNX de 1 modelo por família, diff contra a IR | C-007 promovido acima de `MODEL` | **PARCIAL** — auditoria de pesos reais (`ir.importers.audit_against_real_weights`) contra `smollm2-360m-instruct` (arquitetura `LlamaForCausalLM`, checkpoint real via `named_parameters()`): **291/291 nós casados, zero órfão, zero divergência de shape, contagem de parâmetros com 0,0000 % de erro**. Valida o caminho **denso genérico** do construtor (usado por `llama`/`mistral`/`qwen` no corpus) — não cobre os ramos especiais (4 normas + janela alternada do Gemma, MoE do Mixtral, QKV fundido do Phi), nem é o protocolo exato do ADR (FLOPs/bytes via `torch.export`, que cobriria também operadores sem peso como RoPE/softmax). Faltam: um modelo por ramo especial, e a divergência de FLOPs para operadores funcionais |
| G-002 | Tolerância à quantização é prior, não medição; é 15 % do LHS e 10 % do SRS | Perplexidade/acurácia por camada em INT8/INT4/ternário | C-004, qualquer recomendação de precisão | OPEN |
| G-003 | Roofline não foi calibrado contra latência real | Latência por camada em A100/H100, mesmos shapes | A-002, A-005 | OPEN |
| G-004 | Energia por token é modelo analítico, não telemetria | Potência medida sob workload declarado | A-003, cálculo de break-even | OPEN |
| G-005 | NRE por nó tecnológico vem de faixas públicas | Cotação de foundry / design house | A-006, break-even | OPEN |
| G-006 | Taxa de obsolescência extrapola histórico curto (≈3 anos de corpus) | Série mais longa + registro de rupturas arquiteturais | A-007, risco O do SRS | OPEN |
| G-007 | Área é estimada por constantes, não por síntese | Síntese Yosys/OpenROAD do bloco candidato em PDK aberta | A-008, PPA | OPEN |
| G-008 | Configs do corpus foram transcritas, não baixadas da fonte | `atlas registry verify` com hash upstream | A-009, todo resultado numérico | **PARCIAL** — 5/9 conferidos com hash e data em 2026-08-15; uma divergência real corrigida ([COR-001](../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)). Os 4 restantes (`meta-llama/*`, `google/gemma-2-9b`) exigem aceite de licença e token |
| G-009 | Sem telemetria de produção: distribuição real de S/T/batch é assumida | Traces de workload de cliente | V (volume) do LHS | OPEN |
| G-010 | Sem revisão adversarial externa (§6.7): autor e auditor são o mesmo | Revisão por pessoa que não construiu o artefato | Portão V3 | OPEN |
| G-011 | Pesos do LHS/SRS nunca calibrados; 70 % do peso é inerte na comparação intra-modelo (ver [CE-001](../04_VALIDATION/COUNTEREXAMPLES/CE-001-lhs-nao-discrimina.md)) | Três casos com desfecho conhecido (bloco endurecido, ganho medido) | C-006, qualquer priorização entre papéis | OPEN |
| G-012 | Nenhum falsificador vigia **coerência interna** do relatório: a seção 6 dizia "nada foi dimensionado" enquanto o Anexo D publicava área e NRE, no mesmo `run_id` ([R-002](../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)) | Um F6 que confronte afirmações qualitativas com os `Finding` emitidos | integridade de qualquer relatório emitido | **PARCIAL** — guarda de não-finitos e `not_applicable` fecham os dois casos conhecidos; a classe permanece aberta |
| G-013 | O teto de saturação de 100× em `perf_per_watt_finding` não tem base empírica: um projeto legítimo com 99,5 % endurecido satura o fator do mesmo jeito que um inválido | Casos reais de perf/W de ASIC contra GPU, com protocolo declarado | fator P do SRS | OPEN |
| G-014 | A região fixa nunca foi não-vazia com o corpus real: o caminho econômico completo só é exercitado por partição sintética em teste | Corpus com estabilidade suficiente, ou política calibrada por G-011 | validade externa de todo o módulo de economia | OPEN |

## Dívida de evidência (§6.3)

| Decisão | Evidência atual | Risco | Evidência pendente | Data limite |
|---|---|---|---|---|
| Usar IR analítica em vez de traçada | A-001 | Médio: erro sistemático em ops de fusão | G-001 | ciclo C-002 |
| Priors de quantização fixos | A-004 | **Alto**: entra direto no score de decisão | G-002 | ciclo C-002 |
| η de GPU por faixa | A-005 | Médio: desloca a fronteira roofline | G-003 | ciclo C-002 |
| Constantes de área/energia | A-003, A-008 | Alto: define PPA e break-even | G-004, G-007 | ciclo C-003 |
