# ADR-0004 — Economia emitida como distribuição, nunca como ponto

Status: ACEITA · Data: 2026-08-03 · Ciclo: C-001

## Contexto

O Método §6.6 afirma que valor econômico também é falsificável, e §18.2 alerta contra benchmarks
promocionais. A equação de break-even do §12.8 é uma divisão — e uma divisão por uma diferença
de custos pequena e incerta explode. Um único número ("break-even em 4,1 trilhões de tokens")
transmite precisão que os insumos (`A-006`, `A-008`, G-004, G-005) não têm.

## Alternativas

1. Ponto único com nota de rodapé sobre incerteza.
2. Análise de cenários (pessimista/base/otimista) escrita à mão.
3. **Monte Carlo** sobre distribuições declaradas por parâmetro, emitindo P10/P50/P90 e a
   probabilidade de break-even ocorrer **dentro** da vida econômica.

## Decisão adotada

Alternativa **3**, com semente fixa e distribuições versionadas em `config/economics_priors.v1.json`.
A saída obrigatória inclui:

- `P(break-even antes do fim da vida útil)` — a única métrica que responde à decisão real;
- decomposição de sensibilidade (qual parâmetro domina a variância);
- o valor esperado ajustado por **risco de obsolescência**, tratado como sobrevivência da estrutura,
  não como desconto arbitrário.

## Razões

- O falsificador F4 da carta do problema ("break-even P50 > vida econômica") só é verificável se
  houver P50.
- A decomposição de sensibilidade converte a incerteza em **plano de pesquisa**: o parâmetro que
  domina a variância vira o próximo item do `GAP_REGISTER`, com prioridade justificada.
- Impede o uso comercial mais perigoso do produto: entregar um número redondo que o cliente leva
  para o comitê de investimento como se fosse medição.

## Consequências positivas

- O relatório mostra explicitamente quando a decisão **não pode** ser tomada com a evidência atual
  (intervalo atravessa a vida útil) — que é um entregável legítimo, não uma falha.

## Consequências negativas

- Exige que cada premissa econômica declare uma distribuição, não só um valor.
- Resultado é mais difícil de vender que um número único. Aceito: o produto vende auditabilidade.

## Evidência necessária para revisar

Cotações reais de foundry (G-005) e síntese real (G-007) estreitariam as distribuições a ponto de
tornar o P50 defensável isoladamente para nós tecnológicos específicos.
