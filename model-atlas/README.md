<div align="center">

# DOUVRAS Model Atlas

**Descobre em qual capacidade um modelo pequeno falha, com rótulo acionável — e verifica o
instrumento que faz essa medida antes de existir qualquer modelo para medir.**

[![Método](https://img.shields.io/badge/m%C3%A9todo-DOUVRAS%202.0-1f2937)](../METODO_DOUVRAS.md)
[![Ciclo](https://img.shields.io/badge/ciclo-C--002%20conclu%C3%ADdo-0d9488)](04_VALIDATION/EXPERIMENTS/X-002-RESULT.md)
[![Testes](https://img.shields.io/badge/testes-82%20verdes-16a34a)](../tests/model/)
[![Portões](https://img.shields.io/badge/port%C3%B5es-6%2F7%20%E2%80%94%20V3%20bloqueado-f59e0b)](#portões-do-ciclo)
[![Lacunas](https://img.shields.io/badge/lacunas-10%20abertas-dc2626)](02_OBSERVATION/GAP_REGISTER.md)

[![Falsificadores](https://img.shields.io/badge/falsificadores-1%20de%206%20disparado-b91c1c)](00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)
[![Corpus](https://img.shields.io/badge/BR--Agent--Bench-96%20tarefas%20%C2%B7%20132%20contraexemplos-0369a1)](corpus/tasks/)
[![Sem GPU](https://img.shields.io/badge/requer%20GPU-n%C3%A3o-64748b)](06_ARCHITECTURE/ADR/ADR-0006-execucao-opcional.md)
[![Sem pesos](https://img.shields.io/badge/requer%20pesos-n%C3%A3o-64748b)](06_ARCHITECTURE/ADR/ADR-0006-execucao-opcional.md)

</div>

---

## O que é

O eixo de **capacidade** do [DOUVRAS](../README.md). O [Silicon Atlas](../silicon-atlas/)
pergunta que parte de um modelo está madura para virar hardware; este pergunta o que o modelo
sabe fazer — antes de alguém gastar máscara ou GPU descobrindo.

O ciclo C-002 responde uma pergunta que quase todo projeto de benchmark pula:

> **o grader aceita o certo, rejeita o errado, e pelo motivo certo?**

Ela não precisa de GPU, não precisa de pesos e não precisa de rede. E se a resposta for não,
todo escore publicado depois é ruído com autoridade.

## Instalação e uso

A partir da raiz do monorepo:

```bash
pip install -e ".[dev]"
python scripts/build_task_corpus.py       # gera as 96 tarefas
python -m pytest tests/core tests/model   # 82 testes
python scripts/run_model_cycle.py         # ciclo completo
```

---

## Resultados do ciclo C-002

### 1 · O instrumento foi verificado antes de medir alguém

| Medida | Valor | Alvo |
|---|---:|---:|
| aceitação do gabarito | **100,0 %** (96/96) | 100 % |
| rejeição de contraexemplo | **100,0 %** (132) | 100 % |
| precisão do rótulo | **100,0 %** | 100 % |
| determinismo entre execuções | **idêntico** | idêntico |
| modos de falha sem sonda | **nenhum** | nenhum |

Cada tarefa carrega a regra de acerto, a trajetória de referência que a regra precisa aprovar,
e trajetórias sabidamente erradas que a regra precisa reprovar — cada uma rotulada com o modo
de falha que exibe. Escrever os três lado a lado é o que impede a regra de divergir do que a
tarefa afirma medir.

### 2 · O ambiente é executado, não descrito

```text
respondente  ──propõe──►  chamada de ferramenta
     ▲                             │
     └────── observação ──── ambiente determinístico
```

Nenhum respondente escreve a própria observação. Sem isso, quem inventa o saldo e quem consulta
o saldo produzem o mesmo registro — e alucinação, o modo de falha mais caro em agentes, fica
invisível para o grader.

### 3 · O escore agregado **não** discrimina — e isso foi retratado

Falsificador **F3 disparado**: margem de **0,062** contra o limiar declarado de 0,20.

| Sonda | Escore | Tarefas no alvo | Queda no alvo | Queda agregada |
|---|---:|---:|---:|---:|
| `oraculo` | 1,000 | — | — | — |
| `resposta-direta` | 0,000 | 36 | 1,000 | 1,000 |
| `argumento-errado` | 0,688 | 30 | 1,000 | 0,312 |
| `desiste-no-erro` | 0,875 | 12 | **1,000** | **0,125** |
| `plano-invertido` | 0,938 | 24 | 0,250 | **0,062** |

`desiste-no-erro` destrói **100 %** das tarefas que ataca e move o agregado em 0,125, porque
essas tarefas são 12,5 % do corpus. Um instrumento lido pelo agregado chamaria isso de
"respondente com 87,5 % de acerto".

O escore agregado não é uma medida ruim de uma capacidade — é uma medida boa de nada em
particular. Diagnóstico em [CE-101](04_VALIDATION/COUNTEREXAMPLES/CE-101-margem-agregada-diluida.md),
retratação em [R-101](00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md).

**A métrica de `F3` não foi trocada.** Redefinir um falsificador depois de vê-lo disparar é
ajustar o instrumento ao resultado.

### 4 · A primeira medição real: 0 % em 96 tarefas, com **zero** chamadas de ferramenta

`tucano-2b4-instruct` Q4_K_M, em CPU, prompt `agent-ptbr-v2`, temperatura 0:

| Medida | Valor |
|---|---:|
| escore geral | **0,0 %** (0/96) |
| chamadas de ferramenta emitidas | **0** |
| tokens/s (geração) | 12,14 |
| TTFT médio | 6,42 s |

O modelo não erra a ferramenta — **nunca chega a chamar uma**. Toda trajetória termina no
primeiro passo com um JSON que tem a forma do contrato e valores de exemplo:

```json
{"acao": "chamar", "ferramentas": "nome_daferramentas", "argumentos": {"campos": "valor"}}
```

Ele **descreve** o protocolo em vez de executá-lo. Fora do protocolo, responde português
normalmente — não é incapacidade de língua nem de instrução.

**A hipótese óbvia foi testada e rejeitada.** Um exemplo demonstrado injetado no prompt
(`G-112`, modo diagnóstico, 16 tarefas nas oito capacidades) manteve 0,0 % e zero chamadas. O
zero-shot não estava medindo falta de exemplo.

Os três modelos sem pesos locais continuam saindo como **ausência declarada**, não como zero —
a recusa é imposta por tipo ([ADR-0007](06_ARCHITECTURE/ADR/ADR-0007-sondas-nao-sao-modelos.md)):

```text
CapabilityFingerprint.from_run(execução sintética)
    → todas as capacidades = None, OPEN_GAP, G-101
```

### 4.1 · E um defeito no artefato publicado do modelo

O template de chat embutido no GGUF **está errado** (`G-114`):

| Prompt | Saída |
|---|---|
| `<instruction>Qual é a capital da França?` | `</instruction>A capital da França é Paris…` |
| `<instruction>…</instruction>` ← o que o template monta | `FFQuala</</. A PerguntQualfQual…` |

O template fecha a tag no prompt; o modelo foi treinado para emitir essa tag. O tokenizer está
correto e não depende de BOS. **Toda ferramenta que aplique o template publicado** — llama-server
com `--jinja`, `apply_chat_template`, Ollama, LM Studio — recebe saída degenerada desse modelo,
e publicaria zero atribuindo ao modelo.

### 5 · O que a aritmética já responde: cabe em 16 GB

`smollm3-3b`, o maior do corpus, com folga de runtime de 1,20×:

| Quantização | Pesos | Com folga | Cabe em 16 GB? | Qualidade |
|---|---:|---:|:---:|:---:|
| `f16` | 6,00 GB | 7,20 GB | sim | — |
| `q8` | 3,18 GB | 3,82 GB | sim | — |
| `q4` | 1,68 GB | 2,02 GB | sim | — |

A coluna **Qualidade** está vazia porque nenhuma perplexidade foi medida (`G-103`). É a coluna
que decide a escolha de quantização, e a única que a aritmética não dá. TTFT, tokens/s e RAM de
pico saem como `OPEN_GAP` — não existe fórmula honesta para latência numa máquina que nunca
executou o modelo.

---

## Portões do ciclo

```bash
PYTHONPATH=src python -m model_atlas.cli gates
```

| Portão | Estado | Evidência |
|---|:---:|---|
| **D0** — identidade do problema | ✅ | carta com pergunta, baseline congelado, não objetivos e critérios F1..F6 |
| **O1** — cobertura observacional | ✅ | 96 tarefas em 8 capacidades, 3 modelos, cobertura mínima atendida |
| **U2** — estrutura candidata | ✅ | 4 modos de falha atravessam mais de uma capacidade; casos que não se encaixam nomeados |
| **V3** — sobrevivência mínima | ❌ | instrumento não discrimina (`CE-101`); sem revisão adversarial **humana** (`G-110`) |
| **R4** — estrutura mínima operável | ✅ | duas UMIs com função preservada, componentes e limites de validade |
| **A5** — protótipo verificável | ✅ | suíte verificada: 82 testes (core + capacidade) |
| **S6** — operação cumulativa | ✅ | ledger, changelog, retratações e operação presentes |

---

## Linha de comando

```bash
matlas registry list                 # modelos registrados e proveniência
matlas tasks list                    # corpus por capacidade
matlas tasks validate                # toda tarefa tem regra que algum grader implementa
matlas instrument                    # o benchmark mede o que diz medir?
matlas probes                        # cada sonda dispara o modo que prometeu
matlas failures                      # Failure Atlas
matlas capability qwen3.5-0.8b       # vetor de capacidades (ou as ausências declaradas)
matlas css qwen3.5-0.8b              # alvo de especialização e diagnóstico de discriminação
matlas profile smollm3-3b --ram 16   # memória por quantização
matlas assess qwen3.5-0.8b -o r.md   # Model Capability Assessment completo
matlas gates                         # estado dos portões D0 → S6
matlas lint 99_RELEASES/reports      # vocabulário proibido
```

---

## ⚠️ Limitações honestas

Este sistema **não** mede nenhum modelo, **não** publica ranking e **não** substitui avaliação
humana de qualidade.

- **O corpus é sintético.** 96 tarefas saem de 8 templates paramétricos. Até prova em
  contrário, ele mede o gerador e não o mundo (`A-103`, `G-107`). É a limitação mais séria e a
  menos mitigada.
- **As sondas foram escritas por quem escreveu o grader.** Elas provam que o grader vê a falha
  *na forma em que a sonda a produz* (`A-106`). Um modelo real erra por caminhos que quem
  escreveu o corpus não antecipou — e é exatamente por isso que mais sondas não substituem
  `G-110`.
- ~~Nenhuma ficha de modelo foi conferida na fonte~~ — **`G-108` fechada em 2026-08-15**: as
  três fichas foram conferidas contra o Hub, com hash e data. Achou dois erros de transcrição
  ([COR-101, COR-102](00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)), incluindo `qwen3.5-0.8b`
  com 8,4 % a menos de parâmetros que o checkpoint real.
- **Os priors do CSS nunca foram calibrados** (`G-104`). Quatro dos cinco fatores são palpite
  de engenharia.
- **O limiar de 0,20 que retratou `C-102` não tem base empírica** (`G-105`). Um valor de 0,05
  mudaria a conclusão do ciclo. Por isso ele mora numa constante nomeada — afrouxá-lo é a
  manobra mais provável depois de um falsificador disparar, e agora aparece no `git diff`.

São **11 lacunas abertas** em [GAP_REGISTER](02_OBSERVATION/GAP_REGISTER.md).

### Como derrubar este trabalho

| # | Ataque | O que cai se der certo |
|---|---|---|
| 1 | Conferir à mão o gabarito de dez tarefas | `C-101`; em `BRAB-NUM-*`, fecha `G-109` |
| 2 | Escrever trajetória que erra só o argumento e ver o rótulo | a precisão de rótulo de `C-101` |
| 3 | Nomear um modo de falha real que a taxonomia não cobre | `C-104` |
| 4 | Baixar uma ficha do Hub e comparar campo a campo | `A-101`, fecha `G-108` |
| 5 | Executar um modelo quantizado e comparar com o footprint | `A-102`, fecha `G-102` |
| 6 | Correlacionar escore no corpus com traços reais | `A-103`, fecha `G-107` |

O item 6 é o mais caro e o mais importante.

---

<div align="center">

<sub>Do problema ao benchmark. Do benchmark ao baseline. Do baseline ao dataset.</sub>

</div>
