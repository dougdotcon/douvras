---
artifact: CHANGELOG
---

# Changelog

Registra mudanças de **código, priors e alegações**. Uma mudança de prior que altera uma
recomendação é tão relevante quanto uma mudança de código, e por isso entra aqui.

## [0.2.1] — 2026-08-14 — Migração para o monorepo DOUVRAS

Mudança **estrutural**, sem alteração de resultado. O contrato epistêmico saiu de
`silicon_atlas/status.py` para `douvras_core` e passou a ser compartilhado com o Model Atlas
([ADR-0005](../../model-atlas/06_ARCHITECTURE/ADR/ADR-0005-douvras-core.md)).

### Verificação de não-regressão

Os 24 artefatos do ciclo C-001 foram reemitidos após a migração e comparados com a versão
anterior, ignorando `run_id` e `generated_at`: **zero diferença de conteúdo**. Os números do
ciclo — SRS, região endurecível, teto de Amdahl, dívida de evidência de 38,6 % — são os mesmos.

### Alterado

- `status.py` → `douvras_core/status.py`; `STATUS_POLICY.md` sobe para a governança da raiz.
- `CONFIG_DIR` e `CORPUS_DIR` deixam de ser `parents[2]` e passam por
  `douvras_core.paths.project_root("silicon-atlas")`: com dois atlas sobre o mesmo `src/`, a
  contagem de níveis deixou de identificar o dono do arquivo.
- `cmd_gates` passa a usar os verificadores de `douvras_core.gates`.
- `scripts/run_cycle.py` → `scripts/run_silicon_cycle.py`; a suíte que o portão A5 verifica
  passa a ser `tests/core` + `tests/silicon` (**176 testes**).

### Corrigido — inconsistências de documentação

Três números que discordavam entre si, do tipo que `G-012` existe para acusar:

- README dizia "14 lacunas abertas" enquanto `atlas gates` dizia 13. Ambos certos sobre coisas
  diferentes: 14 registradas, 13 abertas, 1 parcial. `count_gaps` agora reporta as duas
  contagens separadas, e o README passa a dizer as duas.
- `SUCCESS_AND_FAILURE.md` (S7) e `OBSERVABILITY.md` diziam "11 lacunas", número de antes de
  `G-012`, `G-013` e `G-014` existirem.

## [0.2.0] — 2026-08-04 — Revisão adversarial do ciclo C-001

Revisão por 13 agentes independentes em 6 dimensões (física do modelo de custo, contrato
epistêmico, defeitos de programação, fidelidade ao Método, adequação de testes, coerência do
produto), com verificação cética por dimensão. 42 achados sobreviveram à tentativa de refutação.

### Retratado — precede as correções (Método §4.7)

- **R-002** — banda de recomendação de 8 dos 9 relatórios. O fator `P — perf_per_watt` valia
  1,000 nos nove, derivado de um acelerador que os próprios relatórios declaravam inexistente.
  Todos os nove passam a recomendar `software`.
- **R-003** — "nenhum NRE foi estimado" era falso no mesmo `run_id`: o Markdown suprimia, o JSON
  publicava. F4 disparava sobre objeto inexistente.
- **R-004** — estabilidade 1,000 para famílias sem transição observada. O sistema premiava
  ausência de dado. Empate de data (Qwen 7B/14B) era tratado como transição temporal.
- **R-005** — três afirmações do README sem sustentação nos artefatos.

### Corrigido

- `simulate()` recusa dimensionar acelerador sem ponto de projeto, em vez de fabricar um com
  `np.maximum(flops, 1.0)`. `EconomicsResult.not_applicable` propaga a ausência até o JSON.
- `energy_gain` passa a incluir o resíduo de Amdahl. Antes, dividia a energia da GPU inteira pela
  energia da região endurecida apenas: chegava a 6,7× acima do teto físico da própria partição, e
  era **anti-monotônico** — endurecer nada pontuava mais que endurecer 99,5 %.
- `family_stability` devolve `None`, nunca 1.0, sem transição observada; pares de escala (mesma
  data) saem de `diffs` e são reportados à parte.
- Métrica de decisão devolve `None` em vez de `NaN`; o portão de emissão recusa qualquer
  `Finding` numérico não-finito.
- `fits_in_device_memory` compara **pesos residentes** com a capacidade, não tráfego de leitura
  por passo. Mixtral (93,4 GB) deixa de "caber" em 80 GB.
- F2 avalia o bloco **mais custoso**, não o primeiro do ranking LHS. No Mixtral isso apontava
  para `lm_head` (1,0 % do custo) em vez de `expert_gate_proj` (29,0 %).
- Partição registra o **motivo** do bloqueio (estabilidade, irregularidade, quantização, política
  de runtime): 87 dos 98 pontos percentuais do Mixtral eram irregularidade, não estabilidade, e
  as duas causas pedem ações opostas.
- `hardening_ceiling_finding` e `SensitivityResult.finding` passam por `derive()`: emitiam
  `COMPUTATIONAL_EVIDENCE` sem lacunas para valores derivados de fatores `ASSUMPTION`.
- `DesignPoint` normaliza FLOPs por token e carrega a precisão dominante; com lote > 1 o die era
  dimensionado B vezes maior e a energia de cômputo usava int8 fixo.
- `record_run` idempotente e datado pelo `run_id`; o ledger versionado acumulara 6 tags e a mesma
  frase 4 vezes numa nota de 616 caracteres.
