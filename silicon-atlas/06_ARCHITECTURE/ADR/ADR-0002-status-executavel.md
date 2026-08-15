# ADR-0002 — Status epistêmico como tipo, não como comentário

Status: ACEITA · Data: 2026-08-03 · Ciclo: C-001

## Contexto

O contrato do Método (§3.1) exige status explícito para toda afirmação. Em projetos reais essa
regra sobrevive nos documentos e morre no código: a planilha diz `ASSUMPTION`, o dashboard mostra
o número sozinho, e três meses depois ninguém sabe se `break_even = 4.1e12 tokens` é medição ou chute.

## Alternativas

1. Convenção documental: cada relatório declara status manualmente.
2. Anotação: campo `status` opcional em dicionários de saída.
3. **Tipo obrigatório**: nenhum valor numérico trafega entre motores sem `Finding(value, status, …)`,
   com propagação automática do status mais fraco.

## Decisão adotada

Alternativa **3**. `Finding` é imutável, exige `status`, e `Finding.derive()` calcula o status do
resultado como o **mínimo** dos status das dependências, limitado pelo status máximo que o método
de cálculo permite. Promover manualmente levanta `StatusViolation`.

## Razões

- Torna o §3.2 (vocabulário proibido) verificável por máquina, não por disciplina pessoal.
- A regra "uma conclusão não pode ser mais forte que sua dependência mais fraca" é exatamente um
  reticulado (lattice) — implementável como `min` sobre uma ordem total.
- Um relatório gerado carrega automaticamente a cadeia de premissas que o sustenta; a seção
  "o que este resultado não demonstra" deixa de ser redigida à mão.

## Consequências positivas

- Impossível emitir um break-even como `EXPERIMENTAL_EVIDENCE` enquanto G-002/G-005 estiverem abertos.
- A "dívida de evidência" (§6.3) fica computável: basta somar os `Finding` cujo status < `OBSERVATION`.

## Consequências negativas

- Verbosidade: cada motor devolve objetos, não floats. Mitigado por `Finding.value` e operadores
  aritméticos que propagam status.
- Custo de disciplina em código de teste (usa-se `.value` explicitamente).

## Evidência necessária para revisar

Se o overhead de tipagem reduzir a velocidade de iteração de pesquisa a ponto de motores serem
escritos fora do framework, a decisão falhou e deve ser substituída por checagem em fronteira
(apenas na emissão de relatório).
