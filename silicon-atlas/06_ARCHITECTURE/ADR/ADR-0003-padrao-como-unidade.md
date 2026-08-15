# ADR-0003 — A unidade de análise é o padrão de subgrafo, não a camada

Status: ACEITA · Data: 2026-08-03 · Ciclo: C-001

## Contexto

"Qual camada endurecer?" é a pergunta errada. Silício não replica camadas nomeadas; replica
estruturas. Um chip que instancia uma unidade de projeção linear a usa milhares de vezes por token,
atravessando todas as camadas — e, se o padrão for compartilhado, atravessando famílias inteiras
de modelos.

## Alternativas

1. Camada como unidade (`layers.17.mlp.down_proj`).
2. Classe de operador como unidade (`todo linear`).
3. **Padrão de subgrafo**: classe de equivalência sob renomeação, índice de camada e batch,
   com dois níveis de hash.

## Decisão adotada

Alternativa **3**, com dois níveis:

- `pattern_hash` — invariante a tamanho (usa razões: `I/d`, `h/g`, `head_dim`). Responde
  "esta estrutura existe em outra família/tamanho?"
- `exact_hash` — sensível a shape. Responde "posso reusar o **mesmo** circuito, sem re-síntese?"

Estabilidade estrutural (E) usa `pattern_hash`; reuso de silício exige `exact_hash`.

## Razões

- Separa duas perguntas que a literatura promocional confunde: *arquitetura estável* (barata de
  satisfazer) e *shape estável* (cara, e o que realmente permite reuso de máscara).
- Faz o detector de invariantes (§12.4) devolver algo acionável: cobertura por padrão, não
  similaridade global entre modelos.
- Permite que um contraexemplo seja preciso: "o padrão P sobrevive em pattern, quebra em exact
  entre 8B e 70B" é um achado, não um ruído.

## Consequências positivas

- Corpus cross-família comparável mesmo com tamanhos distintos.
- O particionador recebe padrões, e cada partição já vem com a contagem de instâncias por token.

## Consequências negativas

- Dois hashes por subgrafo dobram a superfície de teste (invariância **e** sensibilidade).
- Padrões raros e caros (ex.: `lm_head` com vocabulário grande) aparecem com contagem 1 e podem
  ser subestimados por métricas de repetição — mitigado ponderando por custo, não por contagem.

## Evidência necessária para revisar

Se `pattern_hash` colidir entre arquiteturas semanticamente distintas (falso positivo de
estabilidade), a normalização de razões é grosseira demais e precisa incluir atributos ignorados.
Os testes de sensibilidade em `tests/test_fingerprint_invariants.py` cobrem isso.

---

## Emenda — 2026-08-04 (decisão D-007)

A implementação mostrou que **dois níveis são insuficientes**. Ao comparar Qwen2.5-7B com
Qwen2.5-14B, o `pattern_hash` **não** casa: a razão `I/d` muda de 5,29 para 2,70 entre os dois
tamanhos da mesma família, lançados no mesmo dia. O ADR original previa que o `pattern_hash`
respondesse "esta estrutura existe em outra escala?", mas ele responde "existe na mesma
proporção?" — que é outra pergunta.

Adotado um terceiro nível, mais grosseiro que os dois:

| Nível | O que iguala | Pergunta de hardware |
|---|---|---|
| `topology` | operadores, papéis e conectividade | mesmo *datapath* |
| `pattern` | topologia + proporções de shape | mesma microarquitetura, outra escala |
| `exact` | shapes absolutos + precisão | mesmo circuito, sem re-síntese |

A cobertura cai monotonicamente de `topology` para `exact`, e essa queda **é** a medida do risco
que um projeto de silício assume. Um roadmap que cita estabilidade de topologia para justificar
máscara está usando a evidência do nível errado — que era exatamente o erro que este ADR
pretendia impedir, e que a versão de dois níveis ainda deixava passar.

Consequência prática registrada no ciclo C-001: o bloco MLP de `llama-3-8b` e o de
`mistral-7b-v0.1` são idênticos no nível **exato** (ambos d=4096, I=14336), apesar de famílias e
laboratórios distintos. Um mesmo circuito serve os dois. Já `qwen2.5-7b` e `qwen2.5-14b`
compartilham `topology` e divergem em `pattern` e `exact`.
