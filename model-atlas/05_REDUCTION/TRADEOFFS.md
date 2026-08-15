---
artifact: TRADEOFFS
cycle: C-002
---

# Trade-offs

Cada linha é uma escolha que fecha uma porta. Registradas para que a porta fechada seja visível
quando alguém quiser abri-la.

| Escolha | Ganha | Perde | Reabrir quando |
|---|---|---|---|
| Corpus sintético gerado por template | escala, determinismo, zero custo de aquisição, nenhum problema de privacidade | validade externa: mede o gerador até prova em contrário (`G-107`) | houver traços reais de agente, mesmo poucos |
| Grader declarativo | uma regra auditável por tarefa; 17 regras cobrem 96 tarefas | expressividade: uma tarefa cujo acerto exige julgamento não é representável | aparecer capacidade que nenhuma combinação declarativa expresse |
| Ambiente com seis tipos de ferramenta | o interpretador cabe na cabeça e é verificável | tarefas com efeito dependente de tempo, concorrência ou estado externo ficam de fora | uma família de tarefa relevante exigir |
| Sondas sintéticas em vez de modelos | verificação do instrumento sem GPU, sem rede, em segundos | cobre só os modos que o autor imaginou (`A-106`) | primeira execução real |
| Rótulo múltiplo por trajetória | preserva a informação de que uma falha teve duas causas | a soma das taxas do Failure Atlas passa de 100 %, o que confunde na primeira leitura | — |
| Escore como fração de tarefas aprovadas | simples, auditável, sem parâmetro escondido | não pondera dificuldade nem valor; e o agregado foi retratado (`R-101`) | `G-104` e `G-106` fecharem |
| CSS com cinco fatores | força a explicitar o que entra na escolha de alvo | quatro dos cinco fatores são priors não calibrados (`G-104`) | três casos com desfecho conhecido |
| Footprint só de pesos | responde "cabe?" sem baixar nada | não responde "roda em velocidade útil?" | telemetria real (`G-102`) |
| Um projeto por eixo, core compartilhado | correção no contrato vale para os dois; nenhum eixo depende do outro | uma camada de indireção a mais para quem lê pela primeira vez | os dois eixos precisarem de semânticas diferentes para status |

## O trade-off que define o produto

Um relatório que conclui *"ainda não dá para saber, e aqui está exatamente o que falta"* é mais
difícil de vender que um com números. É também a única versão que continua valendo quando o
cliente confere.

O Silicon Atlas chegou nessa mesma bifurcação por outro caminho — recusando dimensionar um
acelerador que não existe — e a resposta foi a mesma. É a segunda vez, em dois eixos
independentes, que a recusa em produzir número é o produto.
