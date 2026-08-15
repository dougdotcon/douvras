---
artifact: COMPETING_MODELS
cycle: C-001
gate: U2
date: 2026-08-04
---

# Modelos concorrentes

O portão U2 exige que a estrutura candidata **produza uma previsão ou decisão distinguível**
(Método §4.3). Distinguível de quê? Das explicações rivais. Este documento as declara.

Cada modelo abaixo explica os mesmos dados. O que os separa é o que preveem sobre o **próximo**
dado — e é por isso que declará-los antes vale mais do que escolher o vencedor depois.

---

## M1 — Estratificação (a hipótese do projeto)

> O caminho dominante e estável deve ser endurecido; adaptação, controle e operadores emergentes
> permanecem programáveis.

**Prevê**: existe uma fração `f` estável e dominante, e o valor está em fixá-la.

**Estado em C-001**: a fração dominante existe (67 % do decode em três papéis de projeção), mas a
parte *estável* dela é vazia sob a estabilidade observada. O modelo prevê valor onde a medição
não encontra.

**Como seria refutado**: se `f` estável permanecer vazio após ampliar o corpus e estreitar o
escopo, M1 não é falso — é inaplicável ao mercado de modelos abertos em sua velocidade atual.

---

## M2 — Fixação total (a tese forte)

> Um modelo inteiro pode ser gravado em silício, e o ganho vem justamente de eliminar toda
> programabilidade.

**Prevê**: o ganho cresce super-linearmente com o grau de fixação; a arquitetura híbrida é um
meio-termo que perde para os dois extremos.

**Estado em C-001**: não avaliado diretamente — `simulate(hardened_only=False)` existe, mas o
ciclo não o executou como caso principal. É a lacuna de comparação mais relevante para C-005.

**Como seria distinguido de M1**: comparar valor esperado ajustado ao risco de
`hardened_only=True` contra `False`, no mesmo corpus. Se M2 vencer em todos os cenários, C-005
é refutada.

**Evidência externa a favor**: `E-002` (demonstrador com modelo 8B hardwired) e `E-003`. Ambas
com as ressalvas registradas no ledger.

---

## M3 — Memória, não computação

> O gargalo não é aritmética nem programabilidade: é mover pesos. Quem resolver a hierarquia de
> memória ganha, independentemente de fixar ou não o modelo.

**Prevê**: ganho proporcional à redução de bytes movidos, e quase indiferente à especialização
lógica. Um acelerador com pesos em ROM on-chip vence não por ser fixo, mas por ser **próximo**.

**Estado em C-001**: **é o modelo mais sustentado pelos dados**. Decode a ~1 FLOP/byte contra
inflexão de ~92; 99,9 % do tempo limitado por banda; a quantização para INT4 sozinha rende 3,6×
em decode sem tocar em silício.

**Consequência desconfortável para o projeto**: se M3 estiver certo, o produto mais valioso não é
o assessment de silício — é o assessment de hierarquia de memória. Registrado, não endereçado.

---

## M4 — Lote e escalonamento resolvem antes

> O problema econômico de inferência cede a batching, cache de prefixo e escalonamento, muito
> antes de justificar hardware novo.

**Prevê**: a vantagem de qualquer acelerador encolhe conforme o lote cresce, porque o regime
migra de memória para computação.

**Estado em C-001**: **medido e favorável a M4**. Ir de lote 1 para 64 leva a intensidade de 1,10
para 21,82 FLOP/byte e derruba a energia por token de 6595 para 343 mJ — 19× de ganho sem
silício. Ver [TRANSFORMATION_MATRIX](TRANSFORMATION_MATRIX.md).

**Como seria refutado**: se o lote grande for inviável por latência contratada (SLA de token
único) ou por memória de KV cache, o ganho de M4 não é realizável e a vantagem volta para M1/M3.
Essa é exatamente a condição que um cliente precisa declarar — e que `G-009` cobre.

---

## M5 — Convergência arquitetural

> Modelos abertos estão convergindo para um bloco comum; a estabilidade vai **aumentar** com o
> tempo, e a janela de obsolescência vai se alargar.

**Prevê**: a cobertura no nível exato deve subir a cada ciclo.

**Estado em C-001**: parcialmente sustentado. No nível de topologia a convergência é forte
(0,89 de cobertura, 8 de 9 modelos). No nível exato é fraca (0,33). M5 é verdadeiro na camada
que não decide máscara.

**Como seria testado**: medir a série temporal da cobertura exata ao longo de vários ciclos. Se
subir, M5 se fortalece e o risco de obsolescência cai. É o teste mais barato e mais decisivo
disponível, e depende apenas de continuar executando o ciclo.

---

## Tabela de discriminação

O que cada modelo prevê para a próxima medição:

| Medição | M1 estratificação | M2 fixação total | M3 memória | M4 lote | M5 convergência |
|---|---|---|---|---|---|
| cobertura exata no próximo ciclo | estável | irrelevante | irrelevante | irrelevante | **sobe** |
| ganho ao aumentar lote | cai um pouco | cai | cai muito | **cai muito** | inalterado |
| ganho de INT4 sem silício | moderado | irrelevante | **grande** | moderado | irrelevante |
| valor de `hardened_only=False` vs `True` | menor | **maior** | igual | menor | maior |
| participação do KV em contexto longo | cresce | cresce | **domina** | cresce | cresce |

Nenhuma linha desta tabela é opinião: todas são executáveis com o código existente. As duas
primeiras já foram medidas e favorecem M3 e M4.

## Consequência para o ciclo C-002

O próximo ciclo deve priorizar as medições que **separam** os modelos, não as que confirmam o
preferido:

1. rodar `hardened_only=False` e comparar com `True` (separa M1 de M2, testa C-005);
2. varrer lote de 1 a 256 e medir onde a vantagem de hardening desaparece (separa M4);
3. repetir a cobertura exata com corpus ampliado (testa M5).

Nenhuma delas exige hardware, pesos ou dinheiro. Todas são executáveis nesta semana.
