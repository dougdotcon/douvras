"""DOUVRAS IR — representacao canonica de um caminho de inferencia (Metodo 12.2).

O grafo e independente de hardware e de workload: descreve *o que* e computado, com shapes
simbolicos em B (batch), S (prompt) e T (contexto). Custo em tempo e energia e responsabilidade
do profiler; aqui ficam apenas propriedades da computacao (FLOPs, elementos, bytes de peso),
que nao dependem do dispositivo.

Status da IR: MODEL. Nunca OBSERVATION (ADR-0001).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Iterator, Sequence


class OpKind(StrEnum):
    """Classes de operador da IR. A granularidade e a que o hardware distingue."""

    EMBEDDING = "embedding"
    NORM = "norm"
    LINEAR = "linear"
    ROPE = "rope"
    ATTN_SCORES = "attn_scores"       # Q @ K^T
    ATTN_SOFTMAX = "attn_softmax"
    ATTN_CONTEXT = "attn_context"     # P @ V
    KV_WRITE = "kv_write"
    KV_READ = "kv_read"
    ACTIVATION = "activation"
    ELEMENTWISE = "elementwise"
    RESIDUAL = "residual"
    ROUTER = "router"                 # MoE: escolha de especialista por token
    DISPATCH = "dispatch"             # MoE: gather/scatter de tokens por especialista
    LOGIT_CAP = "logit_cap"
    SAMPLING = "sampling"


class Phase(StrEnum):
    PREFILL = "prefill"
    DECODE = "decode"


@dataclass(frozen=True)
class Precision:
    name: str
    bits: float

    @property
    def bytes_per_elem(self) -> float:
        return self.bits / 8.0

    def __str__(self) -> str:
        return self.name


PRECISIONS: dict[str, Precision] = {
    "fp32": Precision("fp32", 32),
    "bf16": Precision("bf16", 16),
    "fp16": Precision("fp16", 16),
    "fp8": Precision("fp8", 8),
    "int8": Precision("int8", 8),
    "int4": Precision("int4", 4),
    # ternario empacotado: log2(3) bits por peso, na pratica ~1.6 (ver TOM, E-005)
    "ternary": Precision("ternary", 1.6),
}


def precision(name: str) -> Precision:
    try:
        return PRECISIONS[name]
    except KeyError:
        raise ValueError(f"precisao desconhecida: {name!r}; use {sorted(PRECISIONS)}") from None


@dataclass(frozen=True)
class Workload:
    """Condicoes sob as quais o custo e avaliado. Sem workload nao existe hotspot.

    ``prompt_len`` (S) e usado em PREFILL; ``context_len`` (T) em DECODE.
    """

    phase: Phase = Phase.DECODE
    batch: int = 1
    prompt_len: int = 2048
    context_len: int = 2048
    activation_precision: str = "bf16"

    @property
    def tokens(self) -> int:
        """Tokens processados por invocacao."""
        return self.batch * (self.prompt_len if self.phase is Phase.PREFILL else 1)

    @property
    def seq(self) -> int:
        """Comprimento de sequencia relevante para atencao."""
        return self.prompt_len if self.phase is Phase.PREFILL else self.context_len

    @property
    def act_precision(self) -> Precision:
        return precision(self.activation_precision)

    def label(self) -> str:
        return (
            f"{self.phase.value} B={self.batch} "
            + (f"S={self.prompt_len}" if self.phase is Phase.PREFILL else f"T={self.context_len}")
            + f" act={self.activation_precision}"
        )


def causal_score_elems(seq: int, window: int | None) -> float:
    """Elementos de score por cabeca em prefill causal, com janela deslizante opcional."""
    if window is None or window >= seq:
        return seq * (seq + 1) / 2.0
    return seq * window - window * (window - 1) / 2.0


@dataclass
class Node:
    """Um operador da IR.

    ``active_count``  quantas instancias executam por token (MoE: top-k).
    ``resident_count`` quantas instancias precisam existir em memoria (MoE: todos experts).
    A diferenca entre os dois e o que torna MoE barata em FLOPs e cara em memoria.
    """

    id: str
    kind: OpKind
    role: str
    block: str
    layer: int | None = None
    weight_shape: tuple[int, ...] | None = None
    bias: int = 0
    inputs: tuple[str, ...] = ()
    attrs: dict[str, Any] = field(default_factory=dict)
    active_count: int = 1
    resident_count: int = 1
    dynamic: bool = False
    data_dependent_addressing: bool = False
    weight_precision: str = "bf16"

    # -- estrutura ------------------------------------------------------------------
    def _param_elems(self) -> int:
        n = 0
        if self.weight_shape:
            n = 1
            for x in self.weight_shape:
                n *= x
        return n + self.bias

    @property
    def weight_elems(self) -> int:
        """Pesos residentes em memoria (footprint). MoE conta todos os experts."""
        return self._param_elems() * self.resident_count

    @property
    def active_weight_elems(self) -> int:
        """Pesos efetivamente lidos por invocacao (MoE le apenas os experts ativos)."""
        return self._param_elems() * self.active_count

    def weight_bytes(self, override: str | None = None) -> float:
        return self.weight_elems * precision(override or self.weight_precision).bytes_per_elem

    def active_weight_bytes(self, override: str | None = None) -> float:
        return self.active_weight_elems * precision(override or self.weight_precision).bytes_per_elem

    def read_weight_bytes(self, w: "Workload", override: str | None = None) -> float:
        """Bytes de peso realmente lidos da memoria por invocacao.

        Distingue dois casos que a contagem ingenua confunde:

        * **gather** (tabela de embeddings): le apenas as linhas dos tokens correntes.
        * **produto matricial** (inclusive `lm_head`): le a matriz inteira, porque todos os
          logits sao necessarios — e por isso um vocabulario grande custa caro em decode.
        """
        if self.kind is OpKind.EMBEDDING:
            b = precision(override or self.weight_precision).bytes_per_elem
            return self.tokens(w) * float(self.attrs.get("width", 0)) * b
        return self.active_weight_bytes(override)

    # -- custo aritmetico -----------------------------------------------------------
    def tokens(self, w: Workload) -> int:
        """Tokens que este no processa.

        A cabeca de logits e o sampling rodam apenas na ultima posicao durante prefill;
        tratar como B*S superestimaria o custo de prefill em ordens de grandeza.
        """
        if self.attrs.get("scope") == "last_token":
            return w.batch
        return w.tokens

    def flops(self, w: Workload) -> float:
        """FLOPs por invocacao sob o workload dado. Propriedade da computacao, nao do chip."""
        a = self.attrs
        tok = self.tokens(w)
        k = self.kind

        if k is OpKind.LINEAR:
            din, dout = a["in_features"], a["out_features"]
            return 2.0 * tok * din * dout * self.active_count

        if k is OpKind.ROUTER:
            return 2.0 * tok * a["in_features"] * a["out_features"] + 5.0 * tok * a["out_features"]

        if k in (OpKind.ATTN_SCORES, OpKind.ATTN_CONTEXT):
            heads, hd = a["heads"], a["head_dim"]
            if w.phase is Phase.PREFILL:
                elems = w.batch * heads * causal_score_elems(w.prompt_len, a.get("window"))
            else:
                keys = min(w.context_len, a.get("window") or w.context_len)
                elems = w.batch * heads * keys
            return 2.0 * hd * elems

        if k is OpKind.ATTN_SOFTMAX:
            heads = a["heads"]
            if w.phase is Phase.PREFILL:
                elems = w.batch * heads * causal_score_elems(w.prompt_len, a.get("window"))
            else:
                keys = min(w.context_len, a.get("window") or w.context_len)
                elems = w.batch * heads * keys
            return 5.0 * elems  # max, exp, soma, divisao

        if k is OpKind.NORM:
            return 5.0 * tok * a["width"]

        if k is OpKind.ROPE:
            return 6.0 * tok * a["width"]

        if k is OpKind.ACTIVATION:
            cost = {"silu": 5.0, "gelu": 10.0, "relu": 1.0}.get(a.get("fn", "silu"), 5.0)
            return cost * tok * a["width"] * self.active_count

        if k in (OpKind.ELEMENTWISE, OpKind.RESIDUAL):
            return 1.0 * tok * a["width"] * self.active_count

        if k is OpKind.LOGIT_CAP:
            return 3.0 * tok * a["width"]

        if k is OpKind.SAMPLING:
            return 6.0 * tok * a["width"]

        if k is OpKind.DISPATCH:
            return 0.0

        return 0.0  # EMBEDDING, KV_READ, KV_WRITE: movimento puro

    # -- movimento de dados ---------------------------------------------------------
    def activation_bytes(self, w: Workload) -> float:
        """Bytes de ativacao lidos+escritos. Nao inclui pesos nem KV cache."""
        a = self.attrs
        b = w.act_precision.bytes_per_elem
        tok = self.tokens(w)
        k = self.kind

        if k is OpKind.LINEAR:
            return b * tok * (a["in_features"] + a["out_features"] * self.active_count)

        if k is OpKind.ROUTER:
            return b * tok * (a["in_features"] + a["out_features"])

        if k is OpKind.EMBEDDING:
            return b * tok * a["width"]

        if k in (OpKind.NORM, OpKind.ROPE, OpKind.LOGIT_CAP):
            return 2.0 * b * tok * a["width"]

        if k in (OpKind.ACTIVATION, OpKind.ELEMENTWISE, OpKind.RESIDUAL):
            return 3.0 * b * tok * a["width"] * self.active_count  # 2 leituras + 1 escrita

        if k is OpKind.SAMPLING:
            return b * tok * a["width"]

        if k in (OpKind.ATTN_SCORES, OpKind.ATTN_SOFTMAX, OpKind.ATTN_CONTEXT):
            # Assume atencao com tiling (estilo FlashAttention): scores nao vao para HBM.
            # Premissa A-002; se o alvo materializar scores, este termo explode.
            if a.get("materialize_scores"):
                if w.phase is Phase.PREFILL:
                    elems = w.batch * a["heads"] * causal_score_elems(w.prompt_len, a.get("window"))
                else:
                    elems = w.batch * a["heads"] * w.context_len
                return 2.0 * b * elems
            return 2.0 * b * tok * a["heads"] * a["head_dim"]

        if k is OpKind.DISPATCH:
            return 2.0 * b * tok * a["width"] * self.active_count

        return 0.0

    def state_bytes(self, w: Workload) -> float:
        """Bytes de estado persistente movidos (KV cache)."""
        a = self.attrs
        b = precision(a.get("kv_precision", w.activation_precision)).bytes_per_elem
        if self.kind is OpKind.KV_WRITE:
            new_tokens = w.prompt_len if w.phase is Phase.PREFILL else 1
            return 2.0 * b * w.batch * new_tokens * a["kv_dim"]
        if self.kind is OpKind.KV_READ:
            keys = min(w.context_len, a.get("window") or w.context_len)
            if w.phase is Phase.PREFILL:
                keys = min(w.prompt_len, a.get("window") or w.prompt_len)
            return 2.0 * b * w.batch * keys * a["kv_dim"]
        return 0.0

    def bytes_moved(self, w: Workload, weight_precision: str | None = None) -> float:
        return (
            self.read_weight_bytes(w, weight_precision)
            + self.activation_bytes(w)
            + self.state_bytes(w)
        )

    def intensity(self, w: Workload, weight_precision: str | None = None) -> float:
        """Intensidade aritmetica: FLOPs por byte. Decide de que lado do roofline o no cai."""
        bm = self.bytes_moved(w, weight_precision)
        return self.flops(w) / bm if bm > 0 else float("inf")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": str(self.kind),
            "role": self.role,
            "block": self.block,
            "layer": self.layer,
            "weight_shape": list(self.weight_shape) if self.weight_shape else None,
            "active_count": self.active_count,
            "resident_count": self.resident_count,
            "dynamic": self.dynamic,
            "data_dependent_addressing": self.data_dependent_addressing,
            "weight_precision": self.weight_precision,
            "attrs": self.attrs,
            "inputs": list(self.inputs),
        }


@dataclass
class Graph:
    """Grafo canonico de um modelo. Imutavel na pratica: construido uma vez, perfilado n vezes."""

    model_id: str
    nodes: list[Node] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def add(self, node: Node) -> Node:
        self.nodes.append(node)
        return node

    def __iter__(self) -> Iterator[Node]:
        return iter(self.nodes)

    def __len__(self) -> int:
        return len(self.nodes)

    def by_id(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def by_block(self, block: str) -> list[Node]:
        return [n for n in self.nodes if n.block == block]

    def blocks(self) -> list[str]:
        seen: dict[str, None] = {}
        for n in self.nodes:
            seen.setdefault(n.block, None)
        return list(seen)

    def layer_nodes(self, layer: int) -> list[Node]:
        return [n for n in self.nodes if n.layer == layer]

    @property
    def num_layers(self) -> int:
        return int(self.meta.get("num_layers", 0))

    def total_weight_elems(self) -> int:
        return sum(n.weight_elems for n in self.nodes)

    def total_flops(self, w: Workload) -> float:
        return sum(n.flops(w) for n in self.nodes)

    def subgraph(self, nodes: Iterable[Node], name: str) -> "Subgraph":
        return Subgraph(name=name, nodes=list(nodes), model_id=self.model_id)

    def block_subgraphs(self) -> list["Subgraph"]:
        """Um subgrafo por bloco (atencao, MLP, MoE, embedding, cabeca)."""
        out: list[Subgraph] = []
        for b in self.blocks():
            ns = self.by_block(b)
            out.append(Subgraph(name=b, nodes=ns, model_id=self.model_id))
        return out

    def as_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "meta": self.meta, "nodes": [n.as_dict() for n in self.nodes]}


@dataclass
class Subgraph:
    """Fronteira declarada sobre um conjunto de nos. Unidade de analise do Atlas (ADR-0003)."""

    name: str
    nodes: list[Node]
    model_id: str = ""

    def __iter__(self) -> Iterator[Node]:
        return iter(self.nodes)

    def __len__(self) -> int:
        return len(self.nodes)

    @property
    def layer(self) -> int | None:
        layers = {n.layer for n in self.nodes if n.layer is not None}
        return next(iter(layers)) if len(layers) == 1 else None

    @property
    def block_role(self) -> str:
        """Papel do bloco sem o indice de camada: 'attention', 'mlp', 'moe', 'head'..."""
        return self.name.split(".")[-1] if "." in self.name else self.name

    def flops(self, w: Workload) -> float:
        return sum(n.flops(w) for n in self.nodes)

    def bytes_moved(self, w: Workload, weight_precision: str | None = None) -> float:
        return sum(n.bytes_moved(w, weight_precision) for n in self.nodes)

    def weight_elems(self) -> int:
        return sum(n.weight_elems for n in self.nodes)

    @property
    def has_dynamic_control(self) -> bool:
        return any(n.dynamic for n in self.nodes)

    @property
    def dynamic_fraction(self) -> float:
        return sum(1 for n in self.nodes if n.dynamic) / len(self.nodes) if self.nodes else 0.0

    @property
    def data_dependent_fraction(self) -> float:
        if not self.nodes:
            return 0.0
        return sum(1 for n in self.nodes if n.data_dependent_addressing) / len(self.nodes)

    def kinds(self) -> list[OpKind]:
        return [n.kind for n in self.nodes]


__all__ = [
    "OpKind",
    "Phase",
    "Precision",
    "PRECISIONS",
    "precision",
    "Workload",
    "Node",
    "Graph",
    "Subgraph",
    "causal_score_elems",
]
