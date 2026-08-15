"""Bordas, determinismo e degradacao graciosa.

O sistema precisa falhar de forma previsivel nas entradas que a operacao real produz: corpus com
um unico modelo, familia sem historico, arquitetura desconhecida, contexto maior que a janela,
particao vazia. Um sistema que so funciona no caminho feliz nao e auditavel.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from silicon_atlas.assessment import Assessment, AssessmentInputs
from silicon_atlas.economics import EconomicsPriors, build_design_point, simulate
from silicon_atlas.hardware import get_device, load_devices
from silicon_atlas.invariants import ModelView, block_role_stability, discover_invariants, family_stability
from silicon_atlas.ir import build_graph
from silicon_atlas.ir.graph import PRECISIONS, Phase, Workload, precision
from silicon_atlas.partition import Partition, Region, partition
from silicon_atlas.profiler import profile, serving_profile
from silicon_atlas.quantization import QuantPriors, evaluate_plan, uniform_plan
from silicon_atlas.readiness import Weights, sensitivity
from silicon_atlas.registry import Registry, UnsupportedArchitecture, verify_spec
from douvras_core.paths import REPO_ROOT, project_root
from douvras_core.status import FindingSet, Finding, Status

#: Raiz do projeto (corpus, priors, fases DOUVRAS) e raiz do monorepo (onde vive `src/`).
#: Depois da extracao do core os dois deixaram de coincidir, e confundi-los faz um subprocesso
#: falhar por nao encontrar o pacote em vez de por aquilo que o teste investiga.
PROJECT = project_root("silicon-atlas")


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load()


@pytest.fixture(scope="module")
def device():
    return get_device("h100-sxm")


# ------------------------------------------------------------------------- corpus ---


def test_single_model_corpus(tmp_path: Path, registry: Registry) -> None:
    """Um corpus de um modelo so nao pode quebrar — e nao pode fingir ter historico."""
    src = PROJECT / "corpus" / "models" / "gemma-2-9b.json"
    (tmp_path / "gemma-2-9b.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    reg = Registry.load(tmp_path)
    assert len(reg) == 1
    views = [ModelView.of(s) for s in reg]

    rep = family_stability(views)
    assert rep.transitions == 0
    assert rep.recent_exact_stability is None
    assert rep.change_rate_per_year is None
    assert rep.scope_spread is None

    stab = block_role_stability(views, views)
    for f in stab.values():
        assert f.status is Status.ASSUMPTION
        assert "G-006" in f.gaps, "sem historico, a estabilidade temporal precisa virar lacuna"


def test_empty_corpus_does_not_crash(tmp_path: Path) -> None:
    reg = Registry.load(tmp_path)
    assert len(reg) == 0
    assert reg.families() == []
    assert discover_invariants([]) == []
    with pytest.raises(KeyError, match="nao registrado"):
        reg["qualquer-coisa"]


def test_unsupported_architecture_is_recorded_not_silently_dropped(tmp_path: Path) -> None:
    (tmp_path / "mamba.json").write_text(
        json.dumps({
            "douvras": {"id": "mamba-x", "family": "mamba"},
            "config": {
                "architectures": ["MambaForCausalLM"], "hidden_size": 2048,
                "num_hidden_layers": 24, "num_attention_heads": 16,
                "intermediate_size": 4096, "vocab_size": 50280,
            },
        }),
        encoding="utf-8",
    )
    reg = Registry.load(tmp_path)
    assert len(reg) == 0
    assert "mamba-x" in reg.errors
    assert "MambaForCausalLM" in reg.errors["mamba-x"]


def test_model_without_published_params_still_renders(registry: Registry, tmp_path: Path) -> None:
    """published_params ausente nao pode quebrar formatacao do relatorio."""
    src = PROJECT / "corpus" / "models" / "llama-3.1-8b.json"
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc["douvras"]["published_params"] = None
    doc["douvras"]["id"] = "sem-params"
    (tmp_path / "sem-params.json").write_text(json.dumps(doc), encoding="utf-8")

    reg = Registry.load(tmp_path)
    spec = reg["sem-params"]
    assert spec.published_params is None
    assert spec.param_count() > 0
    a = Assessment.build(AssessmentInputs(model_id="sem-params", mc_samples=500), corpus_dir=tmp_path)
    text = a.render()
    assert "sem-params" in text
    assert a.falsifier_status()["F5"]["disparado"] is False


# --------------------------------------------------------------------- workload ---


def test_context_shorter_than_sliding_window(registry: Registry, device) -> None:
    g = build_graph(registry["mistral-7b-v0.1"])
    node = g.by_id("L0.kv_read")
    tiny = node.state_bytes(Workload(phase=Phase.DECODE, context_len=128))
    at_window = node.state_bytes(Workload(phase=Phase.DECODE, context_len=4096))
    assert tiny < at_window
    assert tiny == pytest.approx(at_window * 128 / 4096)


def test_prompt_of_one_token(registry: Registry, device) -> None:
    g = build_graph(registry["llama-3.1-8b"])
    p = profile(g, Workload(phase=Phase.PREFILL, batch=1, prompt_len=1), device, "bf16")
    assert p.total_time > 0
    assert p.tokens_per_second > 0
    assert p.memory_bound_share > 0.5, "prefill de 1 token se comporta como decode"


def test_all_declared_precisions_are_usable(registry: Registry, device) -> None:
    g = build_graph(registry["llama-3.1-8b"])
    w = Workload(phase=Phase.DECODE, batch=1, context_len=2048)
    sizes = {}
    for name in PRECISIONS:
        p = profile(g, w, device, weight_precision=name)
        assert p.total_time > 0, name
        sizes[name] = p.weight_bytes
    assert sizes["ternary"] < sizes["int4"] < sizes["int8"] < sizes["bf16"] < sizes["fp32"]


def test_ternary_falls_back_to_available_peak(device) -> None:
    """Nenhum device declara pico ternario: o fallback precisa existir e ser declarado."""
    assert "ternary" not in device.peak_flops
    assert device.peak("ternary") == device.peak_flops["int4"]


def test_unknown_precision_fails_loudly() -> None:
    with pytest.raises(ValueError, match="precisao desconhecida"):
        precision("int3")


def test_unknown_device_fails_loudly() -> None:
    with pytest.raises(KeyError, match="desconhecido"):
        get_device("gpu-imaginaria")


# --------------------------------------------------------------------- particao ---


def test_empty_partition_yields_unit_ceiling() -> None:
    part = Partition(model_id="x", phase_label="serving")
    assert part.hardened_share == 0.0
    assert part.amdahl_ceiling() == 1.0
    assert part.required_speedup_for(2.0) is None
    assert part.as_text() == ""
    assert part.as_dict()["regions"] == {}


def test_partition_with_no_candidates_does_not_crash() -> None:
    part = partition([], model_id="vazio")
    assert part.assignments == []
    assert part.uncovered_share == pytest.approx(1.0)
    findings = part.findings()
    assert all(f.status <= Status.CONDITIONAL_RESULT for f in findings)


def test_sensitivity_with_no_candidates() -> None:
    res = sensitivity([], Weights.load())
    assert res.samples > 0
    assert res.top1_stability == 0.0
    assert res.decidable is False


def test_economics_with_empty_design(registry: Registry, device) -> None:
    """Regiao fixa vazia: o simulador nao pode inventar um acelerador."""
    g = build_graph(registry["llama-3.1-8b"])
    sp = serving_profile(g, device, prompt_len=512, gen_len=64)
    part = Partition(model_id=g.model_id, phase_label="serving")
    design = build_design_point(g, part, sp.decode, target_tokens_per_second=1000)
    assert design.hardened_weight_bits == 0
    assert design.hardened_roles == []
    res = simulate(design, sp, device, annual_tokens=1e12, samples=500,
                   priors=EconomicsPriors.load(), obsolescence_rate_per_year=0.5)
    assert res.not_applicable, "sem regiao fixa nao ha acelerador a simular"
    assert res.prob_asic_cheaper is None
    assert res.as_dict()["percentiles"] is None


# ------------------------------------------------------------------ determinismo ---


def test_assessment_is_deterministic(registry: Registry) -> None:
    """Duas execucoes com a mesma entrada precisam produzir o mesmo relatorio.

    E o requisito central de REPRODUCIBILITY.md: sem isso a auditabilidade nao existe.
    """
    a = Assessment.build(AssessmentInputs(model_id="llama-3.1-8b", mc_samples=1500))
    b = Assessment.build(AssessmentInputs(model_id="llama-3.1-8b", mc_samples=1500))

    assert a.srs.score == b.srs.score
    assert a.part.hardened_share == b.part.hardened_share
    assert a.sens_lhs.top1_stability == b.sens_lhs.top1_stability
    assert a.economics.not_applicable == b.economics.not_applicable
    assert a.economics.as_dict() == b.economics.as_dict()
    assert [c.role for c in a.candidates] == [c.role for c in b.candidates]

    # O texto so difere no cabecalho (run_id e timestamp).
    ta = [l for l in a.render().splitlines() if not l.startswith(("run_id:", "generated_at:"))]
    tb = [l for l in b.render().splitlines() if not l.startswith(("run_id:", "generated_at:"))]
    assert ta == tb


def test_invariant_discovery_is_order_independent(registry: Registry) -> None:
    """A ordem dos modelos no corpus nao pode mudar o resultado."""
    views = [ModelView.of(s) for s in registry]
    forward = {i.key: i.coverage for i in discover_invariants(views, "exact")}
    backward = {i.key: i.coverage for i in discover_invariants(list(reversed(views)), "exact")}
    assert forward == backward


def test_fingerprints_are_stable_across_processes(registry: Registry) -> None:
    """Hash de fingerprint nao pode depender de PYTHONHASHSEED.

    sha256 sobre string canonica e estavel; hash() embutido do Python nao seria.
    """
    import subprocess
    import sys

    code = (
        "import sys; sys.path.insert(0,'src');"
        "from silicon_atlas.registry import Registry;"
        "from silicon_atlas.ir import build_graph;"
        "from silicon_atlas.fingerprint import fingerprint_graph;"
        "s=Registry.load()['llama-3.1-8b'];"
        "print(fingerprint_graph(build_graph(s), s)['L0.mlp'].exact)"
    )
    outs = set()
    for seed in ("0", "1", "12345"):
        env = {**__import__("os").environ, "PYTHONHASHSEED": seed}
        r = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env,
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
        outs.add(r.stdout.strip())
    assert len(outs) == 1, f"fingerprint variou com PYTHONHASHSEED: {outs}"


# -------------------------------------------------------------- governanca/IP ---


def test_client_supplied_model_cannot_be_verified_upstream(tmp_path: Path) -> None:
    """Ameaca S-003 do THREAT_MODEL: nao enviar arquitetura de cliente para servico externo."""
    src = PROJECT / "corpus" / "models" / "llama-3.1-8b.json"
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc["douvras"]["id"] = "cliente-x"
    doc["douvras"]["provenance"] = "CLIENT_SUPPLIED"
    (tmp_path / "cliente-x.json").write_text(json.dumps(doc), encoding="utf-8")

    spec = Registry.load(tmp_path)["cliente-x"]
    with pytest.raises(PermissionError, match="S-003"):
        verify_spec(spec, "meta-llama/Llama-3.1-8B")


def test_verify_without_repo_fails_with_guidance(registry: Registry, tmp_path: Path) -> None:
    src = PROJECT / "corpus" / "models" / "llama-3.1-8b.json"
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc["douvras"]["id"] = "sem-repo"
    doc["douvras"].pop("hf_repo", None)
    (tmp_path / "sem-repo.json").write_text(json.dumps(doc), encoding="utf-8")
    spec = Registry.load(tmp_path)["sem-repo"]
    assert spec.hf_repo is None
    with pytest.raises(ValueError, match="hf_repo"):
        verify_spec(spec)


def test_corpus_declares_hf_repo_for_every_model(registry: Registry) -> None:
    """Sem repo declarado, G-008 nao pode ser fechada por operacao de rotina (RB-001)."""
    faltando = [s.id for s in registry if not s.hf_repo]
    assert not faltando, f"modelos sem hf_repo no corpus: {faltando}"


def test_v3_gate_requires_real_reviews_not_just_a_folder() -> None:
    """Um README na pasta de revisoes nao pode satisfazer o portao V3.

    Regressao: a existencia de EXTERNAL_REVIEWS/README.md fazia glob('*.md') retornar verdadeiro
    e o portao passar sem nenhuma revisao ter ocorrido.
    """
    d = PROJECT / "04_VALIDATION" / "EXTERNAL_REVIEWS"
    assert (d / "README.md").exists(), "premissa do teste: o indice existe"
    assert not list(d.glob("ER-*.md")), "nenhuma revisao externa foi recebida ainda"

    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "-m", "silicon_atlas.cli", "gates"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert r.returncode == 0, r.stderr
    linha = [l for l in r.stdout.splitlines() if l.startswith("V3")]
    assert linha and "BLOQUEADO" in linha[0], r.stdout
    assert "G-010" in linha[0]


def test_evidence_debt_is_measured(registry: Registry) -> None:
    fs = FindingSet("t")
    fs.add(Finding("forte", 1.0, Status.COMPUTATIONAL_EVIDENCE))
    fs.add(Finding("fraco", 2.0, Status.ASSUMPTION, assumptions=("A-001",)))
    fs.add(Finding("ausente", None, Status.OPEN_GAP, gaps=("G-002",)))
    assert fs.evidence_debt() == pytest.approx(0.5)
    assert fs.status_histogram()["ASSUMPTION"] == 1


def test_assessment_evidence_debt_is_reported(registry: Registry) -> None:
    a = Assessment.build(AssessmentInputs(model_id="llama-3.1-8b", mc_samples=500))
    debt = a.findings.evidence_debt()
    assert 0.0 < debt < 1.0
    assert json.loads(a.to_json())["findings"]["evidence_debt"] == pytest.approx(debt, abs=1e-4)
