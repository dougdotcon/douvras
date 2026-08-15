# Método DOUVRAS

Formalizei o método como:

> **DOUVRAS — Delimitação, Observação, Unificação, Validação, Redução, Arquitetura e Sistematização.**

Ele preserva o contrato que já havíamos desenvolvido: pergunta clara, definições explícitas, hipóteses separadas, formalização, critérios de falha, implementação reproduzível, comparação com referências e auditoria. 

Também incorporei os mecanismos mais rigorosos do Programa Tamesis:

* `CLAIM_LEDGER` para controlar alegações;
* `GAP_REGISTER` para registrar lacunas;
* `DEPENDENCY_DAG` para tornar dependências visíveis;
* busca deliberada por contraexemplos;
* revisão adversarial;
* baselines congelados;
* critérios antecipados de encerramento;
* separação entre pesquisa científica e engenharia de produto.  

O tutorial completo tem aproximadamente **7.600 palavras**, incluindo templates, estrutura de repositório, portões de validação, fórmulas, arquitetura do produto, plano de 90 dias e roadmap de até 24 meses.

[Baixar o tutorial completo em Markdown](sandbox:/mnt/data/METODO_DOUVRAS_E_SILICON_ATLAS.md)

## Como aplicar à demanda dos ASICs

O software proposto recebeu o nome:

# **DOUVRAS Silicon Atlas**

> **Uma plataforma que descobre quais partes de um modelo de IA já estão estáveis o suficiente para virar silício.**

A principal correção que o método faz na tese apresentada é esta:

**ASIC não significa necessariamente um chip preso a um único modelo.** Existe uma escala de especialização:

```text
GPU genérica
    ↓
kernel otimizado
    ↓
acelerador de operadores
    ↓
ASIC para Transformers
    ↓
ASIC para uma família de modelos
    ↓
arquitetura e formas fixas
    ↓
pesos parcialmente fixos
    ↓
modelo inteiro hardwired
```

Quanto mais se desce nessa escala, maior pode ser a eficiência, mas também aumentam:

* o risco de obsolescência;
* o custo de fabricação;
* a dependência de um modelo;
* a dificuldade de corrigir falhas;
* o risco de o chip ficar ultrapassado antes do break-even.

A oportunidade não é apenas “fabricar um ASIC do Llama”. É construir o sistema que determina **quanto do modelo deve ser fixado**.

## A tese já começou a se materializar

Em 2026, a Taalas apresentou o HC1, um demonstrador com o Llama 3.1 8B implementado diretamente em hardware. A empresa reporta 17 mil tokens por segundo por usuário, embora esses números sejam do próprio fabricante e ainda devam ser tratados como não reproduzidos independentemente. A implementação preserva contexto configurável e suporte a LoRA, mostrando que uma base hardwired ainda pode manter alguma adaptabilidade. ([Taalas][1])

O artigo *Physical Foundation Models* também argumenta que eliminar parte da programabilidade pode gerar vantagens de várias ordens de grandeza, inclusive por meio de pesos em memória somente leitura ou da implementação física direta das transformações do modelo. Entretanto, o trabalho apresenta essa possibilidade como uma direção de pesquisa com desafios técnicos ainda abertos, e não como garantia de “100 vezes mais barato” para qualquer modelo. ([arXiv][2])

Portanto, a afirmação dos **100×** deve ser tratada como:

```text
CONDITIONAL_HYPOTHESIS
```

Ela precisa declarar:

* modelo;
* workload;
* precisão;
* tamanho de lote;
* comprimento do contexto;
* prefill ou decode;
* consumo total do servidor;
* custo de fabricação;
* baseline de GPU;
* vida útil econômica;
* se o resultado foi reproduzido externamente.

## O que o Silicon Atlas faria

A plataforma receberia modelos e suas diferentes versões e produziria:

1. **Fingerprint arquitetural**
   Identifica atenção, MLP, normalização, RoPE, MoE, shapes, precisão, cache e fluxo de memória.

2. **Análise de estabilidade**
   Compara versões do mesmo modelo e famílias concorrentes para encontrar estruturas que não mudam.

3. **Profiler de custo real**
   Separa tempo e energia gastos em prefill, decode, MLP, atenção, KV cache, roteamento e movimentação de dados.

4. **Detector de candidatos a hardening**
   Procura blocos estáveis, repetitivos, quantizáveis e responsáveis por uma parcela significativa da computação.

