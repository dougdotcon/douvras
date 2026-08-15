"""Construtor da DOUVRAS IR a partir de ``ModelSpec`` (ADR-0001).

Regra do construtor: **desfazer decisoes de implementacao, preservar decisoes de arquitetura**.
QKV fundido (Phi-3) e gate/up fundido viram nos separados, porque a fusao e escolha de kernel,
nao propriedade do modelo. Ja o numero de normalizacoes por camada (Gemma-2 tem quatro) e
arquitetura e precisa aparecer.
"""

from __future__ import annotations

from ..registry import ModelSpec
from .graph import Graph, Node, OpKind

ATTENTION = "attention"
MLP = "mlp"
MOE = "moe"
EMBEDDING = "embedding"
HEAD = "head"


def attention_window(spec: ModelSpec, layer: int) -> int | None:
    """Janela de atencao efetiva da camada.

    Gemma-2 alterna camadas com janela deslizante e camadas globais; Mistral aplica a
    janela em todas. A distincao muda o regime de memoria do decode, entao pertence a IR.
    """
    if spec.sliding_window is None:
        return None
    if spec.architecture == "Gemma2ForCausalLM":
        return spec.sliding_window if layer % 2 == 0 else None
    return spec.sliding_window


def _act_fn(spec: ModelSpec) -> str:
    return {"swiglu": "silu", "geglu": "gelu", "mlp": "relu"}.get(spec.mlp_type, "silu")


def build_graph(spec: ModelSpec) -> Graph:
    """Constroi o grafo canonico completo (todas as camadas expandidas).

    Expandir todas as camadas custa alguns milhares de nos e paga: hotspots por camada,
    janelas alternadas e diffs posicionais ficam explicitos em vez de inferidos.
    """
    d = spec.hidden_size
    wp = spec.default_dtype
    g = Graph(
        model_id=spec.id,
        meta={
            "family": spec.family,
            "version": spec.version_label,
            "architecture": spec.architecture,
            "num_layers": spec.num_layers,
            "hidden_size": d,
            "attention_type": spec.attention_type,
            "is_moe": spec.is_moe,
            "release_date": spec.release_date,
        },
    )

    g.add(
        Node(
            id="embed",
            kind=OpKind.EMBEDDING,
            role="embed_tokens",
            block=EMBEDDING,
            weight_shape=(spec.vocab_size, d),
            attrs={"width": d, "vocab": spec.vocab_size},
            weight_precision=wp,
            data_dependent_addressing=True,  # gather por id de token
        )
    )

    prev = "embed"
    for i in range(spec.num_layers):
        prev = _build_layer(g, spec, i, prev)

    g.add(
        Node(
            id="final_norm",
            kind=OpKind.NORM,
            role="final_norm",
            block=HEAD,
            weight_shape=(d,),
            inputs=(prev,),
            attrs={"width": d, "norm": spec.norm_type},
            weight_precision=wp,
        )
    )
    g.add(
        Node(
            id="lm_head",
            kind=OpKind.LINEAR,
            role="lm_head",
            block=HEAD,
            weight_shape=(d, spec.vocab_size),
            inputs=("final_norm",),
            # Embeddings amarrados: a tabela ja esta residente via `embed`, mas continua
            # sendo lida aqui. resident_count=0 evita contagem dupla de footprint.
            resident_count=0 if spec.tie_word_embeddings else 1,
            attrs={
                "in_features": d,
                "out_features": spec.vocab_size,
                "scope": "last_token",
                "tied": spec.tie_word_embeddings,
            },
            weight_precision=wp,
        )
    )
    if spec.raw_config.get("final_logit_softcapping"):
        g.add(
            Node(
                id="logit_cap",
                kind=OpKind.LOGIT_CAP,
                role="final_logit_softcapping",
                block=HEAD,
                inputs=("lm_head",),
                attrs={"width": spec.vocab_size, "scope": "last_token"},
            )
        )
    g.add(
        Node(
            id="sampling",
            kind=OpKind.SAMPLING,
            role="sampling",
            block=HEAD,
            inputs=("lm_head",),
            attrs={"width": spec.vocab_size, "scope": "last_token"},
            dynamic=True,  # politica de amostragem muda em runtime
        )
    )
    return g


