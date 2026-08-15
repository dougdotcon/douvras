---
artifact: SUCCESS_AND_FAILURE
cycle: C-002
date: 2026-08-14
status: DEFINITION
---

# Sucesso e falha — ciclo C-002

Declarado **antes** da execução (Método §6.1). Um critério escrito depois de ver o resultado
não é critério, é narrativa.

## O que conta como sucesso do ciclo

| # | Desfecho | Alcançado em C-002 |
|---|---|---|
| S1 | Uma hipótese que sobreviveu a testes relevantes | **sim** — `C-101`, `C-103`, `C-104`, `C-105`, todas medidas em 100 % |
| S2 | Uma hipótese refutada com clareza | **sim** — `C-102`, retratada pelo próprio falsificador `F3` |
| S3 | Um contraexemplo preservado | **sim** — `CE-101` |
| S4 | Uma estrutura mínima reutilizável | **sim** — UMI-101 e UMI-102 |
| S5 | Um benchmark | **sim** — 96 tarefas, 132 contraexemplos, baseline congelado |
| S6 | Um software científico reproduzível | **sim** — sem RNG no caminho principal; duas execuções idênticas |
| S7 | Um mapa confiável das lacunas restantes | **sim** — 11 lacunas com evidência necessária declarada |
| S8 | Uma decisão justificada de encerrar uma rota | não — critérios declarados, não atingidos |

Um ciclo que produzisse **apenas** S2 e S3 ainda seria bem-sucedido. O que o tornaria fracasso
seria produzir zero destes e mesmo assim publicar um escore.

## O que conta como sucesso do produto

Distinto do sucesso científico, e deliberadamente não confundido com ele.

| # | Critério | Estado |
|---|---|---|
| P1 | Um terceiro reproduz o assessment sem ajuda do autor | atende — `REPRODUCIBILITY.md`, sem GPU e sem rede |
| P2 | O relatório responde à pergunta que originou o pedido, mesmo quando a resposta é "ainda não" | atende |
| P3 | Cada número é rastreável até sua premissa | atende — Anexo de rastreabilidade |
| P4 | O relatório resiste a leitura hostil | **não testado** — `G-110` |
| P5 | Alguém paga por ele | não testado |

## O que conta como falha

### Falha do ciclo

Os seis falsificadores da [PROBLEM_CHARTER](PROBLEM_CHARTER.md). Estado ao fim de C-002:

| Falsificador | Estado | Consequência aplicada |
|---|---|---|
| F1 — grader aceita trajetória errada | não disparado (1,000) | `C-101` sobrevive |
| F2 — grader rejeita gabarito | não disparado (1,000) | `C-101` sobrevive |
| F3 — margem agregada abaixo de 0,20 | **disparado** (0,062) | `C-102` retratada; portão V3 bloqueado |
| F4 — execuções divergem | não disparado | `C-105` sobrevive |
| F5 — tarefa não avaliável ou cobertura fina | não disparado | `C-103` sobrevive |
| F6 — modo de falha sem sonda | não disparado | `C-104` sobrevive |

**Um dos seis disparou.** Isso não é falha do ciclo: é o ciclo funcionando. O que seria falha é
publicar um leaderboard com um escore cujo próprio critério de discriminação foi reprovado.

### Falha do sistema

Condições que invalidariam o Model Atlas como instrumento, não apenas um resultado:

1. **F1 ou F2 disparar.** O grader não mede o que afirma; nenhum número a jusante vale.
2. **Um relatório ser emitido violando o contrato** (seção faltando, vocabulário proibido,
   número não-finito, contradição interna). O portão de emissão existe para tornar impossível.
3. **Um número sintético ser apresentado como medição de modelo.** `ADR-0007` e a recusa em
   `CapabilityFingerprint.from_run` existem para isso.
4. **Duas execuções com a mesma entrada produzirem vereditos diferentes.**

Nenhuma ocorreu. As quatro têm teste dedicado.

## O que explicitamente NÃO conta

- **Não conta como sucesso** que algum modelo pontue alto. Nenhum modelo foi executado.
- **Não conta como falha** que o assessment saia cheio de ausências declaradas. É o resultado
  que a evidência disponível sustenta.
- **Não conta como sucesso** que as sondas se comportem como esperado em 8 de 8. Elas foram
  escritas por quem escreveu o grader; é consistência interna, não validação.
