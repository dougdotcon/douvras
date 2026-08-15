"""CLI e ClaimLedger — 800 linhas que atravessaram o ciclo C-001 sem um unico teste.

Foi por ai que passaram: `--corpus` silenciosamente ignorada em cinco subcomandos, `registry
verify` procurando um campo inexistente, crash de encoding com stdout redirecionado, e um
`record_run` que duplicava a mesma frase quatro vezes no ledger versionado.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from silicon_atlas.cli import main
from douvras_core.paths import project_root
from douvras_core.status import Claim, ClaimLedger

ROOT = project_root("silicon-atlas")


# ------------------------------------------------------------------------------ CLI ---


@pytest.mark.parametrize(
    "argv",
    [
        ["registry", "list"],
        ["fingerprint", "llama-3.1-8b"],
        ["diff", "llama-3-8b", "llama-3.1-8b"],
        ["stability", "llama"],
        ["invariants", "--level", "exact", "--top", "5"],
        ["profile", "llama-3.1-8b"],
        ["quantize", "llama-3.1-8b"],
        ["devices"],
        ["gates"],
    ],
)
def test_read_only_commands_exit_zero(argv, capsys) -> None:
    assert main(argv) == 0
    assert capsys.readouterr().out.strip(), f"{argv[0]} nao produziu saida"


def test_fingerprint_output_is_valid_json(capsys) -> None:
    main(["fingerprint", "llama-3.1-8b"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["model"] == "llama-3.1-8b"
    assert doc["attention"] == "gqa"
    assert doc["params"] == 8_030_261_248


def test_unknown_model_raises_with_guidance() -> None:
    with pytest.raises(KeyError, match="nao registrado"):
        main(["fingerprint", "modelo-que-nao-existe"])


def test_unknown_family_exits_two(capsys) -> None:
    assert main(["stability", "familia-inexistente"]) == 2
    assert "disponiveis" in capsys.readouterr().err


def test_registry_show_without_model_exits_two(capsys) -> None:
    assert main(["registry", "show"]) == 2
    assert "uso:" in capsys.readouterr().err


def test_partition_survives_redirected_stdout_with_legacy_encoding(monkeypatch) -> None:
    """A arte ASCII usa U+251C/U+2514. Com stdout em cp1252 isso quebrava com exit 1.

    Reproduz o caminho real: nao o console interativo (que usa WriteConsoleW), mas stdout
    redirecionado para arquivo ou pipe.
    """
    buf = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="")
    monkeypatch.setattr(sys, "stdout", buf)
    try:
        code = main(["partition", "llama-3.1-8b"])
    finally:
        buf.flush()
    assert code == 0


def test_corpus_flag_is_honored_by_every_command(tmp_path: Path, capsys) -> None:
    """`--corpus` era honrada por `registry list` e ignorada por score/partition/gates."""
    src = ROOT / "corpus" / "models" / "llama-3.1-8b.json"
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc["douvras"]["id"] = "modelo-alternativo"
    (tmp_path / "modelo-alternativo.json").write_text(json.dumps(doc), encoding="utf-8")

    assert main(["--corpus", str(tmp_path), "registry", "list"]) == 0
    assert "modelo-alternativo" in capsys.readouterr().out

    # Se o corpus fosse ignorado, este id seria desconhecido e levantaria KeyError.
    assert main(["--corpus", str(tmp_path), "score", "modelo-alternativo"]) == 0
    assert "modelo-alternativo" in capsys.readouterr().out

    # E o corpus padrao nao deve mais ser visivel sob a flag.
    with pytest.raises(KeyError):
        main(["--corpus", str(tmp_path), "fingerprint", "llama-3.1-8b"])


def test_lint_returns_one_on_forbidden_vocabulary(tmp_path: Path, capsys) -> None:
    ruim = tmp_path / "ruim.md"
    ruim.write_text("O problema esta resolvido e o ganho e garantido.", encoding="utf-8")
    assert main(["lint", str(ruim)]) == 1
    saida = capsys.readouterr().out
    assert "resolvido" in saida and "garantido" in saida


def test_lint_returns_zero_on_clean_text(tmp_path: Path) -> None:
    bom = tmp_path / "bom.md"
    bom.write_text("Resultado sob condicoes declaradas, com limitacoes.", encoding="utf-8")
    assert main(["lint", str(bom)]) == 0


def test_published_reports_pass_their_own_lint() -> None:
    reports = ROOT / "99_RELEASES" / "reports"
    if not any(reports.glob("*.md")):
        pytest.skip("nenhum relatorio emitido ainda")
    assert main(["lint", str(reports)]) == 0


# --------------------------------------------------------------------- ClaimLedger ---


@pytest.fixture
def ledger_path(tmp_path: Path) -> Path:
    p = tmp_path / "CLAIM_LEDGER.yaml"
    p.write_text(
        "- id: C-100\n"
        "  statement: uma alegacao de teste\n"
        "  status: HYPOTHESIS\n"
        "  assumptions: [A-001]\n"
        "  evidence: []\n"
        "  falsifiers: [algo mensuravel falha]\n"
        "  owner: research\n"
        "  last_reviewed: '2026-01-01'\n",
        encoding="utf-8",
    )
    return p


def test_ledger_round_trip_preserves_fields(ledger_path: Path) -> None:
    a = ClaimLedger.load(ledger_path)
    a.save(ledger_path)
    b = ClaimLedger.load(ledger_path)
    ca, cb = a["C-100"], b["C-100"]
    assert (ca.id, ca.statement, ca.status, ca.falsifiers, ca.assumptions, ca.owner) == (
        cb.id, cb.statement, cb.status, cb.falsifiers, cb.assumptions, cb.owner
    )


def test_record_run_is_idempotent(ledger_path: Path) -> None:
    """Reexecutar o ciclo com o mesmo run_id nao pode inchar o ledger.

    Antes desta correcao, `CLAIM_LEDGER.yaml` acumulou seis tags de execucao e a mesma frase de
    motivo repetida quatro vezes numa nota de 616 caracteres.
    """
    payload = {"C-100": {"falsified": True, "reason": "criterio X disparou"}}
    led = ClaimLedger.load(ledger_path)
    for _ in range(4):
        led.record_run(payload, "20260804T120000Z")
    c = led["C-100"]
    assert c.evidence == ["RUN:20260804T120000Z"]
    assert c.note.count("criterio X disparou") == 1
    assert c.status == "RETRACTED"


def test_record_run_stamps_from_run_id_not_today(ledger_path: Path) -> None:
    """Data de saida derivada do run_id: `date.today()` fazia o YAML mudar por dia de execucao."""
    led = ClaimLedger.load(ledger_path)
    led.record_run({"C-100": {"falsified": False}}, "20260804T120000Z")
    assert led["C-100"].last_reviewed == "2026-08-04"


def test_record_run_never_promotes_status(ledger_path: Path) -> None:
    """Execucao anexa evidencia e pode retratar; promover e decisao humana registrada."""
    led = ClaimLedger.load(ledger_path)
    led.record_run({"C-100": {"falsified": False}}, "20260804T120000Z")
    assert led["C-100"].status == "HYPOTHESIS"
    assert led["C-100"].evidence == ["RUN:20260804T120000Z"]


def test_record_run_ignores_unknown_claims(ledger_path: Path) -> None:
    led = ClaimLedger.load(ledger_path)
    led.record_run({"C-999": {"falsified": True}}, "20260804T120000Z")
    assert [c.id for c in led.claims] == ["C-100"]


def test_claim_detects_its_own_falsifiers() -> None:
    c = Claim(id="C-1", statement="x", status="HYPOTHESIS", falsifiers=["a falhou", "b falhou"])
    assert c.check_falsified({"a falhou": True, "b falhou": False}) == ["a falhou"]
    assert c.check_falsified({}) == []


def test_real_ledger_has_no_duplicated_evidence() -> None:
    """Guarda contra a regressao no arquivo versionado, nao so na classe."""
    led = ClaimLedger.load(ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml")
    for c in led.claims:
        assert len(c.evidence) == len(set(c.evidence)), f"{c.id} com evidencia duplicada"
        for frase in {p.strip() for p in c.note.split("|") if p.strip()}:
            assert c.note.count(frase) == 1, f"{c.id} repete '{frase[:40]}...' na nota"
