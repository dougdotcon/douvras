---
artifact: ADR
id: ADR-0006
date: 2026-08-14
status: adotada
---

# O caminho principal roda sem pesos, sem GPU e sem rede

## Contexto

O Model Atlas mede comportamento, e comportamento exige execução. A tentação óbvia é fazer o
download de pesos ser pré-requisito do ciclo. A máquina de referência do laboratório é uma CPU
com 16 GB de RAM.

## Alternativas

1. **Exigir pesos.** O ciclo só roda depois de baixar alguns GB; sem rede, nada acontece.
2. **Simular a resposta do modelo** com um gerador estatístico e reportar os números como se
   fossem medição.
3. **Separar o que precisa de execução do que não precisa**, e declarar ausência no resto.

## Decisão adotada

Alternativa 3. `pip install -e .` instala `numpy` e `pyyaml`; o ciclo inteiro roda com isso. A
execução real fica no extra `[run]` e fecha `G-101`, `G-102` e `G-103`.

## Razões

- É o mesmo raciocínio do [`ADR-0001`](../../../silicon-atlas/06_ARCHITECTURE/ADR/ADR-0001-ir-analitica.md)
  do Silicon Atlas, e pela mesma razão comercial: o assessment roda **antes** de qualquer NDA e
  antes de qualquer compra de hardware.
- A alternativa 2 é a que destrói o produto. Um número que parece medição e não é contamina
  tudo a jusante, e quem lê o relatório três arquivos depois não tem como saber.
- Há trabalho real a fazer sem pesos, e ele é o trabalho que quase ninguém faz: verificar o
  instrumento. Aceitação de gabarito, rejeição de contraexemplo, precisão de rótulo,
  determinismo e cobertura da taxonomia são todos mensuráveis offline.

## Consequências positivas

- O ciclo roda em segundos e é reexecutável por qualquer pessoa, o que é pré-requisito do
  portão A5.
- A separação entre "o que a aritmética sabe" e "o que só a medição sabe" fica explícita no
  tipo: o orçamento de memória sai como `ASSUMPTION`; TTFT e tokens/s saem como `OPEN_GAP`.

## Consequências negativas

- **Nenhuma capacidade de modelo é medida neste ciclo.** O assessment sai concluindo "não dá
  para saber ainda", e isso é desconfortável de mostrar a um cliente.
- O corpus de modelos existe sem que nenhum deles tenha sido executado — o registro é uma
  promessa de trabalho, não um resultado.

## Evidência necessária para revisar esta decisão

Primeira execução real bem-sucedida em CPU com um modelo de 0,5B a 0,8B quantizado. A partir
daí, o caminho principal pode passar a exigir execução para os modelos que já têm pesos locais,
mantendo o modo offline para os demais.