def _build_layer(g: Graph, spec: ModelSpec, i: int, prev: str) -> str:
    d = spec.hidden_size
    wp = spec.default_dtype
    p = f"L{i}"
    ab = f"{p}.{ATTENTION}"
    window = attention_window(spec, i)
    gemma_style = spec.norms_per_layer == 4

    # ---- normalizacao de entrada da atencao ----
    g.add(
        Node(
            f"{p}.attn_norm",
            OpKind.NORM,
            "input_layernorm",
            ab,
            i,
            weight_shape=(d,),
            inputs=(prev,),
            attrs={"width": d, "norm": spec.norm_type},
            weight_precision=wp,
        )
    )

    # ---- projecoes Q, K, V ----
    for role, out_dim, bias_elems in (
        ("q_proj", spec.q_dim, spec.q_dim if spec.qkv_bias else 0),
        ("k_proj", spec.kv_dim, spec.kv_dim if spec.qkv_bias else 0),
        ("v_proj", spec.kv_dim, spec.kv_dim if spec.qkv_bias else 0),
    ):
        g.add(
            Node(
                f"{p}.{role}",
                OpKind.LINEAR,
                role,
                ab,
                i,
                weight_shape=(d, out_dim),
                bias=bias_elems,
                inputs=(f"{p}.attn_norm",),
                attrs={"in_features": d, "out_features": out_dim},
                weight_precision=wp,
            )
        )

    # ---- RoPE em Q e K ----
    for role, width, src in (
        ("rope_q", spec.q_dim, "q_proj"),
        ("rope_k", spec.kv_dim, "k_proj"),
    ):
        g.add(
            Node(
                f"{p}.{role}",
                OpKind.ROPE,
                role,
                ab,
                i,
                inputs=(f"{p}.{src}",),
                attrs={"width": width, "theta": spec.rope_theta},
            )
        )

    # ---- KV cache ----
    kv_attrs = {"kv_dim": spec.kv_dim, "window": window, "kv_precision": wp}
    g.add(
        Node(f"{p}.kv_write", OpKind.KV_WRITE, "kv_write", ab, i,
             inputs=(f"{p}.rope_k", f"{p}.v_proj"), attrs=dict(kv_attrs))
    )
    g.add(
        Node(f"{p}.kv_read", OpKind.KV_READ, "kv_read", ab, i,
             inputs=(f"{p}.kv_write",), attrs=dict(kv_attrs))
    )

    # ---- nucleo de atencao ----
    core = {
        "heads": spec.num_heads,
        "head_dim": spec.head_dim,
        "kv_heads": spec.num_kv_heads,
        "window": window,
        "materialize_scores": False,  # premissa A-002: atencao com tiling
        "causal": True,
    }
    g.add(Node(f"{p}.attn_scores", OpKind.ATTN_SCORES, "qk", ab, i,
               inputs=(f"{p}.rope_q", f"{p}.kv_read"), attrs=dict(core)))
    if spec.raw_config.get("attn_logit_softcapping"):
        g.add(Node(f"{p}.attn_cap", OpKind.LOGIT_CAP, "attn_logit_softcapping", ab, i,
                   inputs=(f"{p}.attn_scores",),
                   attrs={"width": spec.num_heads * spec.head_dim}))
    g.add(Node(f"{p}.attn_softmax", OpKind.ATTN_SOFTMAX, "softmax", ab, i,
               inputs=(f"{p}.attn_scores",), attrs=dict(core)))
    g.add(Node(f"{p}.attn_context", OpKind.ATTN_CONTEXT, "pv", ab, i,
               inputs=(f"{p}.attn_softmax", f"{p}.kv_read"), attrs=dict(core)))
    g.add(
        Node(f"{p}.o_proj", OpKind.LINEAR, "o_proj", ab, i,
             weight_shape=(spec.q_dim, d),
             bias=d if spec.o_bias else 0,
             inputs=(f"{p}.attn_context",),
             attrs={"in_features": spec.q_dim, "out_features": d},
             weight_precision=wp)
    )

    tail = f"{p}.o_proj"
    if gemma_style:
        g.add(Node(f"{p}.post_attn_norm", OpKind.NORM, "post_attention_layernorm", ab, i,
                   weight_shape=(d,), inputs=(tail,),
                   attrs={"width": d, "norm": spec.norm_type}, weight_precision=wp))
        tail = f"{p}.post_attn_norm"
    g.add(Node(f"{p}.attn_residual", OpKind.RESIDUAL, "residual_add", ab, i,
               inputs=(prev, tail), attrs={"width": d}))

    # ---- bloco MLP / MoE ----
    mb = f"{p}.{MOE if spec.is_moe else MLP}"
    g.add(Node(f"{p}.mlp_norm", OpKind.NORM,
               "pre_feedforward_layernorm" if gemma_style else "post_attention_layernorm",
               mb, i, weight_shape=(d,), inputs=(f"{p}.attn_residual",),
               attrs={"width": d, "norm": spec.norm_type}, weight_precision=wp))

    if spec.is_moe:
        last = _build_moe(g, spec, i, mb, f"{p}.mlp_norm")
    else:
        last = _build_dense_mlp(g, spec, i, mb, f"{p}.mlp_norm")

    if gemma_style:
        g.add(Node(f"{p}.post_mlp_norm", OpKind.NORM, "post_feedforward_layernorm", mb, i,
                   weight_shape=(d,), inputs=(last,),
                   attrs={"width": d, "norm": spec.norm_type}, weight_precision=wp))
        last = f"{p}.post_mlp_norm"

    out = f"{p}.mlp_residual"
    g.add(Node(out, OpKind.RESIDUAL, "residual_add", mb, i,
               inputs=(f"{p}.attn_residual", last), attrs={"width": d}))
    return out


