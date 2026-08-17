<div align="center">

# DOUVRAS

**Dois eixos de pesquisa sobre o mesmo contrato epistêmico: o que num modelo de IA está maduro
para virar silício, e o que num modelo de IA está maduro para ser medido.**

[![Método](https://img.shields.io/badge/m%C3%A9todo-DOUVRAS%202.0-1f2937)](METODO_DOUVRAS.md)
[![Testes](https://img.shields.io/badge/testes-267%20verdes-16a34a)](tests/)
[![Ciclos](https://img.shields.io/badge/ciclos-C--001%20%C2%B7%20C--002%20%C2%B7%20C--003-0d9488)](#os-dois-eixos)
[![Portões](https://img.shields.io/badge/port%C3%B5es-6%2F7%20em%20ambos%20os%20eixos-f59e0b)](#estado-dos-portões)
[![Retratações](https://img.shields.io/badge/retrata%C3%A7%C3%B5es-6%20%C2%B7%20corre%C3%A7%C3%B5es-3-b91c1c)](#o-que-o-sistema-retratou-de-si-mesmo)

[![Status máximo](https://img.shields.io/badge/status%20m%C3%A1ximo-CONDITIONAL__RESULT-7c3aed)](00_GOVERNANCE/STATUS_POLICY.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](pyproject.toml)
[![Sem GPU](https://img.shields.io/badge/requer%20GPU-n%C3%A3o-64748b)](#instalação)
[![Sem rede](https://img.shields.io/badge/requer%20rede-n%C3%A3o-64748b)](#instalação)

</div>

---

## O que é

Implementação executável do [Método DOUVRAS](METODO_DOUVRAS.md). O método não é decoração
deste repositório — ele **roda**:

- nenhum número sai de um motor sem status epistêmico;
- nenhuma conclusão é mais forte que sua dependência mais fraca, imposto por tipo e não por
  disciplina;
- nenhum relatório é emitido fora do contrato — o portão recusa;
- critérios de falha são declarados **antes** do experimento e avaliados por código.

Dois ciclos concluídos, sobre problemas diferentes. Nos dois, a resposta foi negativa — e nos
dois a negativa é o produto. Um sistema que só sabe dizer "sim" não é instrumento de decisão.

## Os dois eixos

```mermaid
flowchart TD
    C["<b>douvras_core</b><br/>status · portões · portão de emissão<br/><i>1 009 linhas, zero domínio</i>"]
    C --> S["<b>Silicon Atlas</b><br/>ciclo C-001<br/>o que vira hardware"]
    C --> M["<b>Model Atlas</b><br/>ciclo C-002<br/>o que dá para medir"]
    S --> SR["região endurecível <b>vazia</b><br/>teto de Amdahl 1,00×"]
    M --> MR["instrumento <b>verificado</b><br/>escore agregado <b>retratado</b>"]
    SR --> C2["codesign<br/><i>invariante comportamental ∩ arquitetural</i>"]
    MR --> C2

    style C fill:#1e293b,stroke:#0d9488,stroke-width:3px,color:#fff
    style S fill:#334155,color:#fff
    style M fill:#334155,color:#fff
    style C2 fill:#78350f,color:#fff
```

O nó de codesign está em marrom porque **ainda não existe**: ele só é calculável quando houver
capacidade medida em mais de um modelo. Uma interface entre os dois eixos hoje seria
acoplamento sem conteúdo.

| | [Silicon Atlas](silicon-atlas/) | [Model Atlas](model-atlas/) |
|---|---|---|
| pergunta | que parte deste modelo está estável, dominante em custo e tolerante a baixa precisão o bastante para virar silício? | em qual capacidade este modelo falha, e o instrumento que mede isso é confiável? |
| entrada | 9 `config.json`, 5 famílias | 96 tarefas pt-BR, 8 capacidades, 132 contraexemplos |
| produto | Silicon Readiness Assessment | Model Capability Assessment |
| resposta do ciclo | **não**: nenhum caso justifica máscara com a evidência disponível | **ainda não**: nenhum modelo executado; o instrumento, sim, foi verificado |
| falsificadores disparados | 3 de 5 | 1 de 6 |
| portão bloqueado | V3 | V3 |

## Instalação

```bash
pip install -e ".[dev]"        # numpy, pyyaml, pytest — nada mais
python -m pytest tests         # 267 testes
```

Nenhum dos dois eixos exige GPU, pesos de modelo, `torch` ou rede no caminho principal
([ADR-0001](silicon-atlas/06_ARCHITECTURE/ADR/ADR-0001-ir-analitica.md) ·
[ADR-0006](model-atlas/06_ARCHITECTURE/ADR/ADR-0006-execucao-opcional.md)). Os dois assessments
rodam **antes** de qualquer NDA e antes de qualquer compra de hardware.

```bash
python scripts/run_silicon_cycle.py    # ciclo C-001: 9 assessments de silício
python scripts/build_task_corpus.py    # gera as 96 tarefas do BR-Agent-Bench
python scripts/run_model_cycle.py      # ciclo C-002: 3 assessments de capacidade
```

---

## O contrato epistêmico, em código

```mermaid
flowchart TD
    subgraph entrada["Entradas com status próprio"]
        A1["IR analítica<br/><code>ASSUMPTION</code>"]
        A2["acurácia do grader<br/><code>COMPUTATIONAL_EVIDENCE</code>"]
        A3["priors não calibrados<br/><code>OPEN_GAP</code>"]
    end
    A1 --> D{"derive()<br/>min(status dos pais, teto)"}
    A2 --> D
    A3 --> D
    D --> R["resultado<br/><code>CONDITIONAL_RESULT</code>"]
    R -.->|"tentar promover"| X["StatusViolation"]

    style X fill:#7f1d1d,color:#fff,stroke:#dc2626
    style R fill:#1e3a5f,color:#fff
    style A3 fill:#78350f,color:#fff
```

Este bloco é literalmente o mesmo código nos dois eixos. Um `Finding` de custo analítico e um
`Finding` de capacidade medida se combinam pela mesma regra do elo mais fraco — e é isso que
torna o codesign possível depois, em vez de exigir tradução entre dois vocabulários.

A extração do core foi o **teste** dessa afirmação: se a escala de status só servisse para
hardware, seria vocabulário de domínio disfarçado de epistemologia. Ela migrou sem uma linha de
adaptação ([ADR-0005](model-atlas/06_ARCHITECTURE/ADR/ADR-0005-douvras-core.md)), e
`tests/core/` a valida sem importar nenhum dos dois atlas.

---

## Resultados

### Silicon Atlas — ciclo C-001

Nos nove modelos, **nenhum papel passa simultaneamente pelos três limiares** de estabilidade,
economia e quantização. Região endurecível vazia, teto de Amdahl **1,00×** — um ganho de 100×
é inalcançável nesta partição por aritmética, independentemente do silício.

Com região fixa vazia, o simulador **recusa** dimensionar um acelerador: não emite área, NRE
nem break-even. A recusa em produzir números sobre um objeto inexistente é o produto.

Detalhes em [silicon-atlas/README.md](silicon-atlas/README.md).

### Model Atlas — ciclos C-002 e C-003

**O instrumento, verificado antes de medir alguém:**

| Medida | Valor |
|---|---:|
| aceitação do gabarito | **100,0 %** (96/96) |
| rejeição de contraexemplo | **100,0 %** (132) |
| precisão do rótulo | **100,0 %** |
| **margem de discriminação agregada** | **0,062** ← abaixo do limiar de 0,20 |

O grader aceita todo gabarito e rejeita todo contraexemplo com o rótulo certo. O **escore
agregado**, porém, não separa um respondente correto de um degenerado: cada sonda ataca uma
família e o agregado dilui o dano pelo corpus inteiro. `C-102` foi retratada.

**Dois modelos medidos**, mesmas 96 tarefas, mesmo prompt, mesma quantização, mesma máquina:

| | `tucano-2b4-instruct` | `smollm3-3b` |
|---|---:|---:|
| chamadas de ferramenta | **0** | **78** |
| passos numa mesma tarefa | sempre 1 | até 6 |
| escore geral | 0,0 % | **10,4 %** |
| `arguments` | 0,0 % | **50,0 %** |
| `error_recovery` | 0,0 % | **33,3 %** |

O Tucano não erra a ferramenta: **nunca chega a chamar uma**. Devolve o schema com valores de
exemplo — `"ferramenta": "nome_da_ferramenta"` copiado literalmente. O SmolLM3 executa o
protocolo; o que falha nele é a **escolha** da ferramenta, não a forma da ação.

**E os 10,4 % do SmolLM3 são piso, não capacidade.** Ele foi medido em `/no_think`, mas o modo
padrão dele é `/think`. Nas mesmas 71 tarefas (pareado contra o publicado): **14,1 % → 21,1 %**,
+7,0 pontos.

O efeito **não é uniforme por capacidade**, e essa é a parte que a amostra inicial de 16 tarefas
não mostrava direito: `hallucination` salta de 0 % para 83,3 %, mas `arguments` cai de 50 % para
41,7 % e `error_recovery` cai de 33,3 % para 0 %. Raciocinar não é estritamente "mesma ação,
julgamento melhor" — muda o comportamento em direções diferentes por capacidade, e as chamadas
de ferramenta por tarefa **caem** com raciocínio ligado (0,81/tarefa → 0,49/tarefa), não ficam
iguais. Uma afirmação anterior nesta mesma linha de pesquisa dizia o contrário — foi retratada
por [R-103](model-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md#r-103) quando a amostra
cresceu de 16 para 71 tarefas e o padrão simples não se sustentou.

Com isso, `C-108` — *"modelos de 2B a 3B não instanciam chamada de ferramenta"* — foi
**retratada no mesmo ciclo em que foi registrada**, pelo falsificador que ela própria declarou.
Porte não era a variável.

**E a segunda medição não desfez a primeira retratação.** A margem agregada entre os dois
modelos é **0,104**, ainda abaixo do limiar de 0,20 — entre um modelo que nunca chama ferramenta
e um que chama 78 vezes. O sinal está no perfil por capacidade (+0,500 em `arguments`), não no
agregado. Isso **reforça** `R-101` em vez de enfraquecê-la.

No caminho, o eixo encontrou um defeito no artefato publicado de um dos modelos: **o template de
chat embutido no GGUF do Tucano está errado** e faz qualquer ferramenta padrão receber saída
degenerada.

Detalhes em [model-atlas/README.md](model-atlas/README.md).

---

## O que o sistema retratou de si mesmo

Seis afirmações publicadas foram retiradas pelos próprios critérios declarados antes.

| # | Eixo | Afirmação retirada | O que a derrubou |
|---|---|---|---|
| [R-001](silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | silício | o ranking do LHS é estável | falsificador F3, declarado antes |
| [R-002](silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | silício | banda `optimized_kernel` em 8 dos 9 relatórios | o fator vinha de um acelerador que o próprio relatório declarava inexistente |
| [R-003](silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | silício | "nenhum NRE foi estimado" | falso no mesmo `run_id`: o Markdown suprimia, o JSON publicava |
| [R-004](silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | silício | estabilidade 1,000 para famílias sem transição | o sistema premiava **ausência de dado** |
| [R-005](silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | silício | três afirmações do README | intervalo escrito de memória em vez de calculado |
| [R-101](model-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | capacidade | o escore agregado do benchmark discrimina | falsificador F3, com 0,062 contra o limiar de 0,20 |

Em nenhum dos seis casos a métrica foi redefinida para caber no resultado. Redefinir um
falsificador depois de vê-lo disparar é ajustar o instrumento ao resultado, e está proibido por
decisão registrada nos dois eixos (`D-008`, `D-106`).

### E três correções, encontradas ao conferir os corpora contra a fonte

Nenhuma alegação caiu, mas números publicados estavam errados — e nenhum dos três era
detectável sem sair do repositório.

| # | Eixo | O que estava errado |
|---|---|---|
| [COR-001](silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | silício | `phi-3-mini-4k` sem `sliding_window: 2047`: a IR modelava atenção quadrática num modelo de janela deslizante |
| [COR-101](model-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | capacidade | `tucano2-0.5b` declarado `Qwen2ForCausalLM`, inferido do nome do repositório; o checkpoint diz `Qwen3ForCausalLM` |
| [COR-102](model-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md) | capacidade | `qwen3.5-0.8b` tem **0,8734 B** parâmetros, não 0,8 — 8,4 % de erro no footprint, para menos |

`COR-001` é o caso instrutivo: o falsificador `F5` compara contagem de parâmetros derivada com
publicada, e `sliding_window` **não afeta contagem de parâmetros** — afeta custo. O erro
atravessou um corpus inteiro com erro de parâmetros de 0,00 %. Verificação interna não
substitui a fonte, e é exatamente para isso que a lacuna existia.

---

## Estado dos portões

```bash
PYTHONPATH=src python -m silicon_atlas.cli gates
PYTHONPATH=src python -m model_atlas.cli gates
```

| Portão | Silicon Atlas | Model Atlas |
|---|:---:|:---:|
| **D0** — identidade do problema | ✅ | ✅ |
| **O1** — cobertura observacional | ✅ | ✅ |
| **U2** — estrutura candidata | ✅ | ✅ |
| **V3** — sobrevivência mínima | ❌ | ❌ |
| **R4** — estrutura mínima operável | ✅ | ✅ |
| **A5** — protótipo verificável | ✅ | ✅ |
| **S6** — operação cumulativa | ✅ | ✅ |

V3 está bloqueado nos dois eixos **por decisão, não por omissão**: o Método §6.7 exige que a
validação final não dependa de quem criou o resultado. Agentes revisando agentes não fecham
esse portão, e os dois diretórios de revisão externa estão vazios de propósito.

---

## Estrutura

```text
DOUVRAS/
├── METODO_DOUVRAS.md          o método completo — as sete fases, os portões, os contratos
├── 00_GOVERNANCE/             política de status e decisões de nível monorepo
├── docs/                      a tese que originou o eixo de capacidade (3 documentos)
│
├── src/
│   ├── douvras_core/          1 009 linhas — status, portões, emissão. Zero domínio.
│   ├── silicon_atlas/         6 390 linhas — IR, roofline, invariantes, partição, economia
│   └── model_atlas/           3 168 linhas — tarefas, graders, sondas, capacidade, CSS
│
├── silicon-atlas/             ciclo C-001: 7 fases DOUVRAS, priors, corpus, 9 assessments
├── model-atlas/               ciclo C-002: 7 fases DOUVRAS, priors, corpus, 3 assessments
│
├── scripts/
│   ├── run_silicon_cycle.py   regenera os artefatos do eixo de silício
│   ├── run_model_cycle.py     regenera os artefatos do eixo de capacidade
│   └── build_task_corpus.py   gera o BR-Agent-Bench a partir dos templates
│
└── tests/
    ├── core/                  27 testes — o contrato, sem nenhum domínio
    ├── silicon/               149 testes
    └── model/                 91 testes
```

Arquivos marcados **[GERADOS]** dentro dos projetos não devem ser editados: são saída, não
entrada. O que se edita são os priors em `config/`, os corpora, os templates de tarefa e as
alegações em `CLAIM_LEDGER.yaml`.

---

## ⚠️ Limitações honestas

Este repositório **não** demonstra que qualquer modelo deva virar ASIC, **não** mede a
capacidade de nenhum modelo, e **não** substitui síntese física nem avaliação humana.

**No eixo de silício** — o roofline não foi calibrado contra latência medida; a tolerância à
quantização é prior de literatura; a energia do alvo especializado é modelo analítico comparado
com TDP de GPU, assimetria que favorece estruturalmente o alvo. **12 lacunas abertas e 2
parciais.**

**No eixo de capacidade** — o corpus é sintético e até prova em contrário mede o gerador, não o
mundo; as sondas foram escritas por quem escreveu o grader; os priors do CSS nunca foram
calibrados; as medições cobrem **dois** modelos, **uma** quantização e **uma** versão de prompt,
e a diferença entre eles não tem explicação medida. **13 lacunas abertas e 3 parciais.**

**Nos dois** — o limiar que produz a conclusão do ciclo não tem base empírica. No silício é
`min_stability = 0,60`; na capacidade é a margem de `0,20`. Nos dois casos, afrouxar o limiar é
a manobra mais provável sob pressão comercial, e nos dois casos ele mora em arquivo ou constante
nomeada: agora aparece no `git diff`.

Enquanto houver lacuna aberta, nenhum resultado passa de `CONDITIONAL_RESULT` — literalmente:
tentar promover levanta `StatusViolation`.

---

## Posição estratégica

> **Ser a camada de descoberta e auditoria que determina o que merece virar chip e o que merece
> virar dataset — e que diz "ainda não" quando for o caso, com a aritmética à vista.**

Um assessment que conclui *"não vale a pena fabricar"* é uma entrega bem-sucedida. Um benchmark
que conclui *"meu próprio escore agregado não decide nada"* também. Um sistema que sempre
recomendasse agir seria mais fácil de vender e destruiria o único ativo que o produto tem.

O modelo comercial derivado disso está em
[docs/03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md](docs/03_MODELO_DE_NEGOCIO_E_PRECIFICACAO.md).

---

<div align="center">

**DOUVRAS Labs** — Muitas formas. Uma estrutura.

<sub>Da hipótese à estrutura. Da estrutura ao teste. Do teste ao sistema.</sub>

</div>
