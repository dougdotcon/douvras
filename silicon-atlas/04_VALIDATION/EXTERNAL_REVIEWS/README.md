---
artifact: EXTERNAL_REVIEWS_INDEX
status: VAZIO — lacuna G-010 aberta
---

# Revisões externas

**Este diretório está vazio, e isso é o achado.**

O Método §6.7 estabelece que uma pessoa não aprova sozinha a própria afirmação, e o portão V3
(§4.4) exige que a hipótese sobreviva a pelo menos uma revisão adversarial. No ciclo C-001, autor
e auditor são o mesmo agente. Por isso:

- `G-010` está aberta no [GAP_REGISTER](../../02_OBSERVATION/GAP_REGISTER.md);
- o portão **V3 está bloqueado** — `atlas gates` reporta isso a cada execução;
- nenhum documento deste repositório pode alegar ter sobrevivido a revisão independente.

Um diretório com um arquivo dizendo "revisado internamente, tudo certo" seria pior que vazio:
daria aparência de auditoria sem a substância.

## Papéis mínimos ainda não preenchidos (Método §6.7)

| Papel | Ocupado por | Estado |
|---|---|---|
| autor | agente que construiu o sistema | preenchido |
| adversário interno | mesmo agente | **conflito de interesse** |
| auditor de fontes | mesmo agente | **conflito de interesse** |
| auditor computacional | testes automatizados | parcial — testes escritos pelo autor |
| especialista externo | ninguém | **vazio** |
| curador de status | mesmo agente | **conflito de interesse** |

## O que uma revisão externa útil precisa atacar

Em ordem de valor. Um revisor que confirmasse tudo teria produzido pouco; o pedido é que tente
derrubar.

1. **A IR representa o modelo?** Trace um modelo do corpus com `torch.export` e compare FLOPs e
   bytes por classe de operador. Divergência > 10 % em classe com > 5 % do custo derruba `A-001`.
2. **O roofline acerta o regime?** Meça latência por camada em GPU real. Se o decode não for
   memory-bound como o modelo prevê, `C-003` cai e com ela boa parte das conclusões.
3. **Os priors de quantização são defensáveis?** Meça perplexidade por camada. Qualquer papel com
   prior ≥ 0,7 que degrade além do limite derruba `A-004`.
4. **A assimetria energética invalida a comparação?** O ganho de energia compara modelo analítico
   de ASIC contra TDP medido de GPU (`E-008` do THREAT_MODEL). É defensável ou o número deveria
   ser retirado?
5. **O corpus é representativo ou conveniente?** Nove modelos, cinco famílias, todos
   decoder-only densos ou MoE. A conclusão sobreviveria a atenção linear, SSM, difusão?
6. **A partição vazia é resultado ou artefato do limiar?** `min_stability = 0.6` em
   [partition_policy.v1.json](../../config/partition_policy.v1.json) é decisão de projeto sem
   base empírica. Um limiar de 0,45 mudaria toda a conclusão do ciclo.

O item 6 é o mais desconfortável e por isso o mais importante.

## Como registrar uma revisão

Crie `ER-<NNN>-<sobrenome>.md` seguindo o modelo abaixo. Revisões que **confirmam** também são
registradas — inclusive as que não encontraram nada, porque a ausência de achado só tem valor se
a busca foi documentada.

```markdown
---
artifact: EXTERNAL_REVIEW
id: ER-001
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
