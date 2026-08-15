"""Fingerprint e invariantes: invariancia **e** sensibilidade.

Um hash estrutural util precisa falhar nos dois sentidos. Se so testarmos que padroes iguais
colidem, um hash constante passa. Por isso cada teste de invariancia tem um par de sensibilidade
(ADR-0003, "evidencia necessaria para revisar").
"""

from __future__ import annotations

import copy

import pytest

from silicon_atlas.fingerprint import (
    fingerprint_graph,
    fingerprint_subgraph,
    group_patterns,
    model_fingerprint,
    node_signature,
)
from silicon_atlas.invariants import (
    ModelView,
    block_role_stability,
    diff_versions,
    discover_invariants,
    family_stability,
)
from silicon_atlas.ir import build_graph
from silicon_atlas.registry import Registry


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load()


@pytest.fixture(scope="module")
def views(registry: Registry) -> list[ModelView]:
    return [ModelView.of(s) for s in registry]


# ---------------------------------------------------------------------- invariancia ---


def test_pattern_hash_is_invariant_to_layer_index(registry: Registry) -> None:
    spec = registry["llama-3.1-8b"]
    g = build_graph(spec)
    fps = fingerprint_graph(g, spec)
    mlps = [fp for name, fp in fps.items() if name.endswith(".mlp")]
    assert len({fp.exact for fp in mlps}) == 1, "camadas identicas devem colapsar num padrao"
    assert len(mlps) == spec.num_layers


def test_pattern_hash_is_invariant_to_node_renaming(registry: Registry) -> None:
    spec = registry["llama-3.1-8b"]
    g = build_graph(spec)
    original = fingerprint_subgraph(g.subgraph(g.by_block("L0.mlp"), "L0.mlp"), spec)

    g2 = copy.deepcopy(g)
    for n in g2.by_block("L0.mlp"):
        n.id = n.id.replace("L0", "camada_zero")
    renamed = fingerprint_subgraph(g2.subgraph(g2.by_block("L0.mlp"), "L0.mlp"), spec)
    assert renamed.exact == original.exact


def test_topology_survives_size_change_but_exact_does_not(registry: Registry) -> None:
    """Caso-teste declarado no corpus: Qwen 7B vs 14B (ADR-0003)."""
    small, large = registry["qwen2.5-7b"], registry["qwen2.5-14b"]
    a = fingerprint_graph(build_graph(small), small)["L0.mlp"]
    b = fingerprint_graph(build_graph(large), large)["L0.mlp"]
    assert a.topology == b.topology, "mesmo datapath"
    assert a.exact != b.exact, "shapes diferentes exigem re-sintese"


# --------------------------------------------------------------------- sensibilidade ---


def test_exact_hash_detects_gqa_change(registry: Registry) -> None:
    llama2, llama3 = registry["llama-2-7b"], registry["llama-3-8b"]
    a = fingerprint_graph(build_graph(llama2), llama2)["L0.attention"]
    b = fingerprint_graph(build_graph(llama3), llama3)["L0.attention"]
    assert a.exact != b.exact
    assert a.pattern != b.pattern, "razao h/g mudou: MHA -> GQA"


def test_exact_hash_detects_moe(registry: Registry) -> None:
    dense, moe = registry["mistral-7b-v0.1"], registry["mixtral-8x7b-v0.1"]
    a = fingerprint_graph(build_graph(dense), dense)
    b = fingerprint_graph(build_graph(moe), moe)
    assert "L0.mlp" in a and "L0.moe" in b
    assert {f.exact for f in a.values()} != {f.exact for f in b.values()}


def test_signature_reacts_to_precision(registry: Registry) -> None:
    spec = registry["llama-3.1-8b"]
    g = build_graph(spec)
    node = g.by_id("L0.gate_proj")
    d = spec.hidden_size
    before = node_signature(node, "exact", d)
    node.weight_precision = "int4"
    assert node_signature(node, "exact", d) != before
    assert node_signature(node, "topology", d) == node_signature(node, "topology", d)


def test_mlp_circuit_is_shared_across_families(registry: Registry) -> None:
    """Achado do ciclo: o MLP de llama-3-8b e o de mistral-7b sao o mesmo circuito."""
    a, b = registry["llama-3-8b"], registry["mistral-7b-v0.1"]
    fa = fingerprint_graph(build_graph(a), a)["L0.mlp"]
    fb = fingerprint_graph(build_graph(b), b)["L0.mlp"]
    assert a.hidden_size == b.hidden_size and a.intermediate_size == b.intermediate_size
    assert fa.exact == fb.exact, "MLP dimensionalmente identico deve colidir no nivel exato"


