"""Modelos de dispositivo e de energia.

Dois modelos distintos, deliberadamente:

* **GPU**: energia = tempo x TDP x overhead de servidor x PUE. E o que o data center paga,
  e nao exige adivinhar a microarquitetura do fabricante.
* **Alvo especializado**: energia = FLOPs x pJ/FLOP + bytes x pJ/byte por nivel de memoria.
  Necessario porque um ASIC hipotetico nao tem TDP publicado.

A assimetria entre os dois e uma premissa (A-003) e esta declarada em toda saida. Comparar
um modelo analitico otimista com uma medida real de GPU e o erro classico que produz
"100x" — ver CLAIM_LEDGER C-004.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from douvras_core.paths import project_root
from douvras_core.status import Finding, Status

from .ir.graph import Phase

#: Priors versionados deste atlas. Resolvido pelo projeto, nao por `parents[N]`: com dois
#: atlas sobre o mesmo `src/`, a contagem de niveis deixou de identificar o dono do arquivo.
CONFIG_DIR = project_root("silicon-atlas") / "config"


@dataclass(frozen=True)
class Device:
    """Alvo de execucao com picos, banda e custo declarados."""

    key: str
    name: str
    device_class: str
    peak_flops: dict[str, float]
    memory_bandwidth: float          # bytes/s
    memory_capacity: float           # bytes
    tdp_watts: float
    compute_efficiency: dict[str, float]
    bandwidth_efficiency: dict[str, float]
    server_overhead_factor: float = 1.3
    pue: float = 1.2
    hourly_cost_usd: float | None = None
    process_node_nm: int | None = None
    source: str = ""

    def peak(self, dtype: str) -> float:
        if dtype in self.peak_flops:
            return self.peak_flops[dtype]
        # ternario roda no datapath de int4/int8 do dispositivo generico
        for fallback in ("int4", "int8", "fp8", "bf16"):
            if fallback in self.peak_flops:
                return self.peak_flops[fallback]
        raise KeyError(f"{self.key}: sem pico declarado para {dtype!r}")

    def effective_compute(self, dtype: str, phase: Phase) -> float:
        return self.peak(dtype) * self.compute_efficiency.get(phase.value, 0.5)

    def effective_bandwidth(self, phase: Phase) -> float:
        return self.memory_bandwidth * self.bandwidth_efficiency.get(phase.value, 0.7)

    def ridge_point(self, dtype: str, phase: Phase) -> float:
        """Intensidade aritmetica na qual o dispositivo troca de regime (FLOP/byte)."""
        return self.effective_compute(dtype, phase) / self.effective_bandwidth(phase)

    def wall_power(self) -> float:
        """Potencia total atribuivel ao acelerador, incluindo host e refrigeracao."""
        return self.tdp_watts * self.server_overhead_factor * self.pue

    def energy_for(self, seconds: float) -> float:
        return seconds * self.wall_power()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "class": self.device_class,
            "memory_bandwidth_gbs": self.memory_bandwidth / 1e9,
            "memory_capacity_gb": self.memory_capacity / 1e9,
            "tdp_watts": self.tdp_watts,
            "wall_power_watts": self.wall_power(),
            "hourly_cost_usd": self.hourly_cost_usd,
            "process_node_nm": self.process_node_nm,
            "source": self.source,
        }


def load_devices(path: Path | None = None) -> dict[str, Device]:
    doc = json.loads((path or CONFIG_DIR / "devices.json").read_text(encoding="utf-8"))
    out: dict[str, Device] = {}
    for key, d in doc.items():
        if key.startswith("_"):
            continue
        out[key] = Device(
            key=key,
            name=d["name"],
            device_class=d.get("class", "gpu"),
            peak_flops={k: float(v) for k, v in d["peak_flops"].items()},
            memory_bandwidth=float(d["memory_bandwidth"]),
            memory_capacity=float(d["memory_capacity"]),
            tdp_watts=float(d["tdp_watts"]),
            compute_efficiency=dict(d["compute_efficiency"]),
            bandwidth_efficiency=dict(d["bandwidth_efficiency"]),
            server_overhead_factor=float(d.get("server_overhead_factor", 1.3)),
            pue=float(d.get("pue", 1.2)),
            hourly_cost_usd=d.get("hourly_cost_usd"),
            process_node_nm=d.get("process_node_nm"),
            source=d.get("source", ""),
        )
    return out


def get_device(key: str, path: Path | None = None) -> Device:
    devices = load_devices(path)
    if key not in devices:
        raise KeyError(f"dispositivo {key!r} desconhecido; disponiveis: {sorted(devices)}")
    return devices[key]


# --------------------------------------------------------------------------------------
# Modelo de energia para alvo especializado
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EnergyModel:
    """Energia por operacao e por byte, por nivel de memoria.

    Todos os valores sao `ASSUMPTION` (A-003) de ordem de grandeza, ancorados na literatura
    classica de energia por operacao escalada para nos avancados. Fechar G-004 antes de usar
    em decisao economica. A hierarquia relativa (HBM >> SRAM >> ROM >> MAC) e mais robusta
    que os valores absolutos, e e ela que sustenta a tese de endurecimento.
    """

    pj_per_flop: dict[str, float] = field(
        default_factory=lambda: {
            "fp32": 1.60,
            "bf16": 0.40,
            "fp16": 0.40,
            "fp8": 0.12,
            "int8": 0.10,
            "int4": 0.05,
            "ternary": 0.02,
        }
    )
    pj_per_byte_hbm: float = 40.0
    pj_per_byte_sram: float = 1.2
    pj_per_byte_rom: float = 0.30
    process_node_nm: int = 6

    def flop_energy(self, flops: float, dtype: str) -> float:
        return flops * self.pj_per_flop.get(dtype, 0.4) * 1e-12

    def byte_energy(self, nbytes: float, level: str = "hbm") -> float:
        pj = {"hbm": self.pj_per_byte_hbm, "sram": self.pj_per_byte_sram,
              "rom": self.pj_per_byte_rom}[level]
        return nbytes * pj * 1e-12

    def finding(self) -> Finding:
        return Finding(
            name="energy_model.pj_per_byte_hbm",
            value=self.pj_per_byte_hbm,
            status=Status.ASSUMPTION,
            unit="pJ/byte",
            assumptions=("A-003",),
            gaps=("G-004",),
            note="ordem de grandeza; hierarquia relativa e mais confiavel que o absoluto",
        )


DEFAULT_ENERGY = EnergyModel()


__all__ = ["Device", "EnergyModel", "DEFAULT_ENERGY", "load_devices", "get_device", "CONFIG_DIR"]
