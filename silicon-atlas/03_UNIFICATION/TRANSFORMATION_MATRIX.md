---
artifact: TRANSFORMATION_MATRIX
run_id: 20260815T000030Z
generated_by: scripts/run_cycle.py
status: COMPUTATIONAL_EVIDENCE
---

# Matriz de transformacoes

> Arquivo **gerado**. Cada linha e uma medicao, nao uma opiniao.

Um invariante nunca e invariante em abstrato: e invariante **em relacao a um conjunto
declarado de transformacoes** (Metodo 4.3). Esta matriz declara esse conjunto e mede o
resultado de cada uma sobre o corpus.

| Transformacao | O que muda | O que permanece | O que quebra | Leitura |
|---|---|---|---|---|
| mudar versao (llama-3-8b -> llama-3.1-8b, 96 dias) | contexto maximo 8k -> 128k; regime de memoria do KV cache | topologia, proporcoes e shapes exatos (2/2 blocos identicos) | nada | invariante sob esta transformacao |
| mudar geracao (llama-2-7b -> llama-3-8b) | MHA -> GQA (32 -> 8 cabecas KV), vocabulario 32k -> 128k, I 11008 -> 14336 | topologia do bloco (0/2 blocos exatos preservados) | todo circuito dimensionado para os shapes antigos | NAO invariante: re-sintese obrigatoria |
| mudar escala (qwen2.5-7B -> 14B, mesmo dia) | d 3584 -> 5120, L 28 -> 48, razao I/d 5.29 -> 2.70 | topologia (igual) | padrao de proporcoes (quebra) e shapes exatos (quebra) | invariante so no nivel de topologia |
| mudar familia (llama-3-8b -> mistral-7b-v0.1) | vocabulario 128k -> 32k, janela deslizante, rope_theta | MLP exato preservado (mesmo d e I) | atencao exata quebrada (janela deslizante entra no hash) | invariante parcial: um mesmo circuito de MLP serve as duas familias |
| substituir MLP denso por MoE (mistral-7b -> mixtral-8x7b) | footprint 6.4x, FLOPs por token 1.7x | bloco de atencao exato (identico entre os dois) | previsibilidade de memoria: roteamento por token torna o acesso dependente de dado | a regiao de MLP deixa de ser endurecivel; a de atencao permanece |
| mudar precisao (bf16 -> int4 nos pesos) | bytes de peso -75%, tempo de decode 0.28x | topologia, proporcoes e contagem de operacoes | hash exato (precisao entra na identidade do circuito) e qualidade nao medida (G-002) | muda o circuito, nao a arquitetura |
| mudar hardware (H100 -> A100 -> L40S) | throughput absoluto e ponto de inflexao do roofline | o regime: decode permanece limitado por memoria nos tres (h100-sxm: 172 tok/s, memory-bound 100%; a100-sxm-80: 104 tok/s, memory-bound 100%; l40s: 43 tok/s, memory-bound 100%) | nada estrutural | a conclusao qualitativa e invariante ao dispositivo |
| mudar fase (prefill -> decode) | intensidade aritmetica 625 -> 1.06 FLOP/byte; memory-bound 15% -> 100% | o grafo e os shapes (mesmo modelo) | toda conclusao de projeto derivada apenas de prefill | as duas fases pedem hardware diferente |
| mudar contexto (2k -> 32k em decode) | bytes de KV 16x; participacao do KV no trafego 1.8% -> 22.2% | pesos e topologia | o dimensionamento de SRAM de um acelerador projetado para contexto curto | contexto e parametro de projeto, nao detalhe de uso |
| mudar lote (batch 1 -> 64 em decode) | intensidade 1.10 -> 21.82 FLOP/byte; energia por token 6595 -> 342.7 mJ | o grafo e o footprint de pesos | a afirmacao de que decode e sempre limitado por memoria (97% em lote 64) | lote e alavanca economica antes de silicio ser alavanca |

## O que a matriz mostra

As transformacoes que **preservam** a estrutura sao as de versao dentro da mesma linha
arquitetural. As que **quebram** sao as de geracao, de escala e de precisao. Como as tres
ultimas acontecem com frequencia anual no mercado de modelos abertos, a janela em que um
circuito exato permanece util e curta — e essa e a variavel que domina o risco de
obsolescencia, mais que qualquer parametro de fabricacao.

Duas transformacoes nao estruturais merecem atencao especial porque mudam a **conclusao**
sem mudar o modelo: aumentar o lote e aumentar o contexto. A primeira desloca o decode em
direcao ao regime de computacao e enfraquece o argumento de hardening por memoria; a
segunda faz o KV cache disputar espaco com os pesos. Nenhum projeto de silicio deveria ser
avaliado sem declarar as duas.
