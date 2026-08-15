---
artifact: EXTERNAL_REVIEWS_INDEX
status: VAZIO — lacuna G-110 aberta
---

# Revisões externas — Model Atlas

**Este diretório está vazio, e isso é o achado.**

O Método §6.7 estabelece que uma pessoa não aprova sozinha a própria afirmação. Neste ciclo,
quem escreveu as tarefas, quem escreveu os graders e quem escreveu as sondas que testam os
graders são o mesmo agente. Por isso:

- `G-110` está aberta no [GAP_REGISTER](../../02_OBSERVATION/GAP_REGISTER.md);
- o portão **V3 está bloqueado** — `matlas gates` reporta isso a cada execução;
- nenhum documento deste projeto pode alegar ter sobrevivido a revisão independente.

Um arquivo dizendo "revisado internamente, tudo certo" seria pior que a pasta vazia.

## O conflito específico deste eixo

No Silicon Atlas o problema era o de sempre: autor e auditor coincidem. Aqui ele é mais agudo,
e vale nomear o mecanismo.

O ciclo mede o instrumento com **sondas escritas por quem escreveu o instrumento**. Uma sonda
testa se o grader detecta a falha *na forma em que a sonda a produz* (`A-106`). Nada garante
que um modelo real erre dessa forma. É perfeitamente possível ter 100 % de aceitação de
gabarito, 100 % de rejeição de contraexemplo, 100 % de precisão de rótulo — e um grader que
deixa passar o modo como o Qwen realmente quebra, porque ninguém que escreveu o corpus tinha
visto o Qwen quebrar.

**Sondas não substituem revisão externa. Elas cobrem o espaço que o autor imaginou.**

## O que uma revisão externa útil precisa atacar

Em ordem de valor. Um revisor que confirmasse tudo teria produzido pouco; o pedido é que tente
derrubar.

1. **O gabarito está certo?** Pegue dez tarefas e verifique à mão que a trajetória de referência
   é de fato a resposta correta ao enunciado — em especial as `BRAB-NUM-*`, cujo subconjunto
   ótimo foi calculado por quem escreveu o grader (`G-109`).
2. **A regra mede a capacidade que nomeia?** `arguments` reprova por argumento errado ou por
   outra coisa correlacionada? Escreva uma trajetória que erra o argumento e acerta tudo mais.
3. **Falta um modo de falha?** A taxonomia tem oito entradas. Um agente real erra de alguma
   forma que nenhuma delas nomeia?
4. **O limiar de 0,20 do `F3` faz sentido?** Ele decidiu a retratação de `C-102`. É defensável
   ou foi importado sem justificativa do `LHS` do Silicon Atlas (`G-105`)?
5. **O corpus sintético mede o mundo?** Todas as tarefas saem de oito templates paramétricos.
   O escore no corpus prediz alguma coisa fora dele (`A-103`, `G-107`)?
6. **A recusa do `ADR-0007` é forte o bastante?** Existe algum caminho pelo qual um número
   sintético chega ao relatório como se fosse medição?

O item 5 é o mais desconfortável e por isso o mais importante.

## Como registrar uma revisão

Crie `ER-1NN-<sobrenome>.md`. Revisões que **confirmam** também são registradas — a ausência de
achado só tem valor se a busca foi documentada.

```markdown
---
artifact: EXTERNAL_REVIEW
id: ER-101
reviewer: <nome>
affiliation: <instituicao ou empresa>
conflict_of_interest: <declarar qualquer interesse no resultado, ou "nenhum">
date: AAAA-MM-DD
scope: <o que foi revisado e o que nao foi>
---

## O que tentei derrubar
## Como tentei
## O que sobreviveu
## O que não sobreviveu
## O que não consegui avaliar, e por quê
## Recomendação de status para as alegações afetadas
```

Ao receber uma revisão: registre-a aqui, atualize o `CLAIM_LEDGER`, registre a decisão no
`DECISION_LOG` e reexecute o ciclo. Promoção de status é decisão humana, nunca automática.
