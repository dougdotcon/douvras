"""Resolucao de caminhos do monorepo DOUVRAS.

Existe um unico motivo para este modulo: quando havia um atlas so, `parents[2] / "config"`
era suficiente e correto. Com dois atlas sobre o mesmo core, essa expressao passa a apontar
para a raiz do monorepo — que nao tem `config/` nem `corpus/` — e cada motor precisaria
descobrir sozinho a qual projeto pertence.

Aqui a pergunta e respondida em um lugar: `project_root("silicon-atlas")` devolve o diretorio
que carrega as fases DOUVRAS (00_GOVERNANCE .. 99_RELEASES), os priors versionados e o corpus
daquele eixo de pesquisa.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Raiz do monorepo: o diretorio que contem `src/`, `scripts/`, `tests/` e os projetos.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Projetos DOUVRAS conhecidos. Um nome fora desta lista e erro de programacao, nao
#: configuracao ausente — por isso levanta em vez de devolver um caminho inexistente.
PROJECTS: tuple[str, ...] = ("silicon-atlas", "model-atlas")


class UnknownProject(KeyError):
    """Nome de projeto que nao existe no monorepo."""


def _env_key(name: str) -> str:
    return "DOUVRAS_" + name.replace("-", "_").upper() + "_ROOT"


def project_root(name: str) -> Path:
    """Diretorio raiz de um projeto DOUVRAS.

    Aceita sobrescrita por variavel de ambiente (`DOUVRAS_SILICON_ATLAS_ROOT`,
    `DOUVRAS_MODEL_ATLAS_ROOT`) para que um teste possa montar um projeto sintetico em
    diretorio temporario sem tocar nos artefatos reais.
    """
    if name not in PROJECTS:
        raise UnknownProject(
            f"projeto desconhecido: {name!r}; conhecidos: {', '.join(PROJECTS)}"
        )
    override = os.environ.get(_env_key(name))
    return Path(override).resolve() if override else REPO_ROOT / name


#: Fases do Metodo DOUVRAS, na ordem dos portoes D0 -> S6.
PHASES: tuple[str, ...] = (
    "00_GOVERNANCE",
    "01_DELIMITATION",
    "02_OBSERVATION",
    "03_UNIFICATION",
    "04_VALIDATION",
    "05_REDUCTION",
    "06_ARCHITECTURE",
    "07_SYSTEMATIZATION",
    "99_RELEASES",
)

#: Politica de status: subiu para o nivel DOUVRAS junto com `status.py`, porque descreve o
#: contrato do core e nao as decisoes de um atlas especifico.
STATUS_POLICY = REPO_ROOT / "00_GOVERNANCE" / "STATUS_POLICY.md"


__all__ = [
    "REPO_ROOT",
    "PROJECTS",
    "PHASES",
    "STATUS_POLICY",
    "UnknownProject",
    "project_root",
]
