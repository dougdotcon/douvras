"""Invariant Discovery Engine (Metodo 12.4).

Responde a pergunta do ciclo C-001: quais estruturas sobrevivem a mudanca de versao, de
tamanho e de familia — e em qual nivel de identidade sobrevivem.

Um invariante aqui nao e "os modelos sao parecidos". E: *este padrao especifico aparece em
N dos M modelos comparados, com esta cobertura de custo, e quebra nestes casos*. Casos que
nao se encaixam sao preservados, nunca suavizados (Metodo 4.3, portao U2).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .fingerprint import Fingerprint, fingerprint_graph, group_patterns, signature_diff
from .ir.graph import Graph, Workload
from .registry import ModelSpec
from douvras_core.status import Finding, Status

LEVELS = ("topology", "pattern", "exact")


@dataclass
class ModelView:
    """Um modelo ja canonicalizado e impresso digitalmente, pronto para comparacao."""

    spec: ModelSpec
    graph: Graph
    fingerprints: dict[str, Fingerprint] = field(default_factory=dict)

    @classmethod
    def of(cls, spec: ModelSpec) -> "ModelView":
        from .ir import build_graph

        g = build_graph(spec)
        return cls(spec=spec, graph=g, fingerprints=fingerprint_graph(g, spec))

    @property
    def id(self) -> str:
        return self.spec.id

    def layer_blocks(self) -> dict[str, Fingerprint]:
        return {k: v for k, v in self.fingerprints.items() if k.startswith("L")}


@dataclass
class Invariant:
    """Um padrao candidato a invariante, com o registro do que ele NAO cobre."""

    key: str
    level: str
    role: str
    fingerprint: Fingerprint
    models: list[str]
    instances: dict[str, int]              # modelo -> quantas instancias
    cost_share: dict[str, float] = field(default_factory=dict)  # modelo -> fracao do custo
    absent_from: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        """Fracao dos modelos comparados em que o padrao aparece."""
        total = len(self.models) + len(self.absent_from)
        return len(self.models) / total if total else 0.0

    @property
    def families(self) -> list[str]:
        return sorted({m.split("-")[0] for m in self.models})

    @property
    def total_instances(self) -> int:
        return sum(self.instances.values())

    @property
    def mean_cost_share(self) -> float:
        return (
            sum(self.cost_share.values()) / len(self.cost_share) if self.cost_share else 0.0
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "level": self.level,
            "role": self.role,
            "coverage": round(self.coverage, 4),
            "models": self.models,
            "absent_from": self.absent_from,
            "instances": self.instances,
            "total_instances": self.total_instances,
            "mean_cost_share": round(self.mean_cost_share, 6),
            "constants": dict(self.fingerprint.constants),
        }


def discover_invariants(
    views: Sequence[ModelView],
    level: str = "exact",
    workload: Workload | None = None,
) -> list[Invariant]:
    """Encontra padroes compartilhados entre modelos no nivel de identidade pedido.

    ``workload`` opcional pondera cada padrao pela fracao de custo que ele representa —
    sem isso, um padrao onipresente e irrelevante (ex.: uma normalizacao) parece tao
    importante quanto o que domina a inferencia.
    """
    if level not in LEVELS:
        raise ValueError(f"nivel invalido: {level!r}; use {LEVELS}")

    table: dict[str, Invariant] = {}
    all_ids = [v.id for v in views]

    for view in views:
        groups = group_patterns(view.layer_blocks(), level=level)
        totals = view.graph.total_flops(workload) if workload else 0.0
        for key, inst in groups.items():
            inv = table.get(key)
            if inv is None:
                inv = Invariant(
                    key=key,
                    level=level,
                    role=inst.fingerprint.role,
                    fingerprint=inst.fingerprint,
                    models=[],
                    instances={},
                )
                table[key] = inv
            inv.models.append(view.id)
            inv.instances[view.id] = inst.count
            if workload and totals > 0:
                cost = sum(
                    n.flops(workload)
                    for b in inst.blocks
                    for n in view.graph.by_block(b)
                )
                inv.cost_share[view.id] = cost / totals

    for inv in table.values():
        inv.absent_from = [m for m in all_ids if m not in inv.models]

    return sorted(
        table.values(),
        key=lambda i: (-i.coverage, -i.mean_cost_share, -i.total_instances),
    )


# --------------------------------------------------------------------------------------
# Diff entre versoes
# --------------------------------------------------------------------------------------


@dataclass
class VersionDiff:
    """O que mudou entre duas versoes, separado por nivel de identidade."""

    older: str
    newer: str
    days_between: int | None
    changed_config: dict[str, tuple[Any, Any]]
    stability: dict[str, float]                   # nivel -> fracao de blocos preservados
    lost_patterns: dict[str, list[str]]           # nivel -> papeis que sumiram
    gained_patterns: dict[str, list[str]]
    signature_changes: list[str] = field(default_factory=list)

    @property
    def structurally_identical(self) -> bool:
        return self.stability.get("exact", 0.0) >= 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "older": self.older,
            "newer": self.newer,
            "days_between": self.days_between,
            "changed_config": {k: list(v) for k, v in self.changed_config.items()},
            "stability": {k: round(v, 4) for k, v in self.stability.items()},
            "lost_patterns": self.lost_patterns,
            "gained_patterns": self.gained_patterns,
            "signature_changes": self.signature_changes[:40],
        }


_TRACKED_CONFIG = (
    "hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
    "num_key_value_heads", "vocab_size", "max_position_embeddings", "rope_theta",
    "hidden_act", "sliding_window", "tie_word_embeddings", "head_dim",
)


def _days_between(a: ModelSpec, b: ModelSpec) -> int | None:
    if not (a.release_date and b.release_date):
        return None
    fmt = "%Y-%m-%d"
    return abs(
        (_dt.datetime.strptime(b.release_date, fmt) - _dt.datetime.strptime(a.release_date, fmt)).days
    )


def diff_versions(older: ModelView, newer: ModelView) -> VersionDiff:
    """Compara duas versoes bloco a bloco, em todos os niveis de identidade."""
    changed = {
        k: (older.spec.raw_config.get(k), newer.spec.raw_config.get(k))
        for k in _TRACKED_CONFIG
        if older.spec.raw_config.get(k) != newer.spec.raw_config.get(k)
    }

    stability: dict[str, float] = {}
    lost: dict[str, list[str]] = {}
    gained: dict[str, list[str]] = {}
    for level in LEVELS:
        a = group_patterns(older.layer_blocks(), level)
        b = group_patterns(newer.layer_blocks(), level)
        shared = set(a) & set(b)
        union = set(a) | set(b)
        stability[level] = len(shared) / len(union) if union else 1.0
        lost[level] = sorted({a[k].fingerprint.role for k in set(a) - set(b)})
        gained[level] = sorted({b[k].fingerprint.role for k in set(b) - set(a)})

    changes: list[str] = []
    role_a = {fp.role: fp for fp in older.layer_blocks().values()}
    role_b = {fp.role: fp for fp in newer.layer_blocks().values()}
    for role in sorted(set(role_a) & set(role_b)):
        if role_a[role].exact != role_b[role].exact:
            changes.extend(f"[{role}] {ln}" for ln in signature_diff(role_a[role], role_b[role]))

    return VersionDiff(
        older=older.id,
        newer=newer.id,
        days_between=_days_between(older.spec, newer.spec),
        changed_config=changed,
        stability=stability,
        lost_patterns=lost,
        gained_patterns=gained,
        signature_changes=changes,
    )


# --------------------------------------------------------------------------------------
# Estabilidade temporal
# --------------------------------------------------------------------------------------


@dataclass
class StabilityReport:
    """Estabilidade de uma familia ao longo de suas versoes."""

    family: str
    versions: list[str]
    diffs: list[VersionDiff]
    #: Estabilidade por nivel. ``None`` quando nao houve transicao observada — nunca 1.0.
    #: Devolver 1.0 para familia sem historico premiava ausencia de dado (retratacao R-004).
    level_stability: dict[str, float | None]
    change_rate_per_year: float | None
    scale_pairs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def transitions(self) -> int:
        return len(self.diffs)

    @property
    def recent_exact_stability(self) -> float | None:
        """Estabilidade exata apenas na transicao mais recente.

        A distancia entre este numero e a media da familia e o **efeito do escopo**: incluir
        uma geracao arquitetural antiga derruba a estabilidade media. Nenhum dos dois numeros
        e mais correto que o outro; o que nao pode acontecer e o escopo ficar implicito.
        """
        return self.diffs[-1].stability["exact"] if self.diffs else None

    @property
    def scope_spread(self) -> float | None:
        r = self.recent_exact_stability
        if r is None:
            return None
        return r - self.level_stability.get("exact", 0.0)

    def finding(self, level: str = "exact") -> Finding:
        v = self.level_stability.get(level)
        if v is None:
            return Finding(
                name=f"stability.{self.family}.{level}",
                value=None,
                status=Status.OPEN_GAP,
                unit="fracao de blocos preservados",
                gaps=("G-006",),
                note=(
                    f"{len(self.versions)} versao(oes) sem transicao temporal: estabilidade "
                    f"estrutural nao observada"
                    + (f"; {len(self.scale_pairs)} par(es) de escala ignorado(s)"
                       if self.scale_pairs else "")
                ),
            )
        return Finding(
            name=f"stability.{self.family}.{level}",
            value=v,
            status=Status.COMPUTATIONAL_EVIDENCE,
            unit="fracao de blocos preservados",
            assumptions=("A-001",),
            gaps=("G-001",),
            note=f"{self.transitions} transicao(oes) em {' -> '.join(self.versions)}",
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "versions": self.versions,
            "transitions": self.transitions,
            "scale_pairs": [list(p) for p in self.scale_pairs],
            "level_stability": {
                k: (round(v, 4) if v is not None else None)
                for k, v in self.level_stability.items()
            },
            "recent_exact_stability": self.recent_exact_stability,
            "scope_spread": self.scope_spread,
            "change_rate_per_year": self.change_rate_per_year,
            "diffs": [d.as_dict() for d in self.diffs],
        }


def family_stability(views: Sequence[ModelView]) -> StabilityReport:
    """Estabilidade entre versoes **consecutivas no tempo** de uma familia.

    Dois pares distintos precisam ser separados, e confundi-los foi a retratacao R-004:

    * **transicao temporal** — datas de release estritamente crescentes. Mede evolucao, e e o
      que informa risco de obsolescencia.
    * **par de escala** — mesma data, tamanhos diferentes (Qwen2.5 7B e 14B saíram no mesmo dia).
      Mede escalabilidade da arquitetura, nao sua estabilidade no tempo. Fica fora de ``diffs``.

    Sem nenhuma transicao temporal, `level_stability` e ``None`` — nunca 1.0. Ausencia de
    observacao nao e observacao de estabilidade.
    """
    ordered = sorted(views, key=lambda v: (v.spec.release_order_key, v.spec.param_count()))

    diffs: list[VersionDiff] = []
    scale_pairs: list[tuple[str, str]] = []
    for a, b in zip(ordered, ordered[1:]):
        da, db = a.spec.release_date, b.spec.release_date
        if da and db and da == db:
            scale_pairs.append((a.id, b.id))
            continue
        diffs.append(diff_versions(a, b))

    level_stability: dict[str, float | None] = {
        lvl: (sum(d.stability[lvl] for d in diffs) / len(diffs) if diffs else None)
        for lvl in LEVELS
    }

    rate = None
    spans = [d.days_between for d in diffs if d.days_between]
    if spans and diffs:
        changed = sum(1 for d in diffs if not d.structurally_identical)
        years = sum(spans) / 365.25
        rate = changed / years if years > 0 else None

    return StabilityReport(
        family=ordered[0].spec.family if ordered else "?",
        versions=[v.id for v in ordered],
        diffs=diffs,
        level_stability=level_stability,
        change_rate_per_year=rate,
        scale_pairs=scale_pairs,
    )


def block_role_stability(
    family_views: Sequence[ModelView],
    corpus_views: Sequence[ModelView] | None = None,
    *,
    within_weight: float = 0.6,
) -> dict[str, Finding]:
    """Estabilidade (fator E do LHS) por papel de bloco: 'attention', 'mlp', 'moe'...

    Combina duas perguntas distintas:

    * **dentro da familia** — o mesmo circuito continua valendo na proxima versao?
      (o que decide risco de obsolescencia)
    * **no corpus inteiro** — o mesmo circuito serve outros modelos?
      (o que decide o mercado enderecavel do bloco de IP)

    Familia com uma unica versao nao permite responder a primeira: o Finding sai com
    lacuna G-006 aberta em vez de um numero otimista.
    """
    corpus = list(corpus_views or family_views)
    ordered = sorted(family_views, key=lambda v: v.spec.release_order_key)

    def role_hashes(view: ModelView) -> dict[str, set[str]]:
        # Todos os blocos, nao so os de camada: 'head' e 'embedding' mudam com o vocabulario
        # e sao justamente os que mais custam em ROM.
        out: dict[str, set[str]] = {}
        for fp in view.fingerprints.values():
            out.setdefault(fp.role, set()).add(fp.exact)
        return out

    per_model = {v.id: role_hashes(v) for v in corpus}
    roles = sorted({r for m in per_model.values() for r in m})

    out: dict[str, Finding] = {}
    for role in roles:
        # dentro da familia, entre versoes consecutivas
        pairs = 0
        preserved = 0
        for a, b in zip(ordered, ordered[1:]):
            ha, hb = per_model[a.id].get(role, set()), per_model[b.id].get(role, set())
            if ha and hb:
                pairs += 1
                preserved += 1 if (ha & hb) else 0
        within = (preserved / pairs) if pairs else None

        # no corpus inteiro: modelos que compartilham ao menos um hash exato com a familia
        family_hashes = {h for v in ordered for h in per_model[v.id].get(role, set())}
        hits = sum(
            1 for v in corpus if per_model[v.id].get(role, set()) & family_hashes
        )
        cross = hits / len(corpus) if corpus else 0.0

        if within is None:
            out[role] = Finding(
                f"E.{role}",
                cross,
                Status.ASSUMPTION,
                unit="[0,1]",
                assumptions=("A-007",),
                gaps=("G-006",),
                note=(
                    f"familia com uma unica versao no corpus: estabilidade temporal nao "
                    f"observada; usando apenas cobertura de corpus ({hits}/{len(corpus)} modelos)"
                ),
            )
        else:
            val = within_weight * within + (1 - within_weight) * cross
            out[role] = Finding(
                f"E.{role}",
                val,
                Status.COMPUTATIONAL_EVIDENCE,
                unit="[0,1]",
                assumptions=("A-001",),
                gaps=("G-001",),
                note=(
                    f"preservado em {preserved}/{pairs} transicoes de versao; "
                    f"presente em {hits}/{len(corpus)} modelos do corpus"
                ),
            )
    return out


def invariant_map_rows(invs: Iterable[Invariant], min_coverage: float = 0.0) -> list[dict[str, Any]]:
    """Linhas para o INVARIANT_MAP.md (Metodo 4.3), incluindo falhas conhecidas."""
    rows = []
    for inv in invs:
        if inv.coverage < min_coverage:
            continue
        rows.append(
            {
                "candidate": f"{inv.role} [{inv.level}] {inv.key[:8]}",
                "models_covered": len(inv.models),
                "coverage": round(inv.coverage, 3),
                "instances": inv.total_instances,
                "cost_share": round(inv.mean_cost_share, 4),
                "known_failures": ", ".join(inv.absent_from) or "nenhuma no corpus",
                "status": "HYPOTHESIS" if inv.coverage < 1.0 else "PARTIAL_RESULT",
            }
        )
    return rows


__all__ = [
    "ModelView",
    "Invariant",
    "VersionDiff",
    "StabilityReport",
    "discover_invariants",
    "diff_versions",
    "family_stability",
    "invariant_map_rows",
    "LEVELS",
]
