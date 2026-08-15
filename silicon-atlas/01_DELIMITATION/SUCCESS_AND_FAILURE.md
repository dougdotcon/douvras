---
artifact: SUCCESS_AND_FAILURE
cycle: C-001
date: 2026-08-03
status: DEFINITION
---

# Sucesso e falha

Declarado **antes** da execução (Método §6.1). Um critério escrito depois de ver o resultado não
é critério, é narrativa.

## O que conta como sucesso do ciclo

O Método §2 admite dez desfechos como sucesso. Este ciclo se compromete com estes:

| # | Desfecho | Alcançado em C-001 |
|---|---|---|
| S1 | Uma hipótese que sobreviveu a testes relevantes | **sim** — C-002 e C-003 (concentração de custo, decode limitado por memória) |
| S2 | Uma hipótese refutada com clareza | **sim** — C-006, retratada pelo próprio pipeline |
| S3 | Um contraexemplo preservado | **sim** — CE-001 |
| S4 | Uma estrutura mínima reutilizável | **sim** — UMI-1 e UMI-2 |
| S5 | Um benchmark | parcial — baseline congelado, sem medição de hardware |
| S6 | Um software científico reproduzível | **sim** — semente fixa, ciclo reexecutável |
| S7 | Um mapa confiável das lacunas restantes | **sim** — 14 lacunas registradas (13 abertas, 1 parcial) com evidência necessária declarada |
| S8 | Uma decisão justificada de encerrar uma rota | não — critérios de encerramento declarados, não atingidos |

Um ciclo que produzisse **apenas** S2 e S3 ainda seria bem-sucedido. O que o tornaria fracasso
seria produzir zero destes e mesmo assim emitir recomendação.

## O que conta como sucesso do produto

Distinto do sucesso científico, e deliberadamente não confundido com ele (Método §1).

| # | Critério | Estado |
|---|---|---|
| P1 | Um terceiro consegue reproduzir o assessment sem ajuda do autor | atende — `REPRODUCIBILITY.md` |
| P2 | O relatório responde à pergunta que originou o pedido, mesmo quando a resposta é "não" | atende |
| P3 | Cada número do relatório é rastreável até sua premissa | atende — Anexo D |
| P4 | O relatório resiste a leitura hostil de comitê de investimento | **não** — a revisão adversarial de 2026-08-04 derrubou a banda de recomendação de 8 dos 9 |
| P5 | Alguém paga por ele | não testado |

Sobre P4: a revisão foi feita por agentes, não por um comitê humano, e por isso `G-010` continua
aberta. Mas o resultado responde à pergunta antes de qualquer cliente responder: **não resistia**.
Resiste melhor agora, e a diferença está medida em
[RETRACTIONS_AND_CORRECTIONS.md](../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md).

## O que conta como falha

### Falha do ciclo

Os cinco falsificadores da [PROBLEM_CHARTER](PROBLEM_CHARTER.md), F1 a F5. Estado ao fim de C-001:

| Falsificador | Estado | Consequência aplicada |
|---|---|---|
| F1 — nenhum padrão com cobertura ≥ 0,80 entre versões | **disparado** em 5 de 9; **não avaliável** em 4 (famílias sem transição temporal) | H1 enfraquecida; região fixa vazia |
| F2 — o bloco mais custoso muda de identidade entre versões | **disparado** em 9 de 9 | hardening estrutural não se sustenta neste corpus |
| F3 — ranking não sobrevive a ±20 % nos pesos, ou vence por margem menor que o ruído | **disparado** em 9 de 9 | C-006 retratada; portão V3 bloqueado |
| F4 — break-even P50 posterior à vida econômica | **não avaliável** em 9 de 9 | ver abaixo |
| F5 — erro de contagem de parâmetros > 5 % | não disparado | IR validada |

**Correção de 2026-08-04.** A versão anterior deste quadro registrava "F4 disparado em 9 de 9 →
rota ASIC não financiável". F4 compara break-even com vida econômica; com região fixa vazia não
existe break-even a comparar — o `inf` que disparava o critério era fabricado por um `np.maximum`
sobre uma divisão indefinida ([R-003](../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)).

A conclusão de que a rota ASIC não se sustenta neste corpus **permanece**, e agora por um motivo
mais direto: não há região endurecível, logo não há projeto a financiar. O falsificador que a
sustentava era o errado.

**Três dos cinco falsificadores dispararam, e dois não são avaliáveis com a evidência atual.**
Isso não é falha do ciclo: é o ciclo funcionando. O que seria falha é ter emitido recomendação de
tape-out mesmo assim — ou, como quase aconteceu, deixar um falsificador disparar sobre um objeto
inexistente e usar isso como conclusão de governança.

### Falha do sistema

Estas condições invalidariam o Silicon Atlas como instrumento, não apenas um resultado:

1. **F5 disparar.** A IR não representa os modelos; tudo a jusante é ruído.
2. **Um relatório ser emitido violando o contrato** (seção faltando, vocabulário proibido,
   sensibilidade não executada). O portão de emissão existe para tornar isso impossível.
3. **Um `Finding` ser promovido acima de suas dependências.** `StatusViolation` existe para isso.
4. **Duas execuções com a mesma entrada produzirem recomendações diferentes.** Destruiria a
   auditabilidade, que é o único produto real.
5. **O sistema recomendar hardening onde o teto de Amdahl é 1,00×.** Seria contradição interna.

Nenhuma ocorreu. As três primeiras têm teste dedicado.

## O que explicitamente NÃO conta

- **Não conta como sucesso** que o sistema recomende fabricar. O valor está na decisão auditável,
  não na direção dela.
- **Não conta como falha** que a região endurecível tenha ficado vazia nos 9 modelos. Esse é um
  resultado, e é o resultado que a evidência atual sustenta.
- **Não conta como sucesso** que os números pareçam plausíveis. Plausibilidade não é validação;
  `G-003` continua aberta.
