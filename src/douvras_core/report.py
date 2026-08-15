"""Portao de emissao: o que impede um relatorio de sair fora do contrato.

O Metodo 3.2 e 3.3 dizem o que um artefato pode afirmar e quais secoes ele deve conter.
Este modulo transforma isso em recusa executavel, e a lista de verificacoes e a lista de
falhas que ja aconteceram de verdade:

- **secoes obrigatorias** — Metodo 3.3;
- **vocabulario proibido** — Metodo 3.2;
- **numeros nao-finitos** — um `NaN` chegou a afirmacao principal de quatro relatorios
  antes desta guarda existir (`R-003` do Silicon Atlas). O portao vigiava o contrato
  textual e nao a aritmetica que passava por ele;
- **coerencia interna** — a secao que diz "nada foi dimensionado" contra os `Finding`
  emitidos no mesmo `run_id` (`G-012`). Um relatorio pode estar inteiro, bem-comportado
  no vocabulario, com todos os numeros finitos, e ainda assim se contradizer.

`EmissionRefused` e compartilhada pelos dois atlas de proposito: quem consome um relatorio
DOUVRAS captura uma excecao, nao duas.
"""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

from .status import Finding, FindingSet, lint_text


class EmissionRefused(RuntimeError):
    """Portao de emissao bloqueou o relatorio. Nao contornar: corrigir a causa."""


def check_sections(sections: Mapping[str, str], mandatory: Sequence[str]) -> None:
    """Toda secao obrigatoria existe e nao esta vazia (Metodo 3.3)."""
    missing = [s for s in mandatory if not sections.get(s, "").strip()]
    if missing:
        raise EmissionRefused(f"secoes obrigatorias ausentes (Metodo 3.3): {missing}")


def check_finite(findings: FindingSet | Sequence[Finding]) -> None:
    """Nenhum numero nao-finito sai daqui.

    Uma grandeza indefinida deve ser declarada como ausencia (`value=None`, `OPEN_GAP`),
    nunca publicada como numero. `inf` e `nan` sao respostas a perguntas mal-postas, e
    publicar a resposta esconde que a pergunta estava errada.
    """
    items = findings.items if isinstance(findings, FindingSet) else list(findings)
    bad = [f.name for f in items if isinstance(f.value, float) and not math.isfinite(f.value)]
    if bad:
        raise EmissionRefused(
            f"Finding numerico nao-finito: {bad}. Uma grandeza indefinida deve ser declarada "
            f"como ausencia (value=None, OPEN_GAP), nunca publicada como numero."
        )


def check_vocabulary(text: str) -> None:
    """O texto emitido nao usa o vocabulario proibido pelo Metodo 3.2."""
    problems = lint_text(text)
    if problems:
        detail = "; ".join(f"linha {p.line_no}: {p.term} ({p.reason})" for p in problems[:5])
        raise EmissionRefused(f"vocabulario proibido no relatorio (Metodo 3.2): {detail}")


def check_coherence(text: str, findings: FindingSet | Sequence[Finding],
                    rules: Sequence[tuple[str, str]]) -> None:
    """Confronta afirmacoes qualitativas do texto com os `Finding` emitidos (`G-012`).

    Cada regra e um par ``(padrao, nome_do_finding)``: se o padrao aparece no texto, o
    `Finding` nomeado precisa ser uma ausencia declarada (`value is None`). E a formalizacao
    de um defeito real — a secao 6 de um relatorio dizia "nada foi dimensionado" enquanto o
    Anexo D do **mesmo arquivo** publicava area de die e NRE.
    """
    items = findings.items if isinstance(findings, FindingSet) else list(findings)
    by_name = {f.name: f for f in items}
    for pattern, finding_name in rules:
        if not re.search(pattern, text, re.IGNORECASE):
            continue
        f = by_name.get(finding_name)
        if f is not None and f.value is not None:
            raise EmissionRefused(
                f"incoerencia interna (G-012): o texto afirma /{pattern}/ mas o Finding "
                f"{finding_name!r} publica {f.value!r} no mesmo run_id."
            )


def check_no_hand_promotion(findings: FindingSet) -> None:
    """Nenhum `Finding` esta acima do mais fraco dos pais que o proprio conjunto declara.

    `derive()` ja garante isso para quem passa por ele. Esta verificacao existe para quem
    **nao** passou: construir um `Finding(...)` a mao, declarar `parents=(...)` e escolher um
    status melhor que o dos pais e a unica forma de burlar o contrato sem levantar
    `StatusViolation`, e e a forma que a pressa produz.

    Verifica so pais presentes no conjunto — um pai externo nao e verificavel aqui, e fingir
    que e seria pior que nao verificar.
    """
    by_name = {f.name: f for f in findings.items}
    for f in findings.items:
        presentes = [by_name[p] for p in f.parents if p in by_name]
        if not presentes:
            continue
        teto = min(p.status for p in presentes)
        if f.status > teto:
            raise EmissionRefused(
                f"{f.name!r} declara {f.status.name} com pai em {teto.name}: promocao a mao. "
                f"Use derive() ou corrija a cadeia."
            )


def evidence_appendix(findings: FindingSet, title: str = "Anexo — rastreabilidade") -> str:
    """Tabela que liga cada numero emitido a seu status, premissas e lacunas.

    E o que torna a frase "cada numero e rastreavel ate sua premissa" verificavel em vez de
    promocional. Ausencias declaradas aparecem como `—`, nunca somem.
    """
    lines = [
        f"## {title}",
        "",
        "| Resultado | Valor | Status | Premissas | Lacunas |",
        "|---|---|---|---|---|",
    ]
    for f in findings.items:
        if f.value is None:
            val = "— *(ausencia declarada)*"
        elif isinstance(f.value, float):
            val = f"{f.value:,.4g}".replace(",", " ")
        else:
            val = str(f.value)
        if f.unit:
            val += f" {f.unit}"
        lines.append(
            f"| `{f.name}` | {val} | `{f.status.name}` | "
            f"{', '.join(f.assumptions) or '—'} | {', '.join(f.gaps) or '—'} |"
        )
    lines += [
        "",
        f"Elo mais fraco do conjunto: **`{findings.weakest.name}`**. "
        f"Divida de evidencia: **{findings.evidence_debt():.1%}**.",
    ]
    return "\n".join(lines)


def frontmatter(**fields: Any) -> str:
    """Cabecalho YAML de um artefato DOUVRAS."""
    lines = ["---"]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


__all__ = [
    "EmissionRefused",
    "check_sections",
    "check_finite",
    "check_vocabulary",
    "check_coherence",
    "check_no_hand_promotion",
    "evidence_appendix",
    "frontmatter",
]