5. **Particionador híbrido**
   Recomenda o que deve permanecer em CPU, GPU, FPGA, memória programável ou lógica fixa.

6. **Simulador PPA e econômico**
   Estima potência, performance, área, memória, NRE, custo por token e tempo para break-even.

7. **Gerador pré-hardware**
   Produz inicialmente kernels, HLS, RTL parametrizado, testbenches, simulação e protótipos FPGA.

8. **Pacote de verificação**
   Entrega golden model, vetores de teste, tolerâncias numéricas, regressões, propriedades formais e limitações.

## A descoberta mais provável

A primeira hipótese a testar não deveria ser:

> “Podemos fixar um modelo inteiro?”

A hipótese mais segura e comercialmente interessante seria:

> **Uma pequena quantidade de padrões computacionais estáveis concentra grande parte do custo da inferência e pode ser endurecida, enquanto adaptação, controle e operadores emergentes permanecem programáveis.**

Uma possível divisão seria:

```text
LÓGICA FIXA OU IP ESPECIALIZADO
├── projeções matriciais quantizadas
├── determinadas regiões do MLP
├── dataflow de pesos
├── normalização
└── operações estáveis de atenção

MEMÓRIA CONFIGURÁVEL
├── LoRA
├── adapters
├── cabeças especializadas
└── parâmetros por cliente

FPGA OU BLOCO RECONFIGURÁVEL
├── novos operadores
├── roteamento MoE
├── variações de atenção
└── experimentação

CPU/GPU
├── controle
├── sampling
├── fallback
├── segurança
└── orquestração
```

## Stack inicial

O caminho de software pode combinar:

* PyTorch, ONNX e JAX para importar modelos;
* MLIR para criar a representação intermediária `DOUVRAS IR`;
* Apache TVM para exploração de kernels e backends;
* CIRCT para baixar representações em circuitos e gerar Verilog;
* Verilator e cocotb para simulação;
* Yosys e OpenROAD para exploração de síntese e layout;
* FPGA como primeiro hardware real.

MLIR foi projetado para representar computação em vários níveis e hardware heterogêneo; CIRCT fornece infraestrutura para compiladores de circuitos, geração de Verilog e verificação; OpenROAD oferece um fluxo aberto de RTL sintetizável até layout GDSII. ([MLIR][3])

## MVP de 90 dias

O primeiro MVP não fabricaria um chip. Ele provaria cinco capacidades:

```text
modelo
  → representação canônica
  → comparação entre versões
  → descoberta de bloco estável
  → estimativa de ganho
  → microacelerador simulado
```

### Dias 1–30

* importar três famílias de modelos;
* registrar versões e licenças;
* gerar grafos canônicos;
* criar fingerprints;
* mostrar visualmente o que mudou entre versões.

### Dias 31–60

* medir hotspots;
* testar INT8 e INT4;
* criar o `Layer Hardening Score`;
* calcular estabilidade temporal;
* construir a primeira calculadora de break-even.

### Dias 61–90

* selecionar um subgrafo;
* gerar HLS ou RTL;
* executar no Verilator;
* comparar com o golden model;
* produzir uma recomendação de partição;
* apresentar tudo em um dashboard.

## Como ganhar dinheiro antes de fabricar hardware

A entrada comercial mais realista é vender um:

### **Silicon Readiness Assessment**

A empresa envia um modelo ou workload e recebe:

* análise estrutural;
* hotspots;
* estabilidade;
* quantização;
* arquitetura recomendada;
* estimativa de PPA;
* risco de obsolescência;
* cálculo de break-even;
* roadmap FPGA/ASIC;
* pacote técnico para investidores ou fabricantes.

Depois, a receita recorrente viria do monitoramento contínuo:

* novas versões do modelo;
* alterações arquiteturais;
* regressões;
* mudança do break-even;
* surgimento de operadores;
* necessidade de atualizar o projeto de hardware.

A posição estratégica da DOUVRAS seria:

> **Não competir inicialmente para fabricar o chip. Tornar-se a camada de inteligência, auditoria e codesign que determina o que merece virar chip.**

[1]: https://taalas.com/the-path-to-ubiquitous-ai/?utm_source=chatgpt.com "The path to ubiquitous AI"
[2]: https://arxiv.org/abs/2604.27911?utm_source=chatgpt.com "Physical Foundation Models: Fixed hardware implementations of large-scale neural networks"
[3]: https://mlir.llvm.org/?utm_source=chatgpt.com "MLIR"