def _build_dense_mlp(g: Graph, spec: ModelSpec, i: int, block: str, src: str) -> str:
    d, I = spec.hidden_size, spec.intermediate_size
    p = f"L{i}"
    wp = spec.default_dtype
    glu = spec.mlp_gates == 2

    if glu:
        g.add(Node(f"{p}.gate_proj", OpKind.LINEAR, "gate_proj", block, i,
                   weight_shape=(d, I), bias=I if spec.mlp_bias else 0, inputs=(src,),
                   attrs={"in_features": d, "out_features": I}, weight_precision=wp))
    g.add(Node(f"{p}.up_proj", OpKind.LINEAR, "up_proj", block, i,
               weight_shape=(d, I), bias=I if spec.mlp_bias else 0, inputs=(src,),
               attrs={"in_features": d, "out_features": I}, weight_precision=wp))
    g.add(Node(f"{p}.mlp_act", OpKind.ACTIVATION, "act", block, i,
               inputs=(f"{p}.gate_proj" if glu else f"{p}.up_proj",),
               attrs={"width": I, "fn": _act_fn(spec)}))
    if glu:
        g.add(Node(f"{p}.mlp_mul", OpKind.ELEMENTWISE, "glu_mul", block, i,
                   inputs=(f"{p}.mlp_act", f"{p}.up_proj"), attrs={"width": I, "op": "mul"}))
    g.add(Node(f"{p}.down_proj", OpKind.LINEAR, "down_proj", block, i,
               weight_shape=(I, d), bias=d if spec.mlp_bias else 0,
               inputs=(f"{p}.mlp_mul" if glu else f"{p}.mlp_act",),
               attrs={"in_features": I, "out_features": d}, weight_precision=wp))
    return f"{p}.down_proj"


def _build_moe(g: Graph, spec: ModelSpec, i: int, block: str, src: str) -> str:
    """MoE: FLOPs de top-k, footprint de todos os experts.

    A separacao active/resident e o ponto do bloco. Um MoE parece barato em FLOPs e e caro
    em memoria e em previsibilidade de acesso — exatamente o perfil que NAO deve ser endurecido.
    """
    assert spec.moe is not None
    m = spec.moe
    d, I = spec.hidden_size, m.expert_intermediate_size
    p = f"L{i}"
    wp = spec.default_dtype
    glu = spec.mlp_gates == 2

    g.add(Node(f"{p}.router", OpKind.ROUTER, "router", block, i,
               weight_shape=(d, m.num_experts), inputs=(src,),
               attrs={"in_features": d, "out_features": m.num_experts,
                      "top_k": m.experts_per_token},
               weight_precision=wp, dynamic=True, data_dependent_addressing=True))
    g.add(Node(f"{p}.dispatch", OpKind.DISPATCH, "expert_dispatch", block, i,
               inputs=(f"{p}.router", src), attrs={"width": d},
               active_count=m.experts_per_token,
               dynamic=True, data_dependent_addressing=True))

    common = dict(
        active_count=m.experts_per_token,
        resident_count=m.num_experts,
        weight_precision=wp,
        data_dependent_addressing=True,
    )
    if glu:
        g.add(Node(f"{p}.expert_gate", OpKind.LINEAR, "expert_gate_proj", block, i,
                   weight_shape=(d, I), inputs=(f"{p}.dispatch",),
                   attrs={"in_features": d, "out_features": I}, **common))
    g.add(Node(f"{p}.expert_up", OpKind.LINEAR, "expert_up_proj", block, i,
               weight_shape=(d, I), inputs=(f"{p}.dispatch",),
               attrs={"in_features": d, "out_features": I}, **common))
    g.add(Node(f"{p}.expert_act", OpKind.ACTIVATION, "act", block, i,
               inputs=(f"{p}.expert_gate" if glu else f"{p}.expert_up",),
               attrs={"width": I, "fn": _act_fn(spec)},
               active_count=m.experts_per_token))
    if glu:
        g.add(Node(f"{p}.expert_mul", OpKind.ELEMENTWISE, "glu_mul", block, i,
                   inputs=(f"{p}.expert_act", f"{p}.expert_up"),
                   attrs={"width": I, "op": "mul"}, active_count=m.experts_per_token))
    g.add(Node(f"{p}.expert_down", OpKind.LINEAR, "expert_down_proj", block, i,
               weight_shape=(I, d),
               inputs=(f"{p}.expert_mul" if glu else f"{p}.expert_act",),
               attrs={"in_features": I, "out_features": d}, **common))
    g.add(Node(f"{p}.expert_combine", OpKind.ELEMENTWISE, "expert_combine", block, i,
               inputs=(f"{p}.expert_down", f"{p}.router"),
               attrs={"width": d, "op": "weighted_sum"},
               active_count=m.experts_per_token,
               dynamic=True, data_dependent_addressing=True))
    return f"{p}.expert_combine"


__all__ = ["build_graph", "attention_window"]
