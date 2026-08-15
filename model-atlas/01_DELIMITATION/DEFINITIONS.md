---
artifact: DEFINITIONS
cycle: C-002
date: 2026-08-14
---

# Definições

Palavras que este projeto usa com sentido estreito. Onde o sentido comum é mais largo, a
diferença está marcada — porque é nela que a conclusão escorrega.

| Termo | Definição neste projeto | O que **não** é |
|---|---|---|
| **capacidade** | classe de comportamento que falha de forma distinguível das demais, com tarefas e regra de acerto próprias | não é uma habilidade cognitiva; é um agrupamento de modos de falha |
| **trajetória** | sequência de passos propostos pelo respondente, com as observações preenchidas pelo **ambiente** | não é um log escrito pelo modelo |
| **ambiente** | interpretador determinístico das ferramentas declaradas na tarefa | não é um mock que devolve o que a tarefa espera |
| **grader** | função total que aplica a regra declarada e devolve rótulos de falha | não é um juiz-LLM nem uma métrica de similaridade |
| **modo de falha** | rótulo da taxonomia disparado por uma regra específica | não é uma causa; é uma observação |
| **sonda de calibração** | respondente sintético que encarna um modo de falha arquetípico | **não é um modelo**, e nenhum número derivado dela fala de modelo (`ADR-0007`) |
| **oráculo** | sonda que reproduz a trajetória de referência | não é um modelo perfeito; é o teto do instrumento |
| **escore** | fração de tarefas aprovadas em um recorte declarado | não é qualidade; um escore agregado foi retratado neste ciclo (`R-101`) |
| **capability fingerprint** | vetor de capacidades **medidas** de um modelo | não existe sem execução real; ausência é declarada, não zerada |
| **CSS** | pontuação de quão boa candidata a especialização por dados é uma capacidade | não é previsão de ganho; depende de priors não calibrados (`G-104`) |
| **precision cliff** | ponto em que a redução de precisão degrada capacidade de forma abrupta | não foi medido neste ciclo (`G-103`) |
| **footprint** | bytes dos pesos residentes na quantização declarada | não inclui KV cache nem ativações; caber não é rodar |
| **contraexemplo** | trajetória sabidamente errada, rotulada com o modo que exibe | não é um caso de teste do código; é um caso de teste do **critério** |
| **medido** | produzido por execução com pesos reais e protocolo declarado | execução sintética não é medição |

## Sobre "benchmark"

Neste projeto, um benchmark é **corpus + regra + evidência de que a regra funciona**. Um corpus
com regra e sem evidência da regra é um conjunto de opiniões formatadas em JSON.

## Sobre "avaliar um modelo"

Significa: executar o modelo contra o corpus, coletar trajetórias reais e aplicar o grader. Não
significa perguntar a um modelo maior se a resposta parece boa, nem comparar com uma resposta
de referência por similaridade de texto. As duas coisas podem ser úteis; não são isto.
