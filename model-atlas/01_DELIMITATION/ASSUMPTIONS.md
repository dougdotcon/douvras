---
artifact: ASSUMPTIONS
cycle: C-002
date: 2026-08-14
---

# Premissas

Cada premissa é uma coisa que o sistema **usa** e **não demonstrou**. Todo `Finding` derivado
delas carrega o id aqui declarado, e é isso que faz a dívida de evidência ser medida em vez de
estimada.

| # | Premissa | Por que é aceita agora | O que a derruba |
|---|---|---|---|
| **A-101** | A contagem de parâmetros dos modelos do corpus é a declarada nos documentos de origem, aproximada | A fonte diz "cerca de"; transformar em inteiro exato inventaria dígitos | `matlas registry verify` contra o Hub (`G-108`) |
| **A-102** | Os bytes por parâmetro efetivos de cada quantização GGUF são os da tabela `BYTES_PER_PARAM` | São constantes de engenharia do formato, estáveis entre modelos da mesma família | medir o arquivo `.gguf` real e comparar com o calculado |
| **A-103** | Uma tarefa sintética com ambiente executável mede a mesma capacidade que a situação real correspondente | Permite construir corpus sem tráfego de cliente e sem NDA | correlação baixa entre escore no corpus e desempenho em traços reais (`G-107`) |
| **A-104** | Tratabilidade, valor, custo e estabilidade de cada capacidade são os priors de `capability_priors.v1.json` | São necessários para o CSS existir; nenhum dado de calibração está disponível | três casos com desfecho conhecido (`G-104`) |
| **A-105** | Uma margem de 0,20 entre respondente correto e degenerado é suficiente para chamar um escore de discriminante | É a ordem de grandeza usada como corte no `LHS` do Silicon Atlas | replicação contra benchmark público com desfecho conhecido (`G-105`) |
| **A-106** | Uma sonda de calibração que dispara um modo de falha prova que o grader detecta aquele modo **quando ele é injetado desta forma** | É verificável offline e não depende de modelo | um modelo real exibindo o mesmo modo por outro caminho e passando no grader |

## O que estas premissas **não** autorizam

Nenhuma delas autoriza uma frase sobre a capacidade de um modelo. `A-106` é a mais fácil de
esticar indevidamente: ela diz que o grader vê a falha *na forma em que a sonda a produz*. Um
modelo real erra de formas que nenhuma sonda escrita por quem fez o grader vai antecipar — e
esse é precisamente o argumento a favor de `G-110`, a revisão externa.
