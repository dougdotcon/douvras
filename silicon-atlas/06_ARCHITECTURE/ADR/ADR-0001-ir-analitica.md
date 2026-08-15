# ADR-0001 — DOUVRAS IR derivada de configuração, não de traçado

Status: ACEITA · Data: 2026-08-03 · Ciclo: C-001

## Contexto

O Método exige que o portão A5 produza um protótipo que **outra pessoa consiga reproduzir**
(§4.6). A restrição R1 da carta do problema diz que o caminho principal do MVP não pode exigir
GPU, pesos baixados nem `torch`. Um traçado real (`torch.export`/ONNX) exige checkpoint completo
(16 GB para um modelo 8B), licença aceita e ambiente CUDA.

## Alternativas

1. **Traçar o modelo real** (`torch.export`, ONNX export). Fidelidade máxima, custo de entrada máximo.
2. **Derivar o grafo analiticamente do `config.json`** com um construtor por família arquitetural.
3. Ler apenas metadados de `safetensors` (nomes e shapes de tensores) sem topologia.

## Decisão adotada

Alternativa **2** para o caminho principal, com a **1** definida como interface de importação
(`ir.importers`) e registrada como `GAP_REGISTER:G-001`.

A IR é declarada `MODEL` — representação formal — nunca `OBSERVATION`.

## Razões

- Roda em qualquer máquina, sem pesos: o assessment comercial (§17.1) pode ser feito sobre um
  `config.json` público antes de qualquer NDA.
- É **falsificável de forma barata**: a contagem de parâmetros derivada do grafo tem valor
  publicado para comparar (teste E-001). Um traçado não oferece esse contraste tão diretamente.
- Preserva a unidade de análise correta: padrões de subgrafo, não tensores nomeados.

## Consequências positivas

- Corpus inteiro processável em segundos; diff entre versões é trivial.
- Zero risco de vazamento de pesos de cliente (§13.6).

## Consequências negativas

- Não captura fusões, kernels reais, nem operadores fora do template da família.
- Um modelo com arquitetura não coberta pelo construtor falha explicitamente (é preferível a
  produzir um grafo silenciosamente errado) — `UnsupportedArchitecture`.
- Todo resultado a jusante herda `A-001` e fica limitado a `CONDITIONAL_RESULT`.

## Evidência necessária para revisar esta decisão

Traçar um modelo por família e medir a diferença de FLOPs/bytes por classe de operador entre
IR analítica e grafo traçado. Se a divergência exceder 10 % em qualquer classe com participação
> 5 % do custo, a alternativa 1 passa a ser obrigatória para essa família.
