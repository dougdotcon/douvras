---
artifact: MINIMAL_STRUCTURE
cycle: C-001
gate: R4
date: 2026-08-04
---

# Unidade Mínima Invariante — UMI

## A pergunta da fase R

Não "qual é o sistema completo que queremos construir", e sim **qual é a menor estrutura que
preserva o valor observado**. Tudo que sobrar depois dela é conveniência.

## Duas UMIs, não uma

O ciclo encontrou duas unidades mínimas distintas, porque o Silicon Atlas tem duas naturezas:
é um instrumento de medida e é um instrumento de decisão. Elas se reduzem de formas diferentes.

---

## UMI-1 — A unidade de medida: `(padrão, workload, fase) → participação de custo`

### Função preservada

Dizer, com aritmética verificável, **onde o custo de inferência realmente está**, separando
computação de movimentação de memória e prefill de decode.

### Componentes obrigatórios

| Componente | Por quê |
|---|---|
| `registry.ModelSpec` | normaliza arquiteturas divergentes num vocabulário único |
| `ir.build_graph` | expande o modelo em operadores com FLOPs e bytes declarados |
| `ir.Workload` | sem condições declaradas não existe "custo", só número |
| `profiler.roofline` | separa o regime compute-bound do memory-bound |
| `profiler.ServingProfile` | mistura prefill e decode na proporção real de uma requisição |

### Componentes removidos e ainda assim o valor sobrevive

- Fingerprint, invariantes, quantização, LHS/SRS, partição, economia, relatório.
- Pesos do modelo, GPU, `torch`, rede.

Um cliente que só rodasse UMI-1 já receberia a resposta que mais muda decisão de engenharia:
*"98 % do tempo da sua requisição é decode, e 99,9 % do decode é espera de memória — sua próxima
otimização não é aritmética."*

### Aproximações aceitas

- Nós executam em sequência, sem sobreposição entre computação e memória (`A-002`).
- Atenção com *tiling*: scores não vão para a memória principal.
- Eficiências de pico por faixa, não medidas (`A-005`).

### Limites de validade

Vale para decoder-only denso ou MoE, com atenção quadrática ou janela deslizante, em um único
dispositivo. **Não** vale para: paralelismo entre dispositivos, atenção linear/SSM, batching
contínuo com preempção, nem especulação.

### Interfaces

```text
entrada: config.json (estilo Hugging Face) + Workload + Device
saída:   por nó → {flops, bytes, tempo de computação, tempo de memória, intensidade}
```

### Métricas antes e depois da redução

| | Antes (Atlas completo) | Depois (UMI-1) |
|---|---|---|
| módulos necessários | 11 | 4 |
| entradas externas | corpus, 3 arquivos de priors, device | config + device |
| premissas carregadas | A-001 … A-009 | A-001, A-002, A-005 |
| status máximo alcançável | `CONDITIONAL_RESULT` | `COMPUTATIONAL_EVIDENCE` |

A redução **sobe** o status máximo: menos premissas, conclusão mais forte. Esse é o argumento
central da fase R e o motivo de a UMI-1 ser o produto a vender primeiro.

---

## UMI-2 — A unidade de decisão: `(fração endurecível, teto de Amdahl)`

### Função preservada

Impedir que uma expectativa de ganho seja adotada sem confronto aritmético.

### Componentes obrigatórios

`UMI-1` · `partition.Partition.hardened_share` · `partition.amdahl_ceiling`

### Por que é mínima

Duas linhas de aritmética sobre a saída da UMI-1:

```text
teto              = 1 / (1 − f)
aceleração exigida = f / (1/alvo − (1 − f))
```

Não exigem custo de máscara, densidade de área, rendimento, priors de quantização nem taxa de
obsolescência — ou seja, não dependem de nenhuma das lacunas caras (`G-004`, `G-005`, `G-007`).
E ainda assim respondem à pergunta que originou o projeto: *um ganho de 100× é alcançável nesta
arquitetura?*

Para os 9 modelos do corpus, com a política de partição vigente, a resposta é não — e a
justificativa cabe numa linha, sem citar nenhum número de fabricante.

### Limites de validade

O teto vale para arquitetura **híbrida**, onde a região não endurecida permanece no host. Um chip
que absorva o caminho inteiro não está sujeito a ele — mas passa a estar sujeito ao risco de
obsolescência integral, que a UMI-2 não modela. Ali começa o território caro, e é por isso que
ele fica **fora** da unidade mínima.

---

## O que a redução revelou

O componente mais elaborado do sistema — o Silicon Readiness Score, com sete fatores e pesos
calibráveis — **não** entrou em nenhuma das duas UMIs. E o ciclo mostrou por quê: ele não
discrimina candidatos dentro de um modelo
([CE-001](../04_VALIDATION/COUNTEREXAMPLES/CE-001-lhs-nao-discrimina.md)).

A parte que mais parecia produto era a que menos preservava valor. A fase R existe para descobrir
isso antes de a fase A construir em cima.

## Portão R4 — verificação

- [x] existe núcleo testável (`tests/test_profiler_economics.py`);
- [x] interfaces definidas (entrada `config.json` + `Workload` + `Device`);
- [x] custo marginal de complexidade adicional conhecido (cada camada acrescenta premissas e
      **rebaixa** o status máximo do resultado);
- [x] ficou claro o que é fixo, configurável e programável — e que, com a estabilidade
      atualmente observada, a região fixa é vazia.
