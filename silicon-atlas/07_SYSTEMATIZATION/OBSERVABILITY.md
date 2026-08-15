---
artifact: OBSERVABILITY
cycle: C-001
date: 2026-08-04
---

# Observabilidade

Um sistema de análise observa o mundo. Este documento trata do inverso: **como se observa o
sistema de análise**, para saber quando ele está errado.

## O que é observável hoje

### 1. Toda afirmação carrega proveniência

Cada assessment emite o `FindingSet` completo no Anexo D: nome, valor, unidade, status, premissas
e lacunas de todo número que entrou na conclusão. Não existe número órfão no relatório.

```bash
PYTHONPATH=src python -m silicon_atlas.cli assess llama-3.1-8b --json /dev/stdout \
  | python -c "import json,sys; d=json.load(sys.stdin); \
    [print(f['status'].ljust(24), f['name']) for f in d['findings']['findings']]"
```

### 2. O estado dos portões é consultável

```bash
PYTHONPATH=src python -m silicon_atlas.cli gates
```

Reporta D0→S6 com a evidência de cada um e lista os bloqueados. É o sinal de saúde do ciclo,
não do processo.

### 3. Os falsificadores são avaliados a cada execução

`Assessment.falsifier_status()` devolve F1..F5 com critério, valor observado e se disparou.
`scripts/run_cycle.py` imprime os disparados por modelo no resumo.

### 4. A integridade do corpus é verificada a cada carga

`corpus_integrity()` compara a contagem de parâmetros derivada com a publicada. Erro acima de
0,5 % é sinal de corrupção de corpus ou de regressão na IR.

### 5. O lint é executável sobre qualquer artefato

```bash
PYTHONPATH=src python -m silicon_atlas.cli lint 99_RELEASES/reports
```

Sai com código 1 se encontrar vocabulário proibido. Adequado para gate de CI.

## Sinais de alarme e o que cada um significa

| Sinal | Como detectar | O que significa | Ação |
|---|---|---|---|
| erro de parâmetros > 0,5 % | `atlas registry list` | corpus corrompido ou IR regrediu | parar; nada a jusante é válido |
| F5 disparado | resumo do ciclo | idem, versão grave | reverter até o teste voltar a passar |
| `weakest_status` subiu sem fechar lacuna | cabeçalho do relatório | alguém burlou a propagação | auditar `derive()` e o `git diff` dos priors |
| lint com ocorrências | `atlas lint` | linguagem escapou do contrato | corrigir texto, não o lint |
| duas execuções divergem | comparar hashes dos artefatos | semente perdida ou ordenação instável | ver `REPRODUCIBILITY.md` |
| ranking do LHS estabilizou de repente | `atlas score`, campo `discriminates` | ou G-011 foi calibrada, ou alguém reponderou | verificar `DECISION_LOG` |
| região fixa deixou de ser vazia | resumo do ciclo | estabilidade subiu **ou** limiar foi afrouxado | conferir `git diff config/` |

A última linha é a mais importante. A mudança mais provável de acontecer por pressão comercial é
afrouxar `partition_policy` até a região fixa aparecer. O diff de `config/` é a defesa.

## O que **não** é observável e deveria ser

| Lacuna de observabilidade | Consequência | Custo de fechar |
|---|---|---|
| Não há histórico entre execuções | não se vê a série temporal da cobertura exata — justamente o teste de M5 em [COMPETING_MODELS](../03_UNIFICATION/COMPETING_MODELS.md) | baixo: acumular `run_id` num arquivo de série |
| Não há métrica de tempo de execução | regressão de desempenho passaria despercebida | baixo |
| ~~Dívida de evidência não quantificada~~ | — | **fechada**: `FindingSet.evidence_debt()` |
| Não há alerta quando um prior envelhece | priors de 2026 aplicados em 2028 sem revisão | baixo: campo `valid_until` nos arquivos de config |
| Não há registro de incidentes | falhas operacionais não geram aprendizado cumulativo | baixo: diretório `INCIDENTS/` com modelo de entrada |

Todas de custo baixo. Nenhuma foi feita neste ciclo porque nenhuma era necessária para o portão
A5 — e inventar observabilidade antes de haver operação é a mesma antecipação que o Método §4.1
adverte sobre escolher ferramenta antes de arquitetura.

## A métrica que o sistema vigia sobre si mesmo

> **Fração dos `Finding` emitidos cujo status é `ASSUMPTION` ou mais fraco.**

É a dívida de evidência do Método §6.3, medida em vez de estimada. Se ela subir de um ciclo para
o outro, o sistema está acumulando modelagem mais rápido do que evidência — o modo de falha mais
provável de um projeto como este, e o mais difícil de perceber de dentro.

Implementada em `FindingSet.evidence_debt()`, impressa no resumo de `run_cycle.py` e exportada
no JSON de cada assessment junto com o histograma de status.

Valor de referência em C-001 para `llama-3.1-8b`: **20 %** — 4 de 20 resultados apoiados em
premissa não demonstrada. Distribuição:

| Status | Findings |
|---|---|
| `CONDITIONAL_RESULT` | 13 |
| `ASSUMPTION` | 4 |
| `COMPUTATIONAL_EVIDENCE` | 3 |
| `OPEN_GAP` (ausência declarada) | 1 |

Nenhum `Finding` acima de `CONDITIONAL_RESULT`. É a consequência esperada de 13 lacunas abertas,
e a leitura correta: nada aqui sustenta sozinho uma decisão irreversível.
