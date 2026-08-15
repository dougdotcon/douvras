"""Custo de execucao: o que a aritmetica sabe e o que so a medicao sabe.

O paralelo com o Silicon Atlas e exato e vale explicitar. La, o roofline acerta o **regime**
(limitado por memoria ou por aritmetica) com muito mais confianca que o valor absoluto, e o
`ADR-0001` deixou isso escrito antes de alguem se empolgar com o numero. Aqui a divisao e a
mesma, so que mais nitida:

- **footprint de pesos** e multiplicacao: parametros x bytes por parametro. Da para calcular
  sem baixar nada, e responde a pergunta que decide o dia de quem tem 16 GB — *cabe?*
- **TTFT, tokens/s, RAM de pico, latencia** sao medicao. Nao existe formula honesta para eles
  numa maquina que nunca rodou o modelo, e chutar aqui contamina o precision cliff, o CSS e
  qualquer recomendacao de quantizacao a jusante.

Entao o profiler faz as duas coisas e **rotula cada uma pelo que ela e**. O que nao mede, ele
declara ausente com `G-102`, em vez de estimar com um numero de aparencia razoavel.

A conta de footprint tambem nao inclui KV cache nem ativacoes, e isso esta no `note` de todo
`Finding` que ela produz: o Silicon Atlas gastou um ciclo com `embed_tokens` contabilizado
errado para aprender que footprint parcial apresentado como total vira decisao errada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from douvras_core.status import Finding, FindingSet, Status, derive

from .registry import BYTES_PER_PARAM, HFModelSpec

#: Lacuna de medicao de execucao: nenhuma latencia, vazao ou RAM de pico foi observada.
GAP_NO_TELEMETRY = "G-102"

#: Premissa: bytes por parametro efetivos do formato GGUF, de engenharia e nao de medicao.
A_QUANT_BYTES = "A-102"

#: Premissa: contagem de parametros aproximada, transcrita de documento secundario.
A_PARAMS = "A-101"

#: Folga tipica de runtime (contexto, buffers, tokenizer, processo) sobre o footprint de pesos.
#: E um multiplicador de engenharia, nao medicao — por isso o resultado sai como ASSUMPTION.
RUNTIME_OVERHEAD = 1.20


@dataclass
class MemoryBudget:
    """Quanto o modelo ocupa em disco e, aproximadamente, em RAM — por quantizacao."""

    model_id: str
    params: int | None
    rows: dict[str, float] = field(default_factory=dict)

    @classmethod
    def build(cls, spec: HFModelSpec) -> "MemoryBudget":
        linhas: dict[str, float] = {}
        for q in BYTES_PER_PARAM:
            b = spec.weights_bytes(q)
            if b is not None:
                linhas[q] = b
        return cls(model_id=spec.id, params=spec.params, rows=linhas)

    def fits_in(self, quant: str, ram_bytes: float) -> bool | None:
        b = self.rows.get(quant)
        return None if b is None else (b * RUNTIME_OVERHEAD) <= ram_bytes

    def findings(self, ram_bytes: float) -> FindingSet:
        fs = FindingSet(f"orcamento de memoria — {self.model_id}")
        if self.params is None:
            fs.add(
                Finding(
                    "footprint_pesos",
                    None,
                    Status.OPEN_GAP,
                    gaps=("G-108",),
                    note="contagem de parametros ausente no corpus; nada a multiplicar",
                )
            )
            return fs
        base = Finding(
            "parametros",
            self.params,
            Status.ASSUMPTION,
            unit="parametros",
            assumptions=(A_PARAMS,),
            note="aproximado — a fonte diz 'cerca de', nao um inteiro",
        )
        fs.add(base)
        for q, b in self.rows.items():
            bytes_por = Finding(
                f"bytes_por_parametro.{q}",
                BYTES_PER_PARAM[q],
                Status.ASSUMPTION,
                assumptions=(A_QUANT_BYTES,),
            )
            fs.add(
                derive(
                    f"footprint_pesos.{q}",
                    round(b / 1e9, 3),
                    [base, bytes_por],
                    unit="GB",
                    note="somente pesos residentes; nao inclui KV cache nem ativacoes",
                )
            )
        cabe = [q for q in self.rows if self.fits_in(q, ram_bytes)]
        fs.add(
            Finding(
                "quantizacoes_que_cabem",
                cabe,
                Status.ASSUMPTION,
                assumptions=(A_PARAMS, A_QUANT_BYTES),
                note=(
                    f"com folga de runtime de {RUNTIME_OVERHEAD:.2f}x sobre "
                    f"{ram_bytes / 1e9:.0f} GB; caber nao implica ser utilizavel"
                ),
            )
        )
        return fs

    def render(self, ram_bytes: float) -> str:
        if not self.rows:
            return "Sem contagem de parametros no corpus: nao ha footprint a calcular."
        linhas = [
            "| Quantizacao | Pesos | Com folga de runtime | Cabe? | Qualidade |",
            "|---|---:|---:|:---:|:---:|",
        ]
        for q, b in self.rows.items():
            folga = b * RUNTIME_OVERHEAD
            cabe = "sim" if self.fits_in(q, ram_bytes) else "nao"
            linhas.append(
                f"| `{q}` | {b / 1e9:.2f} GB | {folga / 1e9:.2f} GB | {cabe} | — |"
            )
        linhas += [
            "",
            "A coluna **Qualidade** esta vazia porque nenhuma perplexidade foi medida (`G-103`).",
            "E a coluna que decide a escolha de quantizacao, e a unica que a aritmetica nao da.",
        ]
        return "\n".join(linhas)


@dataclass
class InferenceProfile:
    """Telemetria de execucao. Sem execucao, todo campo e ausencia declarada."""

    model_id: str
    measured: bool = False
    ttft_s: float | None = None
    tokens_per_s: float | None = None
    peak_ram_bytes: float | None = None
    quantization: str = ""

    def findings(self) -> FindingSet:
        fs = FindingSet(f"perfil de inferencia — {self.model_id}")
        campos = (
            ("ttft", self.ttft_s, "s"),
            ("tokens_por_segundo", self.tokens_per_s, "tok/s"),
            ("ram_de_pico", self.peak_ram_bytes, "bytes"),
        )
        for nome, valor, unidade in campos:
            if self.measured and valor is not None:
                fs.add(Finding(nome, valor, Status.OBSERVATION, unit=unidade,
                               note=f"medido em {self.quantization}"))
            else:
                fs.add(
                    Finding(
                        nome,
                        None,
                        Status.OPEN_GAP,
                        gaps=(GAP_NO_TELEMETRY,),
                        note="nenhuma execucao real; ver ADR-0006",
                    )
                )
        return fs


__all__ = [
    "MemoryBudget",
    "InferenceProfile",
    "GAP_NO_TELEMETRY",
    "RUNTIME_OVERHEAD",
    "A_PARAMS",
    "A_QUANT_BYTES",
]
