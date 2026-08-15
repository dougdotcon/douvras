"""Os documentos que definem a regra precisam obedecê-la.

O eixo de silício já tinha esta verificação; sem uma equivalente aqui, a governança do Model
Atlas seria o único conjunto de documentos do repositório livre do próprio lint — o que é
exatamente o tipo de assimetria que o `G-012` existe para acusar.
"""

from __future__ import annotations

import pytest
import yaml

from douvras_core.paths import PHASES, project_root
from douvras_core.status import Status, lint_text

ROOT = project_root("model-atlas")


def test_documentos_de_governanca_passam_no_proprio_lint() -> None:
    problemas = []
    for fase in PHASES:
        for f in (ROOT / fase).rglob("*.md"):
            problemas += [
                f"{f.name}:{p.line_no}: {p.term}" for p in lint_text(f.read_text(encoding="utf-8"))
            ]
    readme = ROOT / "README.md"
    if readme.exists():
        problemas += [
            f"README.md:{p.line_no}: {p.term}"
            for p in lint_text(readme.read_text(encoding="utf-8"))
        ]
    assert not problemas, problemas


def test_o_ledger_carrega_a_retratacao_de_c102() -> None:
    """`R-101` precisa estar refletida no ledger, não apenas narrada no Markdown.

    Foi assim que o Silicon Atlas descobriu o `R-003`: o Markdown dizia uma coisa e o JSON do
    mesmo `run_id` publicava outra.
    """
    doc = yaml.safe_load(
        (ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml").read_text(encoding="utf-8")
    )
    por_id = {c["id"]: c for c in doc}
    assert por_id["C-102"]["status"] == "RETRACTED"
    assert "F3" in por_id["C-102"].get("note", "")
    assert any(e.startswith("RUN:") for e in por_id["C-102"]["evidence"])


def test_toda_alegacao_declara_ao_menos_um_falsificador() -> None:
    """Uma alegação sem critério de refutação não é alegação — é opinião com identificador."""
    doc = yaml.safe_load(
        (ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml").read_text(encoding="utf-8")
    )
    sem = [c["id"] for c in doc if not c.get("falsifiers")]
    assert not sem, sem


def test_todo_status_do_ledger_existe_no_enum_ou_e_composto_declarado() -> None:
    doc = yaml.safe_load(
        (ROOT / "00_GOVERNANCE" / "CLAIM_LEDGER.yaml").read_text(encoding="utf-8")
    )
    compostos = {"CONDITIONAL_HYPOTHESIS"}
    for c in doc:
        s = c["status"]
        assert s in compostos or s in Status.__members__, f"{c['id']}: status {s!r}"


def test_as_lacunas_citadas_no_codigo_existem_no_registro() -> None:
    """Um `Finding` que cita `G-1xx` inexistente aponta para nada e some da auditoria."""
    import re

    registro = (ROOT / "02_OBSERVATION" / "GAP_REGISTER.md").read_text(encoding="utf-8")
    declaradas = set(re.findall(r"\bG-1\d\d\b", registro))

    citadas: set[str] = set()
    for py in (project_root("model-atlas").parent / "src" / "model_atlas").rglob("*.py"):
        citadas |= set(re.findall(r"\bG-1\d\d\b", py.read_text(encoding="utf-8")))

    orfas = citadas - declaradas
    assert not orfas, f"lacunas citadas no codigo e ausentes do GAP_REGISTER: {sorted(orfas)}"


@pytest.mark.parametrize(
    "caminho",
    [
        "01_DELIMITATION/PROBLEM_CHARTER.md",
        "02_OBSERVATION/GAP_REGISTER.md",
        "05_REDUCTION/MINIMAL_STRUCTURE.md",
        "04_VALIDATION/EXTERNAL_REVIEWS/README.md",
        "00_GOVERNANCE/RETRACTIONS_AND_CORRECTIONS.md",
        "07_SYSTEMATIZATION/OPERATIONS.md",
    ],
)
def test_artefatos_que_os_portoes_consomem_existem(caminho: str) -> None:
    assert (ROOT / caminho).is_file(), caminho


def test_o_diretorio_de_revisoes_externas_continua_vazio_e_isso_e_o_achado() -> None:
    """Se um `ER-*.md` aparecer, este teste quebra — e o certo é atualizar `G-110`, não o teste."""
    revisoes = list((ROOT / "04_VALIDATION" / "EXTERNAL_REVIEWS").glob("ER-*.md"))
    assert not revisoes, (
        f"revisao externa recebida: {[r.name for r in revisoes]}. "
        "Atualize G-110, o CLAIM_LEDGER e o veredicto do portao V3."
    )
