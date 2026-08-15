---
artifact: THREAT_MODEL
cycle: C-001
date: 2026-08-04
---

# Modelo de ameaças

Duas famílias de ameaça, e a segunda é a que mais importa para este produto.

1. **Confidencialidade** — vazamento de propriedade intelectual do cliente.
2. **Integridade epistêmica** — o sistema emitir uma conclusão que a evidência não sustenta.

A segunda é existencial: um Atlas que produz recomendações bonitas e erradas é pior que nenhum
Atlas, porque transfere confiança para uma decisão de dezenas de milhões.

---

## Parte 1 — Confidencialidade

| ID | Ameaça | Vetor | Mitigação atual | Residual |
|---|---|---|---|---|
| S-001 | Pesos do modelo do cliente vazam | leitura de checkpoint | **o Atlas nunca lê pesos** (ADR-0001); opera sobre `config.json` | arquitetura ainda é revelada pelo config |
| S-002 | Arquitetura proprietária vaza pelo relatório | relatório compartilhado | relatório é arquivo local; nenhuma telemetria, nenhuma chamada de rede no caminho principal | processo do cliente |
| S-003 | Config do cliente vai para serviço externo | `atlas registry verify` faz HTTP | comando **opcional**, nunca no caminho principal; só busca, nunca envia | usuário pode rodar em modelo privado por engano |
| S-004 | Corpus adulterado por terceiro | edição de `corpus/models/*.json` | teste de contagem de parâmetros contra valor publicado detecta a maioria dos campos; hash de proveniência quando verificado | erro que se cancele entre dois campos |
| S-005 | Priors adulterados para favorecer conclusão | edição de `config/*.json` | priors versionados e citados no relatório; `git diff` expõe | sem assinatura de arquivos |

**Ação para S-003**: `verify` deveria recusar rodar sobre modelo marcado `CLIENT_SUPPLIED`. O
enum `ProvenanceStatus.CLIENT_SUPPLIED` existe e ainda não é usado como guarda. Registrado como
melhoria, não como lacuna de evidência.

---

## Parte 2 — Integridade epistêmica

Aqui o "atacante" mais provável não é malicioso: é o entusiasmo do próprio autor, ou a pressão
comercial de um cliente que já decidiu o que quer ouvir.

| ID | Ameaça | Como se manifestaria | Mitigação | Estado |
|---|---|---|---|---|
| E-001 | Número analítico citado como medição | slide dizendo "17 mil tokens/s medidos" | status obrigatório em todo `Finding`; Anexo D lista o status de cada número | **ativo e testado** |
| E-002 | Promoção indevida de status | alguém marca um resultado como `EXPERIMENTAL_EVIDENCE` | `StatusViolation` na construção; `derive()` limita pelo elo mais fraco | **ativo e testado** |
| E-003 | Ganho alegado sem qualificadores | "100× mais rápido" | `lint_text` exige modelo, baseline, precisão, lote, contexto, fase na vizinhança | **ativo e testado** |
| E-004 | Escopo escolhido depois de ver o resultado | comparar só as versões que favorecem | seção "efeito do escopo" **obrigatória** no relatório, mostrando ambos os números | **ativo** |
| E-005 | Reponderar o score até a recomendação sair | ajustar pesos do LHS | pesos versionados em arquivo; análise de sensibilidade obrigatória; CE-001 registra a tentação e a recusa | **ativo** |
| E-006 | Critério de falha reescrito depois do experimento | mudar F1..F5 | falsificadores na `PROBLEM_CHARTER`, sob git, avaliados por código | **ativo** |
| E-007 | Prior otimista inflando recomendação | mexer em `quantization_priors` | prior e medição são **campos distintos**; medição substitui, nunca combina | **ativo e testado** |
| E-008 | Comparação assimétrica (modelo analítico de ASIC vs medição de GPU) | ganho de energia inflado | assimetria declarada em `A-003` e repetida na seção de limitações de todo relatório | **declarado, não eliminado** |
| E-009 | Autor validando o próprio trabalho | ausência de revisão externa | portão V3 **bloqueado** por `G-010` | **não mitigado** |
| E-010 | Relatório citado fora de contexto | trecho isolado sem o Anexo D | cabeçalho YAML carrega `weakest_status`; cada seção repete a ressalva | parcial |

### A ameaça E-008 merece detalhe

O ganho de energia por token compara:

- **GPU**: tempo roofline × TDP × overhead de servidor × PUE — inclui tudo que o data center paga.
- **Alvo especializado**: `FLOPs × pJ/FLOP + bytes × pJ/byte` — inclui apenas o que o modelo prevê.

O segundo omite: distribuição de clock, fugas, I/O, controlador de memória, margens de projeto,
DVFS, e toda a diferença entre um número de datasheet e um sistema em rack. **A assimetria
favorece estruturalmente o alvo especializado.**

Não foi eliminada porque eliminá-la exigiria um modelo de potência de sistema completo para um
chip que não existe. Foi **declarada**: o ganho de energia deve ser lido como teto otimista.
Fechar `G-004` com telemetria real é a única correção honesta.

---

## O que este modelo de ameaças não cobre

- Segurança de infraestrutura (não há servidor; o Atlas é um processo local).
- Autenticação e autorização (não há multi-tenant; ver `DECISION_LOG` D-adiadas).
- Cadeia de suprimentos de dependências (`numpy`, `pyyaml`) — fora de escopo neste ciclo.
- Conformidade de exportação e restrições geopolíticas sobre hardware (Método §18.7) — declarado
  como risco no método, não modelado aqui.
