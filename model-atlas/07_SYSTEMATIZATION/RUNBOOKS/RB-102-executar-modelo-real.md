---
artifact: RUNBOOK
id: RB-102
cycle: C-003
---

# RB-102 — executar um modelo real contra o BR-Agent-Bench

## Quando usar

Há pesos locais de um modelo e se quer capacidade **medida** em vez de ausência declarada.
Fecha `G-101` para aquele modelo, e `G-102` junto, pela telemetria da execução.

## Pré-requisitos

```text
.local/bin/llama-server.exe          release do llama.cpp (x64; independe do Python)
.local/models/<modelo>.gguf          pesos quantizados
```

Ambos ficam fora do versionamento (`.gitignore`). O `.local/` não é entrada nem saída do
método: é máquina.

## Passos

```bash
# 1. registrar a ficha e conferir na fonte
PYTHONPATH=src python -m model_atlas.cli registry verify <id> --write

# 2. prova de fumaça em 3 ou 4 tarefas ANTES da suíte inteira
python .local/smoke.py

# 3. suíte completa
python .local/run_bench.py --model-id <id>
```

O passo 2 não é opcional, e a razão está na seção seguinte.

## O passo que mais economiza tempo: verificar o formato antes do escore

Um harness com formato de conversa errado produz **zero** e o zero parece um resultado. Foi o
que aconteceu na primeira execução deste runbook, duas vezes seguidas, por causas diferentes.

**Sintoma.** Repetição degenerada: `"Qual e Qual e Qual e"`, `"FFQuala</</. A Pergunt"`.
Isso nunca é capacidade baixa — é formato errado. Um modelo fraco erra a tarefa; um modelo
mal formatado não produz linguagem.

**Diagnóstico, na ordem em que compensa fazer:**

1. **O tokenizer trata os marcadores como tokens especiais?**
   `POST /tokenize {"content": "<tag>", "with_pieces": true}` — se `<tag>` vira vários
   pedaços, a conversão do GGUF está defeituosa.
2. **Qual prompt o servidor está montando?**
   `POST /apply-template {"messages": [...]}` devolve a string exata. Compare com o que o
   modelo espera.
3. **O modelo responde a um prompt cru simples?**
   `POST /completion {"prompt": "Pergunta: ...\nResposta:"}` — se aqui sai texto coerente e
   pelo template sai lixo, o problema é o template, não o modelo.
4. **Onde exatamente quebra?** Varie um elemento por vez: tag aberta, tag fechada, com e sem
   BOS, com e sem nova linha.

**O que esse procedimento encontrou no `tucano-2b4-instruct`:** o template embutido no GGUF
fecha `</instruction>` dentro do prompt, mas o modelo foi treinado para **emitir** essa tag.

| Prompt | Saída |
|---|---|
| `<instruction>Qual e a capital da Franca?` | `</instruction>A capital da França é Paris…` |
| `<instruction>Qual e a capital da Franca?</instruction>` | `FFQuala</</. A PerguntQualfQual…` |

Consequência: **toda ferramenta que aplica o template publicado** — llama-server com
`--jinja`, `apply_chat_template` do transformers, Ollama, LM Studio — recebe saída degenerada
desse modelo. Registrado em `G-114`.

## O prompt é parte do instrumento

Trocar a ordem das seções mudou o comportamento por completo: com o contrato de resposta no
início e a lista de ferramentas no fim, o modelo **continuava a lista** em vez de agir. Movendo
o contrato para o fim, colado à geração, ele passou a emitir `{"acao": ...}`.

Por isso `PROMPT_VERSION` existe e entra no relatório. Duas regras:

- revisão de prompt por **defeito estrutural observado** é construção de instrumento, e vale
  registrar a versão e o motivo;
- revisão de prompt **olhando o escore até subir** é ajustar o instrumento ao resultado, e é o
  que o `D-106` proíbe.

A fronteira é: mexer antes de medir, e declarar o que mexeu.

## O que anotar depois da execução

| Campo | Onde |
|---|---|
| `PROMPT_VERSION` | no assessment, junto do escore |
| quantização usada | `G-113` — parte do escore pode ser perda de quantização |
| telemetria (TTFT, tok/s) | fecha `G-102` |
| `max_steps` | trajetória truncada conta como `FAIL_PLANNING` |

## O que **não** fazer

- Não repita a chamada até sair JSON válido. Isso mede a persistência do harness.
- Não conserte o JSON do modelo antes de graduar. Isso mede o harness.
- Não compare escores de `PROMPT_VERSION` diferentes. São instrumentos diferentes.
- Não atribua ao modelo um escore colhido com formato de conversa não verificado.