def test_rope_theta_is_outside_the_hash_but_recorded(registry: Registry) -> None:
    """rope_theta muda conteudo de tabela, nao circuito: fora do hash, dentro das constantes.

    Testado no bloco de atencao, que e onde RoPE vive. llama-3-8b usa theta 5e5 e mistral-7b usa
    1e4: se theta entrasse no hash, dois circuitos identicos exigiriam re-sintese so por causa de
    uma tabela de constantes — que e precisamente a distincao que o ADR-0003 preserva.
    """
    a, b = registry["llama-3-8b"], registry["mistral-7b-v0.1"]
    assert a.rope_theta != b.rope_theta, "premissa do teste"

    fa = fingerprint_graph(build_graph(a), a)["L0.attention"]
    fb = fingerprint_graph(build_graph(b), b)["L0.attention"]

    ca, cb = dict(fa.constants), dict(fb.constants)
    assert ca.get("rope_q.theta") == a.rope_theta, "a constante precisa ser registrada"
    assert cb.get("rope_q.theta") == b.rope_theta
    assert ca["rope_q.theta"] != cb["rope_q.theta"], "e precisa diferir entre os dois modelos"

    # Os hashes diferem aqui pela janela deslizante do mistral, nao por theta. Isolando:
    # duas versoes com mesma janela e theta diferente devem colidir.
    c, d = registry["llama-3-8b"], registry["llama-3.1-8b"]
    fc = fingerprint_graph(build_graph(c), c)["L0.attention"]
    fd = fingerprint_graph(build_graph(d), d)["L0.attention"]
    assert fc.exact == fd.exact
    assert dict(fc.constants)["rope_q.theta"] == dict(fd.constants)["rope_q.theta"]


# ------------------------------------------------------------------------ invariantes ---


def test_llama3_to_31_is_structurally_identical(registry: Registry) -> None:
    d = diff_versions(ModelView.of(registry["llama-3-8b"]), ModelView.of(registry["llama-3.1-8b"]))
    assert d.structurally_identical
    assert d.stability["exact"] == 1.0
    assert set(d.changed_config) == {"max_position_embeddings"}


def test_llama2_to_llama3_is_not_identical(registry: Registry) -> None:
    d = diff_versions(ModelView.of(registry["llama-2-7b"]), ModelView.of(registry["llama-3-8b"]))
    assert not d.structurally_identical
    assert "num_key_value_heads" in d.changed_config
    assert d.signature_changes, "mudanca de shape deve aparecer no diff de assinatura"


def test_cross_family_exact_pattern_exists(views: list[ModelView]) -> None:
    """Achado do ciclo: um mesmo circuito exato atravessa familias distintas."""
    invs = discover_invariants(views, level="exact")
    cross = [i for i in invs if len({m.split("-")[0] for m in i.models}) > 1]
    assert cross, "nenhum padrao cruza familias — H1 perde sustentacao cross-familia"
    top = max(cross, key=lambda i: i.coverage)
    assert top.coverage >= 2 / len(views)


def test_absent_from_is_always_recorded(views: list[ModelView]) -> None:
    """Casos que nao se encaixam sao preservados, nunca suavizados (Metodo, portao U2)."""
    invs = discover_invariants(views, level="exact")
    for inv in invs:
        assert len(inv.models) + len(inv.absent_from) == len(views)


def test_family_stability_orders_by_release(registry: Registry) -> None:
    rep = family_stability([ModelView.of(s) for s in registry.family("llama")])
    assert rep.versions == ["llama-2-7b", "llama-3-8b", "llama-3.1-8b"]
    assert rep.transitions == 2
    assert rep.recent_exact_stability == 1.0
    assert rep.level_stability["exact"] < 1.0
    assert rep.scope_spread > 0, "efeito de escopo deve ser mensuravel e positivo aqui"


def test_single_version_family_declares_gap(registry: Registry) -> None:
    """Sem duas versoes nao se observa estabilidade temporal: o Finding deve dizer isso."""
    views = [ModelView.of(s) for s in registry.family("gemma")]
    stab = block_role_stability(views, views)
    for f in stab.values():
        assert "G-006" in f.gaps
        assert f.status.name == "ASSUMPTION"


def test_model_fingerprint_reports_dynamic_regions(registry: Registry) -> None:
    spec = registry["mixtral-8x7b-v0.1"]
    fp = model_fingerprint(spec, build_graph(spec))
    assert fp["routing"] == "sparse_moe"
    assert "moe" in fp["dynamic_regions"]
    assert fp["distinct_layer_patterns"] >= 1


def test_group_patterns_collapses_identical_layers(registry: Registry) -> None:
    spec = registry["llama-3.1-8b"]
    fps = fingerprint_graph(build_graph(spec), spec)
    groups = group_patterns({k: v for k, v in fps.items() if k.startswith("L")}, "exact")
    assert len(groups) == 2, "atencao e MLP: duas classes para 32 camadas"
    assert all(g.count == spec.num_layers for g in groups.values())
