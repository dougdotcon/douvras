---
artifact: DATA_SOURCES
cycle: C-002
date: 2026-08-14
---

# Fontes de dados

Cada fonte declara **tipo de evidência**. As categorias não se misturam: uma constante de
engenharia e uma medição publicada não têm o mesmo peso, e somar as duas numa média é o começo
de todo relatório que engana.

| Fonte | Tipo | O que fornece | Status máximo que autoriza |
|---|---|---|---|
| `scripts/build_task_corpus.py` | **construção própria** | as 96 tarefas, seus gabaritos e contraexemplos | `COMPUTATIONAL_EVIDENCE` sobre o instrumento; nada sobre o mundo |
| `docs/01_TESE_...md` §5, §11 | **documento secundário** | ficha dos três modelos do corpus | `ASSUMPTION` (`A-101`) |
| `docs/02_ARQUITETURA_...md` §6 | **documento secundário** | correspondência de módulos e ideia do CSS | `DEFINITION` |
| tabela `BYTES_PER_PARAM` | **constante de engenharia** | bytes por parâmetro por quantização GGUF | `ASSUMPTION` (`A-102`) |
| `config/capability_priors.v1.json` | **prior declarado** | tratabilidade, valor, custo, estabilidade | `ASSUMPTION` (`A-104`) |
| `config/css_weights.v1.json` | **decisão de projeto** | pesos do CSS e semente | `ENGINEERING_DECISION` sobre si mesmo |
| execução das sondas | **evidência computacional** | acurácia do grader, cobertura da taxonomia | `COMPUTATIONAL_EVIDENCE` |
| execução de modelo real | **ausente** | — | bloqueado por `G-101` |

## O que **não** é fonte

- **Nenhum tráfego real de agente.** Todas as tarefas saem de oito templates paramétricos
  (`A-103`, `G-107`). O corpus mede o gerador até prova em contrário.
- **Nenhum card de modelo lido diretamente.** As fichas foram transcritas dos documentos
  internos, que por sua vez citam posts e coleções. Dois saltos de proveniência, declarados em
  `G-108`.
- **Nenhuma medição de latência, memória ou qualidade.** `G-102` e `G-103`.

## Baseline congelado

`BASELINE-2026-08-14`. Alterar corpus, priors ou pesos exige nova comparação e entrada no
`DECISION_LOG` — caso contrário, uma melhora de escore entre ciclos pode ser só uma tarefa que
ficou mais fácil.
