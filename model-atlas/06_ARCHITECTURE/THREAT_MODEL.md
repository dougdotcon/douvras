---
artifact: THREAT_MODEL
cycle: C-002
---

# Modelo de ameaças

Duas categorias. A primeira é a que quase todo projeto de benchmark ignora: as ameaças à
**validade** do que o instrumento afirma. A segunda é confidencialidade.

## E — ameaças à validade

| # | Ameaça | Por que é plausível | Mitigação atual | Residual |
|---|---|---|---|---|
| E-101 | O grader concorda com quem o escreveu | Autor do corpus, do grader e das sondas são o mesmo | gabaritos e contraexemplos declarados junto com a regra; `F1` e `F2` | alta — `G-110` |
| E-102 | O corpus mede o gerador, não o mundo | 96 tarefas saem de 8 templates paramétricos | declarado em `A-103`; famílias derivadas do Documento 1 | **alta** — `G-107` |
| E-103 | Sonda ajustada até caber no grader | A tentação aparece quando `F6` dispara | promessa de cada sonda declarada antes; alterar as duas no mesmo commit é sinal de alerta | média |
| E-104 | Número sintético apresentado como medição | Estrutura de dados idêntica à da execução real | recusa no tipo (`ADR-0007`) + regra de coerência no portão | baixa |
| E-105 | Limiar afrouxado depois de o falsificador disparar | `F3` disparou; baixar 0,20 para 0,05 "resolveria" | limiar em constante nomeada, retratação registrada, `D-106` | média |
| E-106 | Escore agregado citado fora de contexto | O número 0,938 de uma sonda degenerada parece bom | `CE-101` publicado; relatório não apresenta agregado como decisão | média |
| E-107 | Contagem de parâmetros errada propaga para o "cabe?" | Dois saltos de proveniência | `A-101` declarada; campos incertos ficam nulos | média — `G-108` |

`E-102` é a mais séria e a menos mitigada. Um benchmark sintético pode ter acurácia de grader
perfeita e ainda assim medir uma habilidade que não existe fora dele.

## S — ameaças de confidencialidade

| # | Ameaça | Mitigação |
|---|---|---|
| S-101 | Tarefa de cliente vazando para serviço externo | o caminho principal não usa rede; `matlas registry verify` recusa fichas `CLIENT_SUPPLIED` |
| S-102 | Trajetória de cliente contendo dado pessoal ser commitada | corpus privado fora do repositório; o gerador só produz dados fictícios |
| S-103 | Benchmark privado de cliente sendo reusado em trabalho público | corpus por cliente em diretório separado, passado por `--corpus` |

## O que este modelo não cobre

Execução de modelo baixado da internet (ainda não acontece), superfície de ataque de um serviço
hospedado (não existe), e envenenamento de corpus por terceiro (não há contribuição externa).
Todos entram quando `G-101` fechar ou quando houver primeiro cliente.
