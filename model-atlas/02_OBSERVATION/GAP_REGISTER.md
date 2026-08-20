---
artifact: GAP_REGISTER
cycle: C-002
date: 2026-08-14
---

# Registro de lacunas — Model Atlas

Lacuna aberta não impede o ciclo — impede que o resultado seja promovido acima de
`CONDITIONAL_RESULT`. Ver [STATUS_POLICY](../../00_GOVERNANCE/STATUS_POLICY.md).

A numeração começa em `G-101` para não colidir com o `GAP_REGISTER` do Silicon Atlas, que
ocupa `G-001`..`G-014`. Os dois eixos compartilham o core, não o registro de lacunas: uma
lacuna é sempre lacuna *de alguma coisa*.

| Gap | Por que importa | Evidência necessária | Bloqueia | Status |
|---|---|---|---|---|
| G-101 | Nenhum modelo real foi executado: todas as capacidades são ausência declarada | Pesos locais + suíte executada com o extra `[run]` | qualquer afirmação sobre capacidade de modelo; CSS | **PARCIAL** — `tucano-2b4-instruct` e `smollm3-3b` executados nas 96 tarefas em 2026-08-15 ([RUN](../99_RELEASES/runs/)). Os outros 2 do corpus continuam sem pesos |
| G-102 | Sem telemetria: TTFT, tokens/s e RAM de pico não foram observados | Execução instrumentada em quantização declarada | recomendação de quantização operacional | **PARCIAL** — tokens/s e TTFT medidos nas duas execuções; RAM de pico continua sem instrumentação |
| G-103 | Precision cliff não medido: a coluna Qualidade da tabela de quantização está vazia | Perplexidade ou escore de capacidade por precisão, na mesma suíte | escolha de quantização; fecha junto com G-101 | OPEN |
| G-104 | Priors de capacidade (tratabilidade, valor, custo, estabilidade) nunca calibrados | Três casos com desfecho conhecido: medir, construir dataset, medir de novo | fator do CSS; qualquer alvo de especialização | **PARCIAL** — 1/3 casos tentado: `structured_output`, LoRA em `smollm2-360m-instruct`, 80 exemplos sintéticos. Resultado sob o grader corrigido (ver `G-120`): **0 % → 0 %**, nenhum ganho medido. Caso **fraco/confundido**, não uma calibração limpa: modelo (360 M) e dataset (80 exemplos, 1 época) foram reduzidos por limite de hardware (3B não coube em RAM via LoRA), não por escolha metodológica — um null result aqui não distingue "capacidade pouco tratável" de "tentativa pequena demais para ensinar". O prior declarado (`tractability: 0.90`) não foi alterado: um caso confundido não é motivo para reponderar o instrumento. Faltam 2 casos, e um caso não-confundido (modelo/dataset adequados) antes de qualquer leitura sobre a capacidade em si. **Tentativa de casos 2/3 abortada em 2026-08-20** antes de qualquer passo útil (1/80 completo): LoRA em `smollm2-360m-instruct` custa ~800–900s/passo nesta máquina — ~18–20h pra 80 exemplos, ~46h pra 200. Custo real não cabe no tempo disponível agora. Nenhuma evidência produzida por essa tentativa; caminho de LoRA local fica marcado como caro demais para iteração rápida até que o custo por passo mude (modelo menor, dataset mais barato por exemplo, ou hardware diferente) |
| G-105 | O limiar de discriminação de 0,20 do `F3` não tem base empírica | Replicação contra benchmarks públicos de agente com desfecho conhecido | veredicto de `F3`; portão V3 | OPEN |
| G-106 | Dificuldade das tarefas é declarada por autoria, não calibrada por desempenho | Curva de acerto por dificuldade com ao menos três modelos reais | qualquer leitura de "tarefa difícil" | OPEN |
| G-107 | O corpus é sintético: nenhuma tarefa veio de tráfego real de agente em produção | Traços de workload de cliente, anonimizados | validade externa do benchmark inteiro | OPEN |
| G-108 | Fichas do corpus de modelos foram transcritas de documento secundário, não da fonte | `matlas registry verify` contra o Hub, com revisão fixada | `A-101`; todo número derivado de contagem de parâmetros | **FECHADA** em 2026-08-15 — 3/3 conferidas com hash e data; duas divergências corrigidas ([COR-101, COR-102](../00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)) |
| G-109 | O alvo do subconjunto ótimo das tarefas de numeracia é calculado pelo mesmo autor do grader | Verificação independente do ótimo declarado em amostra | tarefas `BRAB-NUM-*` | OPEN |
| G-110 | Sem revisão adversarial externa (§6.7): autor e auditor são o mesmo agente | Revisão por pessoa que não construiu o artefato | Portão V3 | OPEN |
| G-111 | O conjunto-alvo de cada sonda é definido pelos modos declarados da tarefa, mais grosso que o que a sonda de fato ataca | Rotular por passo deformado, não por modo declarado | leitura de `probe_sensitivity`; diagnóstico de `CE-101` | OPEN |
| G-112 | O escore depende do prompt tanto quanto do modelo, e o prompt (`agent-ptbr-v2`) é zero-shot, sem exemplo demonstrado, e nunca foi ablacionado | Mesma suíte com few-shot e com ao menos três variantes de prompt, comparadas | qualquer leitura de "o modelo não sabe fazer X" | OPEN |
| G-113 | Só a quantização Q4_K_M foi executada: parte do escore pode ser perda de quantização, não limite do modelo | Mesma suíte em fp16 e em Q8, mesmo prompt | atribuição do escore ao modelo; alimenta `G-103` | OPEN |
| G-114 | O template de chat publicado no GGUF do `tucano-2b4-instruct` está **errado** e produz saída degenerada; o formato correto foi descoberto por experimento nesta máquina | Confirmação junto aos autores, ou comparação com o checkpoint `safetensors` original | validade externa de qualquer escore deste modelo | OPEN |
| G-115 | Dois modelos de porte quase igual (2,44 B e 3,08 B) diferem em 78 chamadas de ferramenta contra zero, e **não se sabe por quê**. Porte não explica | Ablação da variável candidata: corpus de instrução, presença de dados de tool-call no treino, quantização (`G-113`) | qualquer previsão sobre um modelo ainda não executado; aberta por `R-102` | OPEN |
| G-117 | O escore de um modelo de raciocínio híbrido depende do modo tanto quanto do prompt (+14,6 pontos medidos nas 96 tarefas completas), e **nenhum modelo do corpus foi comparado sob orçamento de tempo igual** — `/think` custa bem mais por tarefa | Comparação com custo controlado: mesmo tempo de CPU por tarefa para todos os modelos | comparabilidade entre modelos com e sem raciocínio; leitura de qualquer ranking | OPEN |
| G-116 | O `smollm3-3b` foi medido em `/no_think`; o modo padrão dele é `/think`, e o padrão não foi medido por completo | Mesma suíte em `/think`, com teto de tokens suficiente, até as 96 tarefas | leitura do escore do `smollm3-3b` como capacidade do modelo | **FECHADA** — 96/96 tarefas em `/think`, zero erro de infraestrutura, pareadas contra o publicado: **10,4 % → 25,0 %**, delta **+14,6 pontos**. Efeito **não uniforme** por capacidade: `tool_selection` 0 %→75,0 % e `hallucination` 0 %→83,3 % melhoram muito; `arguments` 50 %→41,7 % e `error_recovery` 33,3 %→0 % **pioram**. Chamadas de ferramenta **caem** com raciocínio (78→66), não ficam iguais — ver correção em `R-103` |
| G-118 | A execução de `/think` foi interrompida pelo Smart App Control do Windows bloqueando `llama-server.exe` (`VerifiedAndReputablePolicyState: 1`), depois de ~36h rodando sem problema — sem aviso prévio, sem entrada no histórico de ameaças do Defender | Decisão do usuário sobre a política (desligar Smart App Control é irreversível sem reinstalar o Windows), ou build assinada do `llama-server` que a política aceite | fechar `G-116`; qualquer execução futura de `/think` ou de novos modelos nesta máquina | **FECHADA** — usuário desativou a política (`VerifiedAndReputablePolicyState: 0`) por decisão própria; confirmado com `llama-server.exe --help` executando normalmente antes de relançar |
| G-120 | O grader de `structured_output` (`answer_json`) só verificava presença de chave na resposta final, nunca se o valor batia com a observação real, e `must_call` só verificava o nome da ferramenta, nunca se a chamada teve sucesso. Um adaptador LoRA aprendeu a explorar exatamente essa lacuna: chamou a ferramenta com o argumento errado (garantindo falha) e respondeu um JSON fixo plausível para as 12 tarefas — 100% de acerto sem nunca ler uma observação real | Regra nova (`answer_grounded`) mais `arg_equals`, e contraexemplo reproduzindo o exploit exato | qualquer escore de `structured_output` medido antes desta correção; a primeira tentativa de calibração do CSS (`G-104`) | **FECHADA** — `answer_grounded` e `arg_equals` adicionados às 12 tarefas, contraexemplo do exploit exato adicionado e rejeitado corretamente |

## Dívida de evidência (§6.3)

| Decisão | Evidência atual | Risco | Evidência pendente | Data limite |
|---|---|---|---|---|
| Corpus sintético gerado por template | A-103 | **Alto**: mede o gerador, não o mundo | G-107 | ciclo C-003 |
| Priors de capacidade fixos | A-104 | **Alto**: entram direto no alvo de dataset | G-104 | ciclo C-003 |
| ~~Contagem de parâmetros aproximada~~ | ~~A-101~~ | — | **quitada** em 2026-08-15 | — |
| Bytes por parâmetro por quantização | A-102 | Médio: desloca o "cabe?" | G-102 | ciclo C-003 |
| Limiar de discriminação de 0,20 | A-105 | **Alto**: decide o veredicto de F3 | G-105 | ciclo C-003 |
