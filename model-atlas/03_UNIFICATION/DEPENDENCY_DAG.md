---
artifact: DEPENDENCY_DAG
run_id: 20260815T004820Z
generated_by: scripts/run_model_cycle.py
---

# Grafo de dependencias

> Arquivo **gerado**. As setas tracejadas sao lacunas abertas — os lugares onde a
> cadeia ainda nao fecha.

```mermaid
flowchart TD
    T["corpus de tarefas<br/>COMPUTATIONAL_EVIDENCE"] --> G["grader verificado<br/>COMPUTATIONAL_EVIDENCE"]
    G --> I["instrumento<br/>COMPUTATIONAL_EVIDENCE"]
    I -.->|"G-107 corpus sintetico"| V["validade externa"]
    W["pesos locais"] -.->|"G-101 ausente"| C["capacidade medida"]
    C --> D["deficit"]
    D --> S["CSS"]
    P["priors de capacidade<br/>ASSUMPTION"] -.->|"G-104 nao calibrados"| S
    S --> A["alvo de dataset"]
    F["ficha do modelo<br/>ASSUMPTION"] -.->|"G-108 nao verificada"| M["footprint de memoria"]
    M --> R["cabe em 16 GB"]
    T2["telemetria"] -.->|"G-102 ausente"| RO["roda em velocidade util"]

    style C fill:#78350f,color:#fff
    style S fill:#78350f,color:#fff
    style A fill:#78350f,color:#fff
    style I fill:#166534,color:#fff
    style G fill:#166534,color:#fff
```

## Onde a cadeia fecha

Do corpus ao instrumento verificado, sem lacuna pendurada: sao afirmacoes sobre
codigo e corpus que estao no repositorio e reexecutam identicos.

## Onde a cadeia nao fecha

| Aresta ausente | Lacuna | Consequencia |
|---|---|---|
| pesos locais -> capacidade medida | `G-101` | nenhuma capacidade e medida; o CSS nao tem entrada |
| priors calibrados -> CSS | `G-104` | mesmo com medicao, o alvo carrega premissa nao demonstrada |
| ficha verificada -> footprint | `G-108` | o 'cabe?' herda a aproximacao da contagem de parametros |
| telemetria -> velocidade util | `G-102` | caber nao e rodar, e o relatorio nao pode dizer que roda |
| corpus real -> validade externa | `G-107` | o instrumento mede o gerador ate prova em contrario |

Lacunas registradas neste ciclo: **10 abertas**.
