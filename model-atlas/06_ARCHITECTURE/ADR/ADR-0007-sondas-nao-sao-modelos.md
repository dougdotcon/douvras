---
artifact: ADR
id: ADR-0007
date: 2026-08-14
status: adotada
---

# Execução sintética não produz capacidade medida

## Contexto

As sondas de calibração (`runner.PROBES`) produzem `RunResult` com escore por capacidade, taxa
de falha por modo e tudo o mais que uma execução real produziria. A estrutura de dados é
idêntica. A diferença é só a origem.

Isso é perigoso exatamente por ser conveniente: `oraculo` tem 100 %, `ferramenta-errada` tem
43,8 %, e a tentação de mostrar essa tabela como "resultados do benchmark" é grande, ainda mais
quando o alternativo é um relatório cheio de travessões.

## Alternativas

1. **Confiar na disciplina de quem escreve o relatório.** Rotular na prosa que aqueles números
   são sintéticos.
2. **Não expor os resultados das sondas.** Guardá-los internos ao módulo de instrumento.
3. **Recusar no tipo, na fronteira, uma vez.**

## Decisão adotada

Alternativa 3. `Respondent.synthetic` é parte do protocolo; `RunResult` carrega a flag; e
`CapabilityFingerprint.from_run` **recusa** produzir capacidade medida a partir de execução
sintética — devolve ausência declarada com `G-101`, uma por capacidade.

## Razões

- A alternativa 1 é o que o Silicon Atlas tentou implicitamente e falhou: o fator `P` valia
  1,000 em oito de nove relatórios, derivado de um acelerador que os próprios relatórios
  declaravam inexistente ([R-002](../../../silicon-atlas/00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md)).
  Disciplina de prosa não sobrevive a um refactor às onze da noite.
- A alternativa 2 joga fora informação legítima: o comportamento das sondas é o que prova que a
  taxonomia está viva.
- Recusar no tipo custa uma linha e vale para sempre. Quem tentar contornar precisa alterar o
  módulo, e isso aparece no diff.

## Consequências positivas

- O Failure Atlas das sondas pode ser publicado sem risco: ele responde "o grader detecta isto",
  e o relatório diz isso na própria seção.
- O portão de emissão tem uma regra de coerência (`COHERENCE_RULES`) confrontando a frase
  *"nenhuma capacidade foi medida"* com o `Finding` `css_alvo`: se algum dia um número entrar
  ali, o relatório não é emitido.

## Consequências negativas

- O assessment deste ciclo é, em grande parte, uma lista de ausências declaradas.
- O CSS não tem entrada e não pode ser exercitado pelo corpus real — a mesma armadilha do
  `G-014` do Silicon Atlas, onde o caminho econômico atravessou um ciclo inteiro sem nunca ter
  sido executado. Mitigado por `tests/model/test_nondegenerate.py`, que monta um fingerprint
  medido sintético **em teste** e força o caminho completo a rodar.

## Evidência necessária para revisar esta decisão

Nenhuma prevista. Um respondente sintético nunca vira medição de modelo; o que pode mudar é a
chegada de respondentes reais, que já entram com `synthetic=False` e passam pelo mesmo caminho.
