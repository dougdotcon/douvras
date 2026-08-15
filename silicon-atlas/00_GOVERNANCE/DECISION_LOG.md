---
artifact: DECISION_LOG
policy: append-only
---

# Registro de decisões

Decisões de projeto e de governança, em ordem cronológica. Decisões arquiteturais detalhadas
ficam em [ADRs](../06_ARCHITECTURE/ADR/); aqui fica o que não cabe num ADR.

| # | Data | Decisão | Justificativa | Reversível por |
|---|---|---|---|---|
| D-001 | 2026-08-03 | O primeiro produto é o assessment, não o chip | Reduz risco de quem fabrica antes de assumir risco próprio (Método §19) | evidência de que ninguém paga por análise sem hardware |
| D-002 | 2026-08-03 | IR derivada de configuração, não de traçado | Roda sem pesos nem GPU; permite assessment antes de NDA | divergência > 10 % contra grafo traçado (`G-001`) |
| D-003 | 2026-08-03 | Status epistêmico como tipo obrigatório | Torna o Método §3.1 verificável por máquina, não por disciplina | queda de velocidade de pesquisa a ponto de motores serem escritos fora do framework |
| D-004 | 2026-08-03 | Unidade de análise é o padrão de subgrafo | Silício replica estruturas, não camadas nomeadas | colisão de `pattern_hash` entre arquiteturas semanticamente distintas |
| D-005 | 2026-08-03 | Economia emitida como distribuição | Um break-even é uma divisão por diferença incerta; ponto único mente | cotações reais que estreitem as faixas (`G-005`, `G-007`) |
| D-006 | 2026-08-03 | Corpus transcrito, com verificação upstream opcional | Permite executar offline; a checagem de contagem de parâmetros já detecta erro de transcrição | — (fechar `G-008` é melhoria, não reversão) |
| D-007 | 2026-08-04 | Três níveis de identidade estrutural, não dois | A implementação mostrou que "mesmo datapath", "mesma proporção" e "mesmo circuito" são perguntas distintas com respostas distintas | emenda ao ADR-0003 |
| D-008 | 2026-08-04 | Manter C-006 retratada em vez de reponderar o LHS | Reponderar até o ranking estabilizar seria ajustar o instrumento ao resultado (Método §4.4) | calibração contra três casos com desfecho conhecido (`G-011`) |
| D-009 | 2026-08-04 | Falsificador F1 avaliado dentro da família, não no corpus inteiro | A carta do problema diz "entre versões"; cobertura cross-família é pergunta de mercado, não de estabilidade | — |
| D-010 | 2026-08-04 | `Finding` com valor nulo não rebaixa o conjunto | Declarar honestamente o que não foi medido não pode ser punido como se fosse resultado fraco | — |

## Decisões deliberadamente adiadas

| Adiada | Por quê | Reabrir quando |
|---|---|---|
| Emissão de HLS/RTL | Sem candidato aprovado, não há o que gerar | região fixa deixar de ser vazia em algum caso |
| Backend MLIR/CIRCT | Custo alto de infraestrutura antes de haver bloco definido | primeiro bloco aprovado para protótipo FPGA |
| API HTTP e multi-tenant | O produto de entrada é um relatório, entregue como arquivo | segundo cliente pagante |
| Suporte a atenção linear e SSM | Fora do corpus atual; construtor falharia alto, como projetado | modelo relevante da família entrar no corpus |
