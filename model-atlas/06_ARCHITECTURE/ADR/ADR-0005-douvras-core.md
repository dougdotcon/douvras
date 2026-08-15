---
artifact: ADR
id: ADR-0005
date: 2026-08-14
status: adotada
---

# Extrair o contrato epistêmico para `douvras_core`

## Contexto

O Silicon Atlas nasceu com `silicon_atlas/status.py`: escala de status, propagação pelo elo mais
fraco, `StatusViolation`, lint de vocabulário, claim ledger. Cerca de 500 linhas que não têm
nada de hardware — descrevem como uma afirmação se relaciona com a evidência que a sustenta.

Com um segundo eixo de pesquisa (Model Atlas), havia três caminhos.

## Alternativas

1. **Reimplementar** o contrato no projeto novo. Duas cópias divergem: a primeira correção de
   `derive()` que entrasse em uma e não na outra criaria dois métodos com o mesmo nome.
2. **Importar `silicon_atlas` do Model Atlas.** Faria o eixo de capacidade depender do eixo de
   silício para existir, o que é falso e viraria acoplamento permanente.
3. **Extrair para um core compartilhado.**

## Decisão adotada

Alternativa 3. `douvras_core` passa a conter `status`, `paths`, `gates` e `report`. Nenhum dos
dois atlas define escala de status, portão ou exceção de emissão.

## Razões

- A extração é o **teste** da afirmação central do Método. Se a escala de status só servisse
  para hardware, ela seria vocabulário de domínio disfarçado de epistemologia. Ela migrou sem
  uma linha de adaptação, e o Model Atlas usa `Status`, `Finding` e `derive` exatamente como
  estão.
- Um `Finding` de capacidade medida e um `Finding` de custo analítico passam a se combinar pela
  mesma regra do elo mais fraco. Isso é pré-requisito do codesign que o Documento 2 descreve:
  a interseção entre invariante comportamental e invariante arquitetural.
- `EmissionRefused` compartilhada significa que quem consome um relatório DOUVRAS captura uma
  exceção, não uma por atlas.

## Consequências positivas

- Correção no contrato vale para os dois eixos na mesma linha.
- `tests/core/` valida o contrato sem importar nenhum dos dois atlas — se algum teste do core
  precisasse de um `ModelSpec` ou de um `Device`, a extração estaria errada.
- Um terceiro atlas herda a disciplina inteira e escreve só a física do próprio problema.

## Consequências negativas

- Uma camada a mais de indireção para quem lê `silicon_atlas` pela primeira vez.
- `project_root()` substituiu `parents[2]`: caminhos agora dependem de um registro explícito de
  projetos, e um nome fora dele levanta `UnknownProject` em vez de devolver caminho morto.
- Mudança no core exige rodar as duas suítes.

## Evidência necessária para revisar esta decisão

Um caso em que os dois atlas precisem de semânticas **diferentes** para o mesmo conceito de
status. Se aparecer, o core está grande demais e o conceito em disputa deve voltar para os
projetos.

## Verificação aplicada

A migração foi conferida por regeneração: os 24 artefatos do ciclo C-001 foram reemitidos após
a extração e comparados com a versão anterior, ignorando `run_id` e timestamp. **Zero diferença
de conteúdo**, e os 149 testes seguem verdes.
