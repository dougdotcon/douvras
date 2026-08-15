---
artifact: DECISION_LOG
scope: DOUVRAS — nível monorepo
policy: append-only
---

# Registro de decisões — DOUVRAS

Decisões que valem para **todos** os atlas. Decisões de um eixo específico ficam no
`DECISION_LOG` do respectivo projeto:
[silicon-atlas](../silicon-atlas/00_GOVERNANCE/DECISION_LOG.md) ·
[model-atlas](../model-atlas/00_GOVERNANCE/DECISION_LOG.md).

| # | Data | Decisão | Justificativa | Reversível por |
|---|---|---|---|---|
| D-011 | 2026-08-14 | O contrato epistêmico vira `douvras_core`, compartilhado pelos atlas | A escala de status descreve como uma afirmação se relaciona com sua evidência; se só servisse para hardware seria vocabulário de domínio disfarçado ([ADR-0005](../model-atlas/06_ARCHITECTURE/ADR/ADR-0005-douvras-core.md)) | dois atlas precisarem de semânticas diferentes para o mesmo conceito de status |
| D-012 | 2026-08-14 | Um projeto por eixo, cada um com suas sete fases DOUVRAS completas | Cada eixo roda o próprio ciclo, com carta, falsificadores e portões próprios. Governança única faria `C-001` do silício colidir com `C-001` de capacidade | um eixo deixar de ter ciclo próprio |
| D-013 | 2026-08-14 | Numeração de lacunas e alegações segregada por eixo (`G-0xx` silício, `G-1xx` capacidade) | Uma lacuna é sempre lacuna *de alguma coisa*; namespace comum faria duas coisas diferentes disputarem o mesmo id | — |
| D-014 | 2026-08-14 | `STATUS_POLICY.md` sobe para a raiz junto com `status.py` | A política descreve o contrato do core, não as decisões de um atlas. Manter no silício faria o Model Atlas citar documento de outro projeto como sua norma | — |
| D-015 | 2026-08-14 | O Silicon Atlas é preservado intacto: nenhum resultado do ciclo C-001 é reemitido, corrigido ou reinterpretado pela migração | A migração é estrutural; alterar número junto seria misturar refatoração com pesquisa e tornar impossível dizer qual das duas causou a mudança | — |
| D-016 | 2026-08-14 | A não-regressão da migração é verificada por regeneração e diff, não por confiança nos testes | Os 149 testes já passavam antes; passar depois não prova que os artefatos emitidos são os mesmos. Verificação: 24 artefatos reemitidos, comparados ignorando `run_id` e timestamp, **zero diferença de conteúdo** | — |

## Sobre o histórico

Este monorepo nasceu do repositório `ASICs`, que continha o ciclo C-001 completo do Silicon
Atlas. O histórico git anterior não foi preservado — o diretório `.git` foi removido antes da
reestruturação. Os artefatos do ciclo C-001 estão preservados por inteiro em
[`silicon-atlas/`](../silicon-atlas/), incluindo as cinco retratações e o registro de correções.

## Relação com os documentos de origem

Os três documentos em [`docs/`](../docs/) são a tese que motivou o eixo de capacidade. O
Documento 2 propõe explicitamente não destruir o Silicon Atlas e sim colocá-lo, junto do Model
Atlas, sobre um core comum — que é exatamente `D-011` e `D-012`. O Documento 1 é anterior e
está parcialmente superado por ele na parte de estrutura e nomenclatura; o Documento 3 é a
camada comercial e não gera decisão técnica.
