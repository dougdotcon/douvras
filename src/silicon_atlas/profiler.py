"""Runtime Profiler (Metodo 12.5) — modelo roofline analitico, por fase.

Regra do modulo: **nunca reportar ganho apenas por FLOPs** (Metodo 18.3). Todo no carrega
tempo de computacao e tempo de memoria separados, e o relatorio diz de que lado do roofline
cada um cai. Em decode, quase tudo cai do lado da memoria — e essa e a informacao que decide
se endurecer aritmetica adianta.

Status maximo emitido: COMPUTATIONAL_EVIDENCE, rebaixado a CONDITIONAL_RESULT pelas lacunas
G-003 (roofline nao calibrado) e G-004 (energia nao medida).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from .hardware import Device
from .ir.graph import Graph, Node, OpKind, Phase, Workload
from douvras_core.status import Finding, Status


@dataclass(frozen=True)
class NodeCost:
    """Custo de um no sob workload e dispositivo declarados."""

    node_id: str
    role: str
    block: str
    kind: OpKind
    layer: int | None
    flops: float
    bytes_moved: float
    compute_time: float
    memory_time: float
    weight_bytes: float
    state_bytes: float

    @property
    def time(self) -> float:
        """Roofline: o no leva o maior dos dois tempos (sem sobreposicao entre nos)."""
        return max(self.compute_time, self.memory_time)

    @property
    def bound(self) -> str:
        return "compute" if self.compute_time >= self.memory_time else "memory"

    @property
    def intensity(self) -> float:
        return self.flops / self.bytes_moved if self.bytes_moved else float("inf")

    @property
    def utilization(self) -> float:
        """Fracao do tempo em que a unidade dominante fica ociosa em relacao ao outro recurso."""
        t = self.time
        return (min(self.compute_time, self.memory_time) / t) if t else 0.0


@dataclass
class PhaseProfile:
    """Perfil completo de uma fase (prefill ou decode) para um modelo em um dispositivo."""

    model_id: str
    device: Device
    workload: Workload
    weight_precision: str
    costs: list[NodeCost] = field(default_factory=list)
    #: Bytes de peso que precisam **residir** em memoria. Distinto do trafego de leitura por
    #: passo: MoE le top-k mas hospeda todos os experts, e a tabela de embeddings e lida por
    #: gather. Confundir os dois publicava `fits_in_device_memory: true` para um modelo de
    #: 93,4 GB numa placa de 80 GB (retratacao R-002, grupo D).
    resident_weight_bytes: float = 0.0

    # -- agregados ------------------------------------------------------------------
    @property
    def total_time(self) -> float:
        return sum(c.time for c in self.costs)

    @property
    def total_flops(self) -> float:
        return sum(c.flops for c in self.costs)

    @property
    def total_bytes(self) -> float:
        return sum(c.bytes_moved for c in self.costs)

    @property
    def weight_bytes(self) -> float:
        """Bytes de peso **lidos por invocacao**. Nao e footprint — ver `resident_weight_bytes`."""
        return sum(c.weight_bytes for c in self.costs)

    @property
    def state_bytes(self) -> float:
        return sum(c.state_bytes for c in self.costs)

    @property
    def memory_bound_share(self) -> float:
        t = self.total_time
        return sum(c.time for c in self.costs if c.bound == "memory") / t if t else 0.0

    @property
    def mean_intensity(self) -> float:
        return self.total_flops / self.total_bytes if self.total_bytes else float("inf")

    @property
    def tokens_per_second(self) -> float:
        """Tokens por segundo por dispositivo, com a granularidade correta por fase."""
        if self.total_time <= 0:
            return float("inf")
        tokens = (
            self.workload.batch * self.workload.prompt_len
            if self.workload.phase is Phase.PREFILL
            else self.workload.batch
        )
        return tokens / self.total_time

    @property
    def energy_joules(self) -> float:
        return self.device.energy_for(self.total_time)

    @property
    def energy_per_token(self) -> float:
        tokens = (
            self.workload.batch * self.workload.prompt_len
            if self.workload.phase is Phase.PREFILL
            else self.workload.batch
        )
        return self.energy_joules / tokens if tokens else float("inf")

    @property
    def fits_in_memory(self) -> bool:
        """Os pesos residentes cabem na memoria do dispositivo?

        Nao inclui KV cache, que escala com lote e contexto e e reportado a parte.
        """
        return self.resident_weight_bytes <= self.device.memory_capacity

    @property
    def memory_headroom(self) -> float:
        """Fracao da capacidade ainda livre depois dos pesos. Negativa quando nao cabe."""
        cap = self.device.memory_capacity
        return (cap - self.resident_weight_bytes) / cap if cap else 0.0

    # -- hotspots -------------------------------------------------------------------
    def group(self, key: Callable[[NodeCost], str]) -> dict[str, dict[str, float]]:
        agg: dict[str, dict[str, float]] = defaultdict(
            lambda: {"time": 0.0, "flops": 0.0, "bytes": 0.0, "count": 0.0}
        )
        for c in self.costs:
            g = agg[key(c)]
            g["time"] += c.time
            g["flops"] += c.flops
            g["bytes"] += c.bytes_moved
            g["count"] += 1
        total = self.total_time or 1.0
        for g in agg.values():
            g["share"] = g["time"] / total
        return dict(agg)

    def by_role(self) -> dict[str, dict[str, float]]:
        return self.group(lambda c: c.role)

    def by_kind(self) -> dict[str, dict[str, float]]:
        return self.group(lambda c: str(c.kind))

    def by_block_role(self) -> dict[str, dict[str, float]]:
        return self.group(lambda c: c.block.split(".")[-1])

    def hotspots(self, by: str = "role", top: int = 12) -> list[tuple[str, dict[str, float]]]:
        table = {"role": self.by_role, "kind": self.by_kind, "block": self.by_block_role}[by]()
        return sorted(table.items(), key=lambda kv: -kv[1]["time"])[:top]

    def block_time(self, block: str) -> float:
        return sum(c.time for c in self.costs if c.block == block)

    def block_share(self, block: str) -> float:
        t = self.total_time
        return self.block_time(block) / t if t else 0.0

    def role_share(self, role: str) -> float:
        t = self.total_time
        return sum(c.time for c in self.costs if c.role == role) / t if t else 0.0

    # -- saidas com status ----------------------------------------------------------
    def findings(self) -> list[Finding]:
        common = dict(
            status=Status.CONDITIONAL_RESULT,
            assumptions=("A-002", "A-005"),
            gaps=("G-003",),
        )
        out = [
            Finding(name=f"{self.model_id}.{self.workload.phase.value}.tokens_per_s",
                    value=self.tokens_per_second, unit="tok/s", **common),
            Finding(name=f"{self.model_id}.{self.workload.phase.value}.memory_bound_share",
                    value=self.memory_bound_share, unit="fracao do tempo", **common),
            Finding(name=f"{self.model_id}.{self.workload.phase.value}.arith_intensity",
                    value=self.mean_intensity, unit="FLOP/byte", **common),
        ]
        out.append(
            Finding(
                name=f"{self.model_id}.{self.workload.phase.value}.energy_per_token",
                value=self.energy_per_token,
                unit="J/token",
                status=Status.CONDITIONAL_RESULT,
                assumptions=("A-002", "A-003", "A-005"),
                gaps=("G-003", "G-004"),
                note="tempo roofline x potencia de parede (TDP x overhead x PUE)",
            )
        )
        return out

    def summary(self) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "device": self.device.key,
            "workload": self.workload.label(),
            "weight_precision": self.weight_precision,
            "total_time_s": self.total_time,
            "tokens_per_second": self.tokens_per_second,
            "total_flops": self.total_flops,
            "total_bytes": self.total_bytes,
            "weight_read_bytes_per_step": self.weight_bytes,
            "resident_weight_bytes": self.resident_weight_bytes,
            "kv_bytes": self.state_bytes,
            "mean_arithmetic_intensity": self.mean_intensity,
            "device_ridge_point": self.device.ridge_point(
                self.weight_precision, self.workload.phase
            ),
            "memory_bound_share": self.memory_bound_share,
            "energy_per_token_j": self.energy_per_token,
            "fits_in_device_memory": self.fits_in_memory,
            "memory_headroom": self.memory_headroom,
            "hotspots_by_role": {
                k: round(v["share"], 4) for k, v in self.hotspots("role", top=10)
            },
            "hotspots_by_block": {
                k: round(v["share"], 4) for k, v in self.hotspots("block", top=8)
            },
        }


def profile_node(
    node: Node, w: Workload, device: Device, weight_precision: str | None = None
) -> NodeCost:
    wp = weight_precision or node.weight_precision
    flops = node.flops(w)
    wb = node.read_weight_bytes(w, wp)
    sb = node.state_bytes(w)
    total_bytes = wb + node.activation_bytes(w) + sb
    # Operadores nao-aritmeticos e leves usam o datapath de ativacao, nao o de pesos.
    compute_dtype = wp if node.kind in (OpKind.LINEAR, OpKind.ROUTER) else w.activation_precision
    return NodeCost(
        node_id=node.id,
        role=node.role,
        block=node.block,
        kind=node.kind,
        layer=node.layer,
        flops=flops,
        bytes_moved=total_bytes,
        compute_time=flops / device.effective_compute(compute_dtype, w.phase),
        memory_time=total_bytes / device.effective_bandwidth(w.phase),
        weight_bytes=wb,
        state_bytes=sb,
    )


def profile(
    graph: Graph,
    workload: Workload,
    device: Device,
    weight_precision: str | None = None,
    precision_plan: dict[str, str] | None = None,
) -> PhaseProfile:
    """Perfila o grafo inteiro.

    ``precision_plan`` mapeia papel de operador -> precisao, permitindo perfilar um plano
    de quantizacao heterogeneo (ex.: MLP em int4, atencao em bf16).
    """
    prof = PhaseProfile(
        model_id=graph.model_id,
        device=device,
        workload=workload,
        weight_precision=weight_precision or "bf16",
    )
    resident = 0.0
    for node in graph:
        wp = (precision_plan or {}).get(node.role) or weight_precision or node.weight_precision
        prof.costs.append(profile_node(node, workload, device, wp))
        resident += node.weight_bytes(wp)
    prof.resident_weight_bytes = resident
    return prof


def profile_both_phases(
    graph: Graph,
    device: Device,
    batch: int = 1,
    prompt_len: int = 2048,
    context_len: int = 4096,
    weight_precision: str | None = None,
    precision_plan: dict[str, str] | None = None,
    activation_precision: str = "bf16",
) -> dict[str, PhaseProfile]:
    """Perfila prefill e decode sob o mesmo modelo e dispositivo.

    Separar as fases nao e detalhe de apresentacao: elas caem em lados opostos do roofline
    e recomendam hardware diferente. Um relatorio que reporta so uma delas esconde metade
    da decisao.
    """
    return {
        phase.value: profile(
            graph,
            Workload(
                phase=phase,
                batch=batch,
                prompt_len=prompt_len,
                context_len=context_len,
                activation_precision=activation_precision,
            ),
            device,
            weight_precision,
            precision_plan,
        )
        for phase in (Phase.PREFILL, Phase.DECODE)
    }


@dataclass
class ServingProfile:
    """Prefill e decode combinados no perfil de uma requisicao real.

    Existe porque nenhuma das duas fases isolada representa o custo que o cliente paga.
    Uma requisicao com prompt de 2k e 512 tokens gerados executa o prefill uma vez e o
    decode 512 vezes: e essa mistura que decide qual bloco merece silicio.
    """

    prefill: PhaseProfile
    decode: PhaseProfile
    gen_len: int = 512

    @property
    def model_id(self) -> str:
        return self.prefill.model_id

    @property
    def device(self) -> Device:
        return self.prefill.device

    @property
    def total_time(self) -> float:
        return self.prefill.total_time + self.gen_len * self.decode.total_time

    @property
    def decode_time_share(self) -> float:
        t = self.total_time
        return (self.gen_len * self.decode.total_time / t) if t else 0.0

    @property
    def tokens_per_request(self) -> int:
        return self.prefill.workload.batch * (self.prefill.workload.prompt_len + self.gen_len)

    @property
    def generated_tokens(self) -> int:
        return self.decode.workload.batch * self.gen_len

    @property
    def energy_joules(self) -> float:
        return self.device.energy_for(self.total_time)

    @property
    def energy_per_generated_token(self) -> float:
        g = self.generated_tokens
        return self.energy_joules / g if g else float("inf")

    @property
    def generated_tokens_per_second(self) -> float:
        return self.generated_tokens / self.total_time if self.total_time else float("inf")

    def by_role(self) -> dict[str, dict[str, float]]:
        """Participacao por papel na requisicao inteira, ponderada pelo numero de execucoes."""
        agg: dict[str, dict[str, float]] = defaultdict(
            lambda: {"time": 0.0, "flops": 0.0, "bytes": 0.0, "count": 0.0}
        )
        for prof, mult in ((self.prefill, 1.0), (self.decode, float(self.gen_len))):
            for role, data in prof.by_role().items():
                g = agg[role]
                g["time"] += data["time"] * mult
                g["flops"] += data["flops"] * mult
                g["bytes"] += data["bytes"] * mult
                g["count"] += data["count"]
        total = self.total_time or 1.0
        for g in agg.values():
            g["share"] = g["time"] / total
        return dict(agg)

    def hotspots(self, top: int = 12) -> list[tuple[str, dict[str, float]]]:
        return sorted(self.by_role().items(), key=lambda kv: -kv[1]["time"])[:top]

    def role_share(self, role: str) -> float:
        return self.by_role().get(role, {}).get("share", 0.0)

    def summary(self) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "device": self.device.key,
            "request": (
                f"prompt={self.prefill.workload.prompt_len} gen={self.gen_len} "
                f"B={self.prefill.workload.batch} ctx={self.decode.workload.context_len}"
            ),
            "total_time_s": self.total_time,
            "decode_time_share": self.decode_time_share,
            "generated_tokens_per_second": self.generated_tokens_per_second,
            "energy_per_generated_token_j": self.energy_per_generated_token,
            "hotspots": {k: round(v["share"], 4) for k, v in self.hotspots(10)},
        }

    def findings(self) -> list[Finding]:
        return [
            Finding(
                name=f"{self.model_id}.serving.decode_time_share",
                value=self.decode_time_share,
                status=Status.CONDITIONAL_RESULT,
                unit="fracao do tempo de requisicao",
                assumptions=("A-002", "A-005"),
                gaps=("G-003", "G-009"),
                note="mistura prefill/decode assumida; telemetria real fecharia G-009",
            ),
            Finding(
                name=f"{self.model_id}.serving.energy_per_token",
                value=self.energy_per_generated_token,
                status=Status.CONDITIONAL_RESULT,
                unit="J/token gerado",
                assumptions=("A-002", "A-003", "A-005"),
                gaps=("G-003", "G-004", "G-009"),
            ),
        ]


def serving_profile(
    graph: Graph,
    device: Device,
    *,
    batch: int = 1,
    prompt_len: int = 2048,
    gen_len: int = 512,
    context_len: int | None = None,
    weight_precision: str | None = None,
    precision_plan: dict[str, str] | None = None,
    activation_precision: str = "bf16",
) -> ServingProfile:
    """Perfil de requisicao completa. Contexto default = prompt + metade da geracao."""
    ctx = context_len if context_len is not None else prompt_len + gen_len // 2
    phases = profile_both_phases(
        graph,
        device,
        batch=batch,
        prompt_len=prompt_len,
        context_len=ctx,
        weight_precision=weight_precision,
        precision_plan=precision_plan,
        activation_precision=activation_precision,
    )
    return ServingProfile(prefill=phases["prefill"], decode=phases["decode"], gen_len=gen_len)


def cost_share_by_block(prof: PhaseProfile) -> dict[str, float]:
    """Fracao do tempo por bloco nomeado (L0.attention, L0.mlp, head...)."""
    total = prof.total_time or 1.0
    agg: dict[str, float] = defaultdict(float)
    for c in prof.costs:
        agg[c.block] += c.time
    return {k: v / total for k, v in agg.items()}


def dominant_roles(prof: PhaseProfile, threshold: float = 0.80) -> list[tuple[str, float]]:
    """Menor conjunto de papeis que soma ``threshold`` do tempo — o 20/80 do Metodo 4.5."""
    ranked = sorted(prof.by_role().items(), key=lambda kv: -kv[1]["share"])
    out: list[tuple[str, float]] = []
    acc = 0.0
    for role, data in ranked:
        out.append((role, data["share"]))
        acc += data["share"]
        if acc >= threshold:
            break
    return out


def concentration_index(prof: PhaseProfile) -> float:
    """Indice de concentracao (Herfindahl) das participacoes por papel.

    Proximo de 1 -> um unico padrao domina (bom candidato a hardening).
    Proximo de 0 -> custo espalhado (endurecer parte nao move o total).
    """
    return sum(v["share"] ** 2 for v in prof.by_role().values())


__all__ = [
    "NodeCost",
    "PhaseProfile",
    "ServingProfile",
    "profile",
    "profile_node",
    "profile_both_phases",
    "serving_profile",
    "cost_share_by_block",
    "dominant_roles",
    "concentration_index",
]
