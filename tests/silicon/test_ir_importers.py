"""`ir.importers` — auditoria da IR analitica contra pesos reais (`ADR-0001`, `G-001`).

Testado sem `torch` nem checkpoint: `audit_against_real_weights` recebe as shapes reais como
`dict` puro, exatamente para que esta suite rode em segundos e sem depender de rede ou peso.
"""

from __future__ import annotations

import pytest

from silicon_atlas.ir import build_graph
from silicon_atlas.ir.importers import audit_against_real_weights
from silicon_atlas.registry import Registry


@pytest.fixture(scope="module")
def spec():
    reg = Registry.load()
    return reg["smollm2-360m-instruct"]


@pytest.fixture(scope="module")
def graph(spec):
    return build_graph(spec)


def _shapes_reais_perfeitas(spec) -> dict[str, tuple[int, ...]]:
    """Reconstroi exatamente as shapes que um checkpoint Llama-family real teria,
    a partir do proprio `spec` — o "gabarito" com o qual a IR foi construida."""
    d, kv, q = spec.hidden_size, spec.kv_dim, spec.q_dim
    intermediate = spec.intermediate_size
    shapes: dict[str, tuple[int, ...]] = {
        "model.embed_tokens.weight": (spec.vocab_size, d),
        "model.norm.weight": (d,),
    }
    if not spec.tie_word_embeddings:
        shapes["lm_head.weight"] = (spec.vocab_size, d)
    for i in range(spec.num_layers):
        p = f"model.layers.{i}"
        shapes[f"{p}.input_layernorm.weight"] = (d,)
        shapes[f"{p}.post_attention_layernorm.weight"] = (d,)
        shapes[f"{p}.self_attn.q_proj.weight"] = (q, d)
        shapes[f"{p}.self_attn.k_proj.weight"] = (kv, d)
        shapes[f"{p}.self_attn.v_proj.weight"] = (kv, d)
        shapes[f"{p}.self_attn.o_proj.weight"] = (d, q)
        shapes[f"{p}.mlp.gate_proj.weight"] = (intermediate, d)
        shapes[f"{p}.mlp.up_proj.weight"] = (intermediate, d)
        shapes[f"{p}.mlp.down_proj.weight"] = (d, intermediate)
    return shapes


def test_checkpoint_identico_ao_gabarito_nao_tem_divergencia(spec, graph) -> None:
    aud = audit_against_real_weights(graph, _shapes_reais_perfeitas(spec), spec.id)
    assert aud.clean, aud.as_dict()
    assert aud.ir_orphans == []
    assert aud.real_orphans == []
    assert aud.shape_divergences == []
    assert aud.matched == aud.ir_nodes_with_weight
    assert aud.elem_count_divergence_pct < 1e-6


def test_embeddings_amarrados_nao_viram_falso_orfao(spec, graph) -> None:
    """`smollm2-360m-instruct` tem `tie_word_embeddings=True`: nao existe `lm_head.weight`
    separado no checkpoint real, e isso NAO pode aparecer como "operador ausente"."""
    assert spec.tie_word_embeddings is True
    shapes = _shapes_reais_perfeitas(spec)
    assert "lm_head.weight" not in shapes
    aud = audit_against_real_weights(graph, shapes, spec.id)
    assert "lm_head" not in aud.ir_orphans
    assert aud.clean, aud.as_dict()


def test_parametro_real_ausente_do_checkpoint_e_orfao_da_ir(spec, graph) -> None:
    """Um no da IR sem contrapartida real e exatamente 'operador ausente invalida o perfil'."""
    shapes = _shapes_reais_perfeitas(spec)
    del shapes["model.layers.0.self_attn.q_proj.weight"]
    aud = audit_against_real_weights(graph, shapes, spec.id)
    assert "L0.q_proj" in aud.ir_orphans
    assert not aud.clean


def test_parametro_real_sem_contrapartida_na_ir_e_orfao_real(spec, graph) -> None:
    """O inverso: o checkpoint tem um tensor que a IR nunca imaginou."""
    shapes = _shapes_reais_perfeitas(spec)
    shapes["model.layers.0.self_attn.q_norm.weight"] = (spec.head_dim,)
    aud = audit_against_real_weights(graph, shapes, spec.id)
    assert "model.layers.0.self_attn.q_norm.weight" in aud.real_orphans
    assert not aud.clean


def test_shape_errada_e_divergencia_nao_orfao(spec, graph) -> None:
    """Uma shape diferente da esperada e um problema mais especifico que 'ausente' —
    o modulo existe, mas a IR modelou a dimensao errada."""
    shapes = _shapes_reais_perfeitas(spec)
    errada = (spec.kv_dim, spec.hidden_size)  # shape de k_proj, propositalmente errada p/ q_proj
    assert errada != (spec.q_dim, spec.hidden_size), "o teste exige uma shape genuinamente diferente"
    shapes["model.layers.0.self_attn.q_proj.weight"] = errada
    aud = audit_against_real_weights(graph, shapes, spec.id)
    assert len(aud.shape_divergences) == 1
    div = aud.shape_divergences[0]
    assert div.node_id == "L0.q_proj"
    assert div.real_shape == errada
    assert "L0.q_proj" not in aud.ir_orphans, "shape errada nao e a mesma coisa que ausente"


def test_linear_inverte_shape_mas_embedding_nao(spec, graph) -> None:
    """`nn.Linear.weight` real e (out, in); a IR guarda (in, out). `nn.Embedding.weight` e
    (vocab, d) nos dois lados. Inverter os dois do mesmo jeito produziria falso positivo
    exatamente no no de embedding."""
    shapes = _shapes_reais_perfeitas(spec)
    aud = audit_against_real_weights(graph, shapes, spec.id)
    assert not any(d.node_id == "embed" for d in aud.shape_divergences), aud.as_dict()


def test_contagem_de_parametros_bate_com_o_gabarito(spec, graph) -> None:
    aud = audit_against_real_weights(graph, _shapes_reais_perfeitas(spec), spec.id)
    assert aud.real_total_elems == spec.published_params
    assert aud.ir_total_elems == spec.published_params
