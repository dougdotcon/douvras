"""Testes-ouro da DOUVRAS IR — evidencia E-001, alegacao C-007.

Estes testes existem para **falsificar** a IR, nao para exibi-la. A contagem de parametros
publicada pelos autores de cada modelo e um numero que nao controlamos: se a IR estiver errada
em qualquer detalhe (GQA, bias, embeddings amarrados, numero de normalizacoes, MoE), ela nao
bate. Bater em nove modelos de cinco familias com erro zero e a evidencia mais forte disponivel
sem baixar pesos.
"""

from __future__ import annotations

import pytest

from silicon_atlas.ir import build_graph
from silicon_atlas.ir.graph import OpKind, Phase, Workload
from silicon_atlas.registry import Registry, corpus_integrity


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load()


def test_corpus_loads_without_errors(registry: Registry) -> None:
    assert len(registry) >= 9
    assert registry.errors == {}, f"modelos rejeitados: {registry.errors}"


@pytest.mark.falsifier
def test_param_count_matches_published(registry: Registry) -> None:
    """F5 — erro acima de 5% invalida todo resultado a jusante.

    Alvo declarado na PROBLEM_CHARTER (M1): erro < 0.5%.
    """
    for spec in registry:
        if not spec.published_params:
            continue
        derived = spec.param_count()
        err = abs(derived - spec.published_params) / spec.published_params
        assert err < 5e-3, (
            f"{spec.id}: derivado {derived:,} vs publicado {spec.published_params:,} "
            f"(erro {err:.4%}) — F5 disparado, IR nao representa o modelo"
        )


def test_graph_weight_sum_equals_spec(registry: Registry) -> None:
    """O grafo e o spec devem concordar ao parametro: sao dois caminhos para o mesmo numero."""
    for spec in registry:
        g = build_graph(spec)
        assert g.total_weight_elems() == spec.param_count(), (
            f"{spec.id}: grafo {g.total_weight_elems():,} != spec {spec.param_count():,}"
        )


def test_corpus_integrity_finding(registry: Registry) -> None:
    f = corpus_integrity(registry)
    assert f.value < 5e-3
    assert f.status.name == "COMPUTATIONAL_EVIDENCE"


# --------------------------------------------------------------------------------------
# Propriedades estruturais que arquiteturas especificas obrigam
# --------------------------------------------------------------------------------------


def test_gqa_reduces_kv_dimension(registry: Registry) -> None:
    llama2, llama3 = registry["llama-2-7b"], registry["llama-3-8b"]
    assert llama2.attention_type == "mha" and llama2.kv_dim == llama2.q_dim
    assert llama3.attention_type == "gqa" and llama3.kv_dim == llama3.q_dim // 4


def test_gemma2_has_four_norms_per_layer(registry: Registry) -> None:
    """Gemma-2 e o contraexemplo do corpus: quebra o template llama se ele for assumido."""
    spec = registry["gemma-2-9b"]
    g = build_graph(spec)
    norms = [n for n in g.layer_nodes(0) if n.kind is OpKind.NORM]
    assert len(norms) == 4, [n.role for n in norms]
    assert spec.head_dim * spec.num_heads != spec.hidden_size  # 16 x 256 != 3584
    assert spec.tie_word_embeddings


def test_gemma2_alternates_sliding_window(registry: Registry) -> None:
    g = build_graph(registry["gemma-2-9b"])
    windows = [
        n.attrs["window"] for n in g if n.kind is OpKind.ATTN_SCORES and n.layer in (0, 1, 2, 3)
    ]
    assert windows == [4096, None, 4096, None], windows


def test_tied_embeddings_are_not_counted_twice(registry: Registry) -> None:
    g = build_graph(registry["gemma-2-9b"])
    head = g.by_id("lm_head")
    assert head.resident_count == 0, "cabeca amarrada nao pode adicionar footprint"
    assert head.active_weight_elems > 0, "mas continua sendo lida durante o calculo"


def test_moe_separates_active_from_resident(registry: Registry) -> None:
    """A distincao que torna MoE barata em FLOPs e cara em memoria."""
    g = build_graph(registry["mixtral-8x7b-v0.1"])
    expert = g.by_id("L0.expert_up")
    assert expert.active_count == 2 and expert.resident_count == 8
    assert expert.weight_elems == 4 * expert.active_weight_elems
    router = g.by_id("L0.router")
    assert router.dynamic and router.data_dependent_addressing


def test_qwen_has_qkv_bias_and_no_o_bias(registry: Registry) -> None:
    g = build_graph(registry["qwen2.5-7b"])
    assert g.by_id("L0.q_proj").bias > 0
    assert g.by_id("L0.o_proj").bias == 0


# --------------------------------------------------------------------------------------
# Custo: propriedades que a aritmetica obriga
# --------------------------------------------------------------------------------------


def test_prefill_flops_match_closed_form(registry: Registry) -> None:
    """Prefill de um denso deve ficar proximo de 2*P*tokens, sem a cabeca de logits."""
    spec = registry["llama-3.1-8b"]
    g = build_graph(spec)
    w = Workload(phase=Phase.PREFILL, batch=1, prompt_len=512)
    body = sum(n.flops(w) for n in g if n.block != "head" and n.block != "embedding")
    non_embed = spec.param_count() - 2 * spec.vocab_size * spec.hidden_size
    expected = 2.0 * non_embed * w.tokens
    assert 0.9 < body / expected < 1.35, body / expected


def test_lm_head_only_runs_on_last_token_in_prefill(registry: Registry) -> None:
    g = build_graph(registry["llama-3.1-8b"])
    head = g.by_id("lm_head")
    long_prompt = Workload(phase=Phase.PREFILL, batch=1, prompt_len=4096)
    short_prompt = Workload(phase=Phase.PREFILL, batch=1, prompt_len=8)
    assert head.flops(long_prompt) == head.flops(short_prompt)


def test_embedding_gather_reads_one_row_not_the_table(registry: Registry) -> None:
    """Um gather le a linha do token. Contar a tabela inteira inflaria o decode em ~1 GB."""
    g = build_graph(registry["llama-3.1-8b"])
    emb = g.by_id("embed")
    w = Workload(phase=Phase.DECODE, batch=1, context_len=2048)
    read = emb.read_weight_bytes(w)
    assert read == pytest.approx(4096 * 2)  # hidden_size x bf16
    assert read < emb.weight_bytes() / 1000


def test_decode_attention_scales_with_context(registry: Registry) -> None:
    g = build_graph(registry["llama-3.1-8b"])
    node = g.by_id("L0.kv_read")
    short = node.state_bytes(Workload(phase=Phase.DECODE, context_len=1024))
    long = node.state_bytes(Workload(phase=Phase.DECODE, context_len=8192))
    assert long == pytest.approx(8 * short)


def test_sliding_window_caps_kv_traffic(registry: Registry) -> None:
    g = build_graph(registry["mistral-7b-v0.1"])
    node = g.by_id("L0.kv_read")
    w_small = Workload(phase=Phase.DECODE, context_len=4096)
    w_large = Workload(phase=Phase.DECODE, context_len=32768)
    assert node.state_bytes(w_large) == pytest.approx(node.state_bytes(w_small))


def test_unsupported_architecture_fails_loudly() -> None:
    from silicon_atlas.registry import UnsupportedArchitecture, normalize_config

    with pytest.raises(UnsupportedArchitecture):
        normalize_config(
            {"architectures": ["MambaForCausalLM"], "hidden_size": 1, "num_hidden_layers": 1,
             "num_attention_heads": 1, "intermediate_size": 1, "vocab_size": 1},
            {"id": "x", "family": "y"},
        )