- `--corpus` honrada por todos os subcomandos; `atlas gates` misturava dois corpora no mesmo quadro.
- `registry verify` lê `hf_repo` do corpus, recusa modelos `CLIENT_SUPPLIED` (ameaça S-003).
- CLI reconfigura stdout para UTF-8: `atlas partition | more` morria com `UnicodeEncodeError`.
- Portões verificam **conteúdo**, não existência de caminho. A5 exige verificação registrada da
  suíte; U2 deixou de ser identidade aritmética sempre verdadeira.
- `STATUS_POLICY.md` reconciliada com `status.py`: `Status.rank` passou a existir, a ordem da
  tabela passou a ser a do enum, e os nomes de comando e módulo foram corrigidos.
- `corpus_integrity` devolve `None` quando nada foi verificado, em vez de "erro máximo 0,00 %".

### Adicionado

- `tests/test_nondegenerate.py` — o caminho econômico completo, que nunca havia sido executado
  sob teste porque o corpus real nunca produz região fixa.
- `tests/test_cli_and_ledger.py` — 800 linhas sem cobertura até aqui.
- `tests/conftest.py` — fixture de partição não-degenerada com fatores controlados.
- Testes que travam cada correção: falsificador que **dispara**, ganho limitado pelo teto de
  Amdahl, monotonicidade na fração endurecida, ledger idempotente, encoding redirecionado.
- `FindingSet.evidence_debt()` e histograma de status, impressos a cada ciclo.
- Artefatos do Método que faltavam: `SUCCESS_AND_FAILURE`, `COMPETING_MODELS`, `TRADEOFFS`,
  `THREAT_MODEL`, `OBSERVABILITY`, `BIBLIOGRAPHY_LEDGER`, `BENCHMARK_SPEC`, baseline congelado,
  runbook RB-001, e `TRANSFORMATION_MATRIX` + `DEPENDENCY_DAG` **gerados de dados reais**.
- `config/partition_policy.v1.json` — os limiares saem do código para arquivo versionado, porque
  afrouxá-los é o modo de falha mais provável sob pressão comercial.

### Lacunas novas

`G-012` (nenhum falsificador vigia coerência interna), `G-013` (teto de saturação do fator P sem
base empírica), `G-014` (caminho econômico nunca exercitado com corpus real).

De 77 para 145 testes.

## [0.1.0] — 2026-08-04 — Ciclo C-001

### Adicionado

- Núcleo epistêmico executável: `Status`, `Finding`, propagação pelo elo mais fraco,
  `StatusViolation`, lint de vocabulário proibido, `ClaimLedger`.
- Model Registry com normalização de 6 arquiteturas Hugging Face, proveniência, licença e hash.
- Corpus inicial: 9 modelos, 5 famílias, com contagem de parâmetros publicada como falsificador.
- DOUVRAS IR: grafo canônico com FLOPs, bytes e shapes simbólicos em B/S/T; suporte a MHA, GQA,
  MQA, MoE esparsa, GLU e MLP clássico, RoPE, janela deslizante alternada, embeddings amarrados,
  *softcapping* de logits e quatro normalizações por camada.
- Fingerprint estrutural em três níveis: `topology`, `pattern`, `exact`.
- Descoberta de invariantes: diff entre versões, cobertura de corpus, estabilidade por papel de
  bloco, taxa de mudança estrutural, efeito do escopo de comparação.
- Profiler roofline por fase, com `ServingProfile` combinando prefill e decode na proporção real
  de uma requisição.
- Modelo de quantização com priors versionados, planos uniformes e por sensibilidade, e
  substituição de prior por medição.
- Silicon Readiness Engine: LHS e SRS conforme Método §12.6, com análise de sensibilidade
  obrigatória e diagnóstico de discriminação.
- Particionador híbrido em quatro regiões, com teto de Amdahl e confronto de ganho alegado.
- Simulador PPA e econômico por Monte Carlo, com percentis, probabilidade de amortização antes da
  obsolescência e decomposição de sensibilidade.
- `Assessment` com portão de emissão que recusa relatório fora do contrato do Método §3.2 e §3.3.
- CLI com 13 comandos; `scripts/run_cycle.py` para o ciclo completo.
- 77 testes, incluindo os cinco falsificadores da carta do problema.

### Corrigido durante o ciclo

- `embed_tokens` contabilizava a tabela de embeddings inteira como bytes lidos por token. Um
  *gather* lê uma linha. O erro inflava o custo de decode em ~1 GB por token e colocava o
  embedding entre os principais candidatos a hardening. Detectado ao revisar o primeiro relatório
  emitido.
- Fator Q avaliado sempre na camada 0, o que aplicava a penalidade de camada de borda a papéis
  presentes em todas as camadas e rebaixava `lm_head` indevidamente para bf16.
- Falsificador F1 avaliado sobre o corpus inteiro em vez de dentro da família — conflitava
  estabilidade temporal com alcance de mercado (decisão D-009).
- `Partition.level` ignorava a região reconfigurável, classificando como "software genérico" uma
  partição com 97 % do custo em operadores regulares aptos a FPGA.
- Razões de atribuição de região eram genéricas ("instável ou não quantizável"); passaram a
  nomear qual limiar falhou e por quanto.
- Tabela de embeddings classificada como candidata a FPGA por ter endereçamento dependente de
  dado. É memória indexada, não lógica reconfigurável.

### Retratado

- **C-006** — o ranking do LHS não sobrevive à perturbação de ±20 % nos pesos. Falsificador F3
  disparado em 5 de 9 modelos. Diagnóstico em `CE-001`, retratação em `R-001`.

### Aberto

11 lacunas em `GAP_REGISTER`. As duas do caminho crítico: `G-002` (tolerância à quantização não
medida) e `G-011` (pesos do score nunca calibrados).
