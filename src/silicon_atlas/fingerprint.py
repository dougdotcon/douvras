"""Structural Fingerprint Engine (Metodo 12.3).

Tres niveis de identidade, porque "o mesmo bloco" significa tres coisas diferentes para quem
projeta hardware (ADR-0003, emenda):

``topology``  mesma topologia de operadores e papeis  -> mesmo *datapath*
``pattern``   topologia + mesmas proporcoes de shape  -> mesma microarquitetura, outra escala
``exact``     shapes absolutos e precisao identicos   -> mesmo circuito, sem re-sintese

Confundir os tres e a origem do otimismo em roadmaps de silicio: "Transformers sao estaveis"
e verdade no nivel de topologia e frequentemente falso no nivel exato.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .ir.graph import Graph, Node, OpKind, Subgraph
from .registry import ModelSpec


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _ratio(x: float, d: float) -> str:
    return f"{x / d:.6g}" if d else "0"


def _flags(n: Node) -> str:
    f = []
    if n.dynamic:
        f.append("dyn")
    if n.data_dependent_addressing:
        f.append("dda")
    if n.active_count != n.resident_count:
        f.append(f"sparse{n.active_count}/{n.resident_count}")
    elif n.active_count > 1:
        f.append(f"x{n.active_count}")
    return ",".join(f)


def node_signature(n: Node, level: str, d: int) -> str:
    """Assinatura canonica de um no no nivel pedido."""
    base = f"{n.kind.value}|{n.role}|{_flags(n)}"
    if level == "topology":
        return base

    a = n.attrs
    if level == "pattern":
        parts = [base]
        if n.weight_shape:
            parts.append("w=" + "x".join(_ratio(x, d) for x in n.weight_shape))
        for key in ("in_features", "out_features", "width"):
            if key in a:
                parts.append(f"{key}={_ratio(a[key], d)}")
        if "head_dim" in a:
            parts.append(f"hd={_ratio(a['head_dim'], d)}")
            parts.append(f"gqa={a['heads'] / max(a.get('kv_heads', a['heads']), 1):.4g}")
        if a.get("window"):
            parts.append("windowed")
        return "|".join(parts)

    # exact
    parts = [base, f"prec={n.weight_precision}"]
    if n.weight_shape:
        parts.append("w=" + "x".join(str(x) for x in n.weight_shape))
    if n.bias:
        parts.append(f"bias={n.bias}")
    for key in ("in_features", "out_features", "width", "heads", "head_dim", "kv_heads",
                "kv_dim", "window", "top_k", "vocab"):
        if key in a and a[key] is not None:
            parts.append(f"{key}={a[key]}")
    return "|".join(parts)


@dataclass(frozen=True)
class Fingerprint:
    """Identidade de um subgrafo nos tres niveis, mais os dados para explicar diferencas."""

    topology: str
    pattern: str
    exact: str
    role: str
    num_nodes: int
    signature: str = field(repr=False, default="")
    constants: tuple[tuple[str, Any], ...] = ()

    def level(self, name: str) -> str:
        return {"topology": self.topology, "pattern": self.pattern, "exact": self.exact}[name]

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "topology": self.topology,
            "pattern": self.pattern,
            "exact": self.exact,
            "num_nodes": self.num_nodes,
            "constants": dict(self.constants),
        }


#: Constantes que mudam conteudo de ROM/LUT mas nao o circuito. Ficam fora dos hashes
#: e aparecem no diff — sao a diferenca entre "re-sintetizar" e "regravar uma tabela".
CONSTANT_KEYS = ("theta", "norm", "fn", "causal")


def fingerprint_subgraph(sg: Subgraph, spec: ModelSpec) -> Fingerprint:
    d = spec.hidden_size
    nodes = sg.nodes
    sigs = {lvl: [node_signature(n, lvl, d) for n in nodes] for lvl in ("topology", "pattern", "exact")}
    consts: dict[str, Any] = {}
    for n in nodes:
        for k in CONSTANT_KEYS:
            if k in n.attrs and n.attrs[k] is not None:
                consts.setdefault(f"{n.role}.{k}", n.attrs[k])
    return Fingerprint(
        topology=_h("\n".join(sigs["topology"])),
        pattern=_h("\n".join(sigs["pattern"])),
        exact=_h("\n".join(sigs["exact"])),
        role=sg.block_role,
        num_nodes=len(nodes),
        signature="\n".join(sigs["pattern"]),
        constants=tuple(sorted(consts.items())),
    )


def fingerprint_graph(graph: Graph, spec: ModelSpec) -> dict[str, Fingerprint]:
    """Fingerprint por bloco do grafo, indexado pelo nome do bloco."""
    return {sg.name: fingerprint_subgraph(sg, spec) for sg in graph.block_subgraphs()}


@dataclass
class PatternInstances:
    """Um padrao e todas as suas instancias dentro de um modelo."""

    fingerprint: Fingerprint
    blocks: list[str]
    level: str

    @property
    def count(self) -> int:
        return len(self.blocks)

    @property
    def key(self) -> str:
        return self.fingerprint.level(self.level)


def group_patterns(
    fps: dict[str, Fingerprint], level: str = "exact"
) -> dict[str, PatternInstances]:
    """Agrupa blocos por identidade no nivel pedido.

    Em um Transformer bem-comportado, 32 blocos de MLP colapsam em 1 padrao com 32 instancias.
    Quando nao colapsam, ha heterogeneidade estrutural — e isso e um achado, nao um detalhe.
    """
    out: dict[str, PatternInstances] = {}
    for name, fp in fps.items():
        key = fp.level(level)
        if key in out:
            out[key].blocks.append(name)
        else:
            out[key] = PatternInstances(fingerprint=fp, blocks=[name], level=level)
    return out


def model_fingerprint(spec: ModelSpec, graph: Graph) -> dict[str, Any]:
    """Fingerprint arquitetural do modelo (formato do Metodo 12.3, estendido)."""
    fps = fingerprint_graph(graph, spec)
    dynamic_regions = sorted({n.block.split(".")[-1] for n in graph if n.dynamic})
    quant_candidates = ["int8"]
    if spec.hidden_size >= 2048:
        quant_candidates.append("int4")
    if not spec.is_moe:
        quant_candidates.append("ternary")

    layer_patterns = group_patterns(
        {k: v for k, v in fps.items() if k.startswith("L")}, level="exact"
    )
    return {
        "model": spec.id,
        "family": spec.family,
        "version": spec.version_label,
        "release_date": spec.release_date,
        "architecture_class": "decoder_transformer",
        "attention": spec.attention_type,
        "gqa_ratio": spec.gqa_ratio,
        "head_dim": spec.head_dim,
        "layers": spec.num_layers,
        "hidden_size": spec.hidden_size,
        "intermediate_size": spec.intermediate_size,
        "mlp": spec.mlp_type,
        "mlp_ratio": round(spec.intermediate_size / spec.hidden_size, 4),
        "normalization": spec.norm_type,
        "norms_per_layer": spec.norms_per_layer,
        "position": spec.position_type,
        "rope_theta": spec.rope_theta,
        "routing": "sparse_moe" if spec.is_moe else "dense",
        "vocab_size": spec.vocab_size,
        "tied_embeddings": spec.tie_word_embeddings,
        "sliding_window": spec.sliding_window,
        "params": spec.param_count(),
        "quantization_candidates": quant_candidates,
        "dynamic_regions": dynamic_regions,
        "distinct_layer_patterns": len(layer_patterns),
        "blocks": {k: v.as_dict() for k, v in sorted(fps.items())},
    }


def fingerprint_json(spec: ModelSpec, graph: Graph, indent: int = 2) -> str:
    return json.dumps(model_fingerprint(spec, graph), indent=indent, ensure_ascii=False)


def signature_diff(a: Fingerprint, b: Fingerprint) -> list[str]:
    """Diferencas linha a linha entre duas assinaturas de padrao (para o relatorio de diff)."""
    import difflib

    return [
        line
        for line in difflib.unified_diff(
            a.signature.splitlines(), b.signature.splitlines(), lineterm="", n=0
        )
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]


__all__ = [
    "Fingerprint",
    "PatternInstances",
    "fingerprint_subgraph",
    "fingerprint_graph",
    "group_patterns",
    "model_fingerprint",
    "fingerprint_json",
    "node_signature",
    "signature_diff",
]
