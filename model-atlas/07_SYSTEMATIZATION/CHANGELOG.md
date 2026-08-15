---
artifact: CHANGELOG
---

# Changelog — Model Atlas

Registra mudanças de **código, corpus, priors e alegações**. Uma mudança de prior que altera
uma recomendação é tão relevante quanto uma mudança de código, e por isso entra aqui.

## [0.1.0] — 2026-08-14 — Ciclo C-002: o instrumento antes da medida

### Adicionado

- `douvras_core` extraído do Silicon Atlas (`ADR-0005`): `status`, `paths`, `gates`, `report`.
  Os dois atlas passam a compartilhar escala de status, portões e portão de emissão.
- `model_atlas` com nove módulos: `tasks` (vocabulário e ambiente executável), `graders`
  (17 regras declarativas), `runner` (execução e sondas), `instrument` (verificação do
  instrumento), `capability`, `failure`, `css`, `profiler`, `registry`, `assessment` e `cli`.
- **BR-Agent-Bench v0.1**: 96 tarefas em 8 capacidades, 132 contraexemplos rotulados, gerados
  por `scripts/build_task_corpus.py` sem nenhuma fonte de aleatoriedade.
- Oito sondas de calibração, cada uma com o modo de falha que promete disparar declarado em
  `runner.PROBES` **antes** da execução.
- `MODEL CAPABILITY ASSESSMENT` com portão de emissão: seções obrigatórias, vocabulário,
  números não-finitos, coerência interna e promoção à mão.
- Governança completa do ciclo: carta com seis falsificadores, premissas `A-101`..`A-106`,
  onze lacunas, baseline congelado, protocolo `X-002`, duas UMIs, três ADRs, runbook.

### Medido

| Métrica | Valor |
|---|---:|
| aceitação do gabarito | 100,0 % (96/96) |
| rejeição de contraexemplo | 100,0 % (132) |
| precisão do rótulo | 100,0 % |
| determinismo | idêntico entre execuções |
| modos de falha sem sonda | nenhum |
| margem de discriminação agregada | **0,062** |

### Retratado — precede as correções (Método §4.7)

- **R-101** — `C-102`, a alegação de que o escore agregado separa respondente correto de
  degenerado por margem maior que 0,20. Falsificador `F3` disparado com 0,062. Diagnóstico em
  `CE-101`: cada sonda ataca uma família e o agregado dilui o dano pelo corpus inteiro —
  `desiste-no-erro` destrói 100 % do que ataca e move o agregado em 0,125.

### Corrigido durante o ciclo

- `check_status_floor` do core verificava condição inalcançável (um `Finding` com lacuna não
  nasce acima de `CONDITIONAL_RESULT`, o construtor impede). Substituída por
  `check_no_hand_promotion`, que verifica algo que pode de fato acontecer.
- Primeiro diagnóstico de `CE-101` comparava o oráculo com a melhor sonda **dentro de cada
  capacidade** e devolvia 0,000 em todas — porque para toda capacidade existe alguma sonda que
  não a ataca. Substituído pela comparação de cada sonda contra o oráculo no alvo que ela
  própria declarou.
- `Environment.call` tinha lógica de `recover_after` que nunca se recuperava, tornando "falha
  transitória" indistinguível de "falha permanente" e esvaziando metade das tarefas de
  recuperação.
- `_rule_must_ask` levantava `StopIteration` em trajetória sem nenhuma chamada.

### Lacunas novas

`G-101` a `G-111`. As três do caminho crítico: `G-101` (nenhuma execução real), `G-104` (priors
do CSS não calibrados) e `G-107` (corpus sintético, validade externa não estabelecida).

### Verificação de não-regressão do Silicon Atlas

Os 24 artefatos do ciclo C-001 foram reemitidos após a extração do core e comparados com a
versão anterior, ignorando `run_id` e timestamp: **zero diferença de conteúdo**. Os 149 testes
do eixo de silício seguem verdes.
