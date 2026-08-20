"""Interface de importacao anunciada pelo `ADR-0001`: traçar um modelo real e comparar contra
a IR analitica derivada de config.

Fora do caminho principal (`R1`, `ADR-0001`) — exige pesos locais, e por isso vive fora do
construtor por familia (`ir/builder.py`), que roda sobre `config.json` sem tocar peso nenhum.

## Por que auditoria de pesos, nao `torch.export`

O criterio do ADR e "traçar um modelo por familia e medir a diferenca de FLOPs/bytes por classe
de operador". Um traçado via `torch.export` produz um grafo ATen de baixo nivel (`aten.mm`,
`aten.rsqrt`, ...) que exigiria um mapeador semantico ATen -> `OpKind` para virar comparavel —
peca propensa a erro silencioso, e o proprio erro que o ADR quer evitar (perfil errado por
mapeamento errado, nao por IR errada).

`named_parameters()` do modelo real da a mesma pergunta com uma resposta mais direta: **todo
tensor de peso que existe de verdade tem um no correspondente na IR, com a shape certa?** Um
modulo aprendido sem contrapartida na IR — ou o inverso, um no da IR sem peso real por tras —
e exatamente "operador ausente invalida o perfil", sem depender de mapear semantica de baixo
nivel. Nao mede FLOPs de operadores sem peso (softmax, RoPE aplicado funcionalmente) — essa
parte do criterio do ADR continua em aberto, e o relatorio declara isso.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .graph import Graph


@dataclass(frozen=True)
class WeightDivergence:
    """Um no da IR analitica cuja shape nao bate com o peso real correspondente."""

    node_id: str
    ir_shape: tuple[int, ...] | None
    real_shape: tuple[int, ...] | None
    real_param_name: str | None


@dataclass
class ImportAudit:
    """Resultado de comparar a IR analitica contra os pesos reais de um checkpoint."""

    model_id: str
    ir_nodes_with_weight: int
    real_params_with_weight: int
    matched: int
    ir_orphans: list[str] = field(default_factory=list)          # no na IR, sem peso real
    real_orphans: list[str] = field(default_factory=list)        # peso real, sem no na IR
    shape_divergences: list[WeightDivergence] = field(default_factory=list)
    ir_total_elems: int = 0
    real_total_elems: int = 0

    @property
    def elem_count_divergence_pct(self) -> float:
        """Diferenca percentual entre contagem de parametros da IR e do checkpoint real."""
        if self.real_total_elems == 0:
            return float("inf")
        return abs(self.ir_total_elems - self.real_total_elems) / self.real_total_elems * 100.0

    @property
    def clean(self) -> bool:
        """Nenhum orfao dos dois lados e nenhuma divergencia de shape."""
        return not self.ir_orphans and not self.real_orphans and not self.shape_divergences

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "ir_nodes_with_weight": self.ir_nodes_with_weight,
            "real_params_with_weight": self.real_params_with_weight,
            "matched": self.matched,
            "ir_orphans": self.ir_orphans,
            "real_orphans": self.real_orphans,
            "shape_divergences": [
                {
                    "node_id": d.node_id,
                    "ir_shape": list(d.ir_shape) if d.ir_shape else None,
                    "real_shape": list(d.real_shape) if d.real_shape else None,
                    "real_param_name": d.real_param_name,
                }
                for d in self.shape_divergences
            ],
            "ir_total_elems": self.ir_total_elems,
            "real_total_elems": self.real_total_elems,
            "elem_count_divergence_pct": round(self.elem_count_divergence_pct, 4),
            "clean": self.clean,
        }


#: Mapeia `role` do no da IR (ver `ir/builder.py`) para o sufixo do nome do parametro real,
#: na convencao HuggingFace/Llama. Declarado aqui, nao adivinhado por regex solto: um mapeamento
#: errado produziria falso "operador ausente" — o inverso do que a auditoria existe para evitar.
_ROLE_TO_PARAM_SUFFIX = {
    "q_proj": "self_attn.q_proj.weight",
    "k_proj": "self_attn.k_proj.weight",
    "v_proj": "self_attn.v_proj.weight",
    "o_proj": "self_attn.o_proj.weight",
    "gate_proj": "mlp.gate_proj.weight",
    "up_proj": "mlp.up_proj.weight",
    "down_proj": "mlp.down_proj.weight",
    "input_layernorm": "input_layernorm.weight",
    "post_attention_layernorm": "post_attention_layernorm.weight",
}

_LAYER_RE = re.compile(r"^L(\d+)\.")


def audit_against_real_weights(
    graph: Graph, named_param_shapes: dict[str, tuple[int, ...]], model_id: str
) -> ImportAudit:
    """Compara os nos com peso da IR analitica contra `named_parameters()` de um checkpoint real.

    `named_param_shapes` e `{nome_do_parametro: tuple(shape)}` — extraido fora desta funcao
    para que ela permaneca testavel sem carregar `torch` nem um checkpoint real (ver
    `tests/silicon/test_ir_importers.py`).
    """
    reais_usados: set[str] = set()
    ir_orphans: list[str] = []
    divergencias: list[WeightDivergence] = []
    matched = 0
    ir_com_peso = 0

    for node in graph:
        if not node.weight_shape:
            continue
        ir_com_peso += 1

        if node.layer is not None:
            nome_real = f"model.layers.{node.layer}.{_ROLE_TO_PARAM_SUFFIX.get(node.role, node.role)}"
        elif node.role == "embed_tokens":
            nome_real = "model.embed_tokens.weight"
        elif node.role == "final_norm":
            nome_real = "model.norm.weight"
        elif node.role == "lm_head":
            # Com embeddings amarrados, `resident_count=0` (ver `ir/builder.py`) e nao existe
            # `lm_head.weight` separado no checkpoint: e o MESMO tensor de `embed_tokens`. Nao
            # e "operador ausente" — e o mesmo peso comparado contra o dono certo.
            nome_real = (
                "model.embed_tokens.weight"
                if "lm_head.weight" not in named_param_shapes
                else "lm_head.weight"
            )
        else:
            nome_real = None

        if nome_real is None or nome_real not in named_param_shapes:
            ir_orphans.append(node.id)
            continue

        real_shape = named_param_shapes[nome_real]
        reais_usados.add(nome_real)
        # So `LINEAR` precisa inverter: a IR guarda (in_features, out_features), mas
        # `nn.Linear.weight` real e (out, in). `EMBEDDING` ja usa (vocab, d) nos dois lados —
        # inverter aqui produziria falso positivo de divergencia de shape.
        if node.kind.value == "linear" and len(node.weight_shape) == 2:
            ir_shape_como_real = tuple(reversed(node.weight_shape))
        else:
            ir_shape_como_real = node.weight_shape
        if ir_shape_como_real == real_shape:
            matched += 1
        else:
            divergencias.append(
                WeightDivergence(
                    node_id=node.id, ir_shape=node.weight_shape,
                    real_shape=real_shape, real_param_name=nome_real,
                )
            )

    real_orphans = sorted(set(named_param_shapes) - reais_usados)

    return ImportAudit(
        model_id=model_id,
        ir_nodes_with_weight=ir_com_peso,
        real_params_with_weight=len(named_param_shapes),
        matched=matched,
        ir_orphans=ir_orphans,
        real_orphans=real_orphans,
        shape_divergences=divergencias,
        ir_total_elems=graph.total_weight_elems(),
        real_total_elems=sum(
            _prod(s) for s in named_param_shapes.values()
        ),
    )


def _prod(shape: tuple[int, ...]) -> int:
    n = 1
    for x in shape:
        n *= x
    return n


__all__ = ["ImportAudit", "WeightDivergence", "audit_against_real_weights"]
