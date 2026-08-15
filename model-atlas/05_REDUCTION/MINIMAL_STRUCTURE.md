---
artifact: MINIMAL_STRUCTURE
cycle: C-002
gate: R4
date: 2026-08-14
---

# Unidade Mínima Invariante — UMI

Não *"qual é a plataforma completa que queremos"*, e sim **qual é a menor estrutura que preserva
o valor observado**. Tudo o que sobrar depois dela é conveniência.

---

## UMI-101 — `(tarefa com ambiente executável, regra declarada, contraexemplo rotulado)`

### Função preservada

Dizer, com veredicto rotulado e reproduzível, **em qual capacidade uma trajetória falhou** — e
provar que o veredicto é confiável antes de aplicá-lo a alguém.

### Componentes obrigatórios

| Componente | Por quê |
|---|---|
| `tasks.Environment` | sem ambiente executado, a observação é escrita pelo respondente e alucinação vira invisível |
| `tasks.EvalTask.rules` | a regra de acerto declarada no dado, não em código por tarefa |
| `graders.grade` | aplica a regra e devolve **rótulo**, não booleano |
| `EvalTask.gold` | o exemplo de acerto que a própria regra precisa aprovar |
| `EvalTask.counterexamples` | os exemplos de erro que a regra precisa reprovar, cada um com o motivo esperado |

### Componentes removidos e ainda assim o valor sobrevive

Registro de modelos, fingerprint de capacidade, Failure Atlas, CSS, orçamento de memória,
assessment, sondas de calibração. E também: pesos, GPU, rede, `torch`.

Quem rodasse apenas a UMI-101 já teria o que quase nenhum benchmark de agente publica — a
evidência de que o próprio grader aceita o certo e rejeita o errado pelo motivo certo.

### Aproximações aceitas

- A tarefa é sintética e o ambiente é um interpretador de seis tipos de ferramenta (`A-103`).
- A dificuldade é declarada por autoria, não calibrada (`G-106`).
- O ótimo das tarefas de numeracia é calculado por quem escreveu o grader (`G-109`).

### Limites de validade

Vale para agente de turno curto com ferramentas nomeadas e ambiente determinístico, em
português brasileiro. **Não** vale para: diálogo longo com estado implícito, ferramentas cujo
efeito depende de tempo real, tarefas cuja resposta correta é uma questão de julgamento, nem
avaliação de qualidade de texto livre.

### Interfaces

```text
entrada: EvalTask (JSON) + Trajectory
saída:   GradeResult {passed, failures: [FailureMode], details}
```

### Métricas antes e depois da redução

| | Antes (Model Atlas completo) | Depois (UMI-101) |
|---|---|---|
| módulos necessários | 9 | 2 |
| entradas externas | corpus de tarefas, corpus de modelos, 2 arquivos de priors | corpus de tarefas |
| premissas carregadas | A-101 … A-106 | A-103 |
| status máximo alcançável | `CONDITIONAL_RESULT` | `COMPUTATIONAL_EVIDENCE` |

A redução **sobe** o status máximo: menos premissas, conclusão mais forte. É o mesmo argumento
que fez a UMI-1 do Silicon Atlas ser o produto a vender primeiro.

---

## UMI-102 — `(sonda declarada, modo prometido) → o grader vê?`

### Função preservada

Impedir que um benchmark seja publicado sem evidência de que enxerga a falha que afirma medir.

### Componentes obrigatórios

`UMI-101` · `runner.PROBES` · `instrument.probe_expectations`

### Por que é mínima

Uma tabela de duas colunas — sonda e modo prometido — escrita **antes** da execução, mais a
comparação com o que de fato disparou. Não precisa de modelo, de priors, de score nem de peso.
E responde à pergunta que decide se vale seguir: *este instrumento está pronto para medir?*

### Limites de validade

Prova que o grader detecta o modo **na forma em que a sonda o produz** (`A-106`). Um modelo real
erra por caminhos que quem escreveu o grader não antecipou — e é exatamente por isso que a
revisão externa (`G-110`) não é substituível por mais sondas.

---

## O que a redução revelou

O componente mais elaborado do Model Atlas — o CSS, com cinco fatores, pesos versionados e
análise de sensibilidade — **não** entrou em nenhuma das duas UMIs. E o ciclo mostrou por quê:
sem capacidade medida ele não tem entrada, e o escore agregado do qual ele dependeria já foi
retratado ([R-101](../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)).

A parte que mais parecia produto foi de novo a que menos preservava valor. É a segunda vez que
a fase R diz isso em dois ciclos, sobre dois eixos diferentes.
