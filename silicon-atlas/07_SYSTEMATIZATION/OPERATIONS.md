---
artifact: OPERATIONS
cycle: C-001
gate: S6
---

# Operação

## O ciclo é uma execução, não um projeto

```bash
python scripts/run_cycle.py
```

Regenera invariantes, resultado do experimento, assessments e evidência no claim ledger. Roda em
segundos sobre o corpus inteiro. Um ciclo DOUVRAS que exige uma semana de trabalho manual não é
executado — e um que não é executado não produz memória.

## Rotina de acompanhamento de versão (o produto recorrente do Método §17.2)

Quando um laboratório publica uma nova versão:

```bash
# 1. registrar a versão no corpus, com proveniência
#    corpus/models/<novo>.json  ← config.json + bloco douvras

# 2. verificar a transcrição contra a fonte
atlas registry verify <novo> --repo <org/nome>

# 3. o que mudou estruturalmente
atlas diff <anterior> <novo>

# 4. a mudança move a decisão?
python scripts/run_cycle.py --models <novo>
```

O que se observa, nessa ordem:

1. **`stability.exact` caiu?** A vida útil de qualquer circuito derivado caiu junto.
2. **Algum papel mudou de participação de custo?** O ranking de candidatos muda com ele.
3. **Algum falsificador passou a disparar?** O ledger retrata sozinho; a decisão de o que fazer
   é humana e vai para o `DECISION_LOG`.
4. **A banda do SRS mudou?** Só então há motivo para reabrir a conversa comercial.

## Política de status em operação

Promover status é **decisão humana registrada**, nunca efeito colateral de execução.
`ClaimLedger.record_run` anexa evidência e pode retratar, mas jamais promove.

Para promover:

1. fechar a lacuna correspondente no `GAP_REGISTER` com evidência anexada;
2. registrar a decisão no `DECISION_LOG`;
3. editar o status no `CLAIM_LEDGER`;
4. reexecutar o ciclo e confirmar que os relatórios refletem o novo status.

## Critérios de encerramento (Método §6.4)

O ciclo de silício desta rota é encerrado se, após três ciclos:

- nenhum caso do corpus produzir região fixa não vazia; **ou**
- o break-even P50 permanecer acima da vida econômica em todos os casos; **ou**
- a taxa de mudança estrutural observada permanecer acima de 0,5/ano nas famílias relevantes; **ou**
- `G-002` permanecer aberta por falta de acesso a pesos ou a orçamento de avaliação.

Encerrar por critério pré-definido é governança, não fracasso. Nesse cenário, o produto
sobrevive como camada de inteligência de otimização — rota 6 do roadmap do Método §16.

## Estado dos portões

```bash
atlas gates
```

| Portão | Estado ao fim de C-001 | O que falta |
|---|---|---|
| D0 — identidade do problema | **aberto** | — |
| O1 — cobertura observacional | **aberto** | — |
| U2 — estrutura candidata | **aberto** | — |
| V3 — sobrevivência mínima | **fechado** | revisão adversarial externa (`G-010`) |
| R4 — estrutura mínima operável | **aberto** | — |
| A5 — protótipo verificável | **aberto** | — |
| S6 — operação cumulativa | **aberto** | — |

V3 permanece fechado por decisão, não por omissão: o Método §6.7 exige que a validação final não
dependa de quem criou o resultado, e neste ciclo autor e auditor são o mesmo agente.

## Riscos operacionais monitorados

| Risco | Sinal de alerta | Ação |
|---|---|---|
| Priors envelhecerem sem revisão | `config/*.json` sem alteração por mais de dois ciclos | revisão obrigatória de premissas |
| Corpus enviesado para uma família | uma família com mais de metade dos modelos | ampliar corpus antes de citar cobertura |
| Score usado além do que sustenta | recomendação intra-modelo citando LHS | bloqueado por `CE-001` até `G-011` fechar |
| Relatório citado sem status | citação externa de número sem o rótulo | Anexo D existe para tornar isso rastreável |
