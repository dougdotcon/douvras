"""Model Registry & Watcher (Metodo 12.1).

Normaliza `config.json` de familias diferentes para um ``ModelSpec`` unico, preservando
proveniencia, licenca e hash. Nada aqui interpreta o modelo: apenas registra o que foi
declarado e de onde veio.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from douvras_core.paths import project_root
from douvras_core.status import Finding, Status


class UnsupportedArchitecture(ValueError):
    """A arquitetura declarada nao tem construtor de IR conhecido.

    Falhar explicitamente e preferivel a produzir um grafo silenciosamente errado
    (ADR-0001, consequencias negativas).
    """


class ProvenanceStatus:
    FETCHED = "FETCHED"  # baixado da fonte, hash registrado
    TRANSCRIBED_UNVERIFIED = "TRANSCRIBED_UNVERIFIED"  # transcrito, ver GAP G-008
    CLIENT_SUPPLIED = "CLIENT_SUPPLIED"  # enviado pelo cliente, nao redistribuivel


@dataclass(frozen=True)
class Provenance:
    source_url: str | None
    provenance: str
    sha256: str | None = None
    retrieved_at: str | None = None

    @property
    def verified(self) -> bool:
        return self.provenance == ProvenanceStatus.FETCHED and bool(self.sha256)

    @property
    def status(self) -> Status:
        return Status.OBSERVATION if self.verified else Status.ASSUMPTION

    @property
    def gaps(self) -> tuple[str, ...]:
        return () if self.verified else ("G-008",)


@dataclass(frozen=True)
class MoESpec:
    num_experts: int
    experts_per_token: int
    expert_intermediate_size: int
    shared_experts: int = 0

    @property
    def sparsity(self) -> float:
        return self.experts_per_token / self.num_experts


@dataclass(frozen=True)
class ModelSpec:
    """Descricao canonica de um modelo decoder-only.

    Campos derivados de `config.json`. Nenhum peso e lido: o Atlas roda sobre metadados
    (restricao R1 e politica de IP do Metodo 13.6).
    """

    id: str
    family: str
    version_label: str
    architecture: str

    hidden_size: int
    num_layers: int
    num_heads: int
    num_kv_heads: int
    head_dim: int
    intermediate_size: int
    vocab_size: int
    max_position: int

    norm_type: str = "rmsnorm"
    norms_per_layer: int = 2
    mlp_type: str = "swiglu"
    position_type: str = "rope"
    rope_theta: float = 10000.0
    tie_word_embeddings: bool = False
    qkv_bias: bool = False
    o_bias: bool = False
    mlp_bias: bool = False
    sliding_window: int | None = None
    moe: MoESpec | None = None

    release_date: str | None = None
    license: str | None = None
    published_params: int | None = None
    hf_repo: str | None = None
    default_dtype: str = "bf16"
    provenance: Provenance = field(
        default_factory=lambda: Provenance(None, ProvenanceStatus.TRANSCRIBED_UNVERIFIED)
    )
    raw_config: Mapping[str, Any] = field(default_factory=dict, repr=False)

    # -- propriedades derivadas -----------------------------------------------------
    @property
    def attention_type(self) -> str:
        if self.num_kv_heads == self.num_heads:
            return "mha"
        if self.num_kv_heads == 1:
            return "mqa"
        return "gqa"

    @property
    def gqa_ratio(self) -> int:
        return self.num_heads // self.num_kv_heads

    @property
    def kv_dim(self) -> int:
        return self.num_kv_heads * self.head_dim

    @property
    def q_dim(self) -> int:
        return self.num_heads * self.head_dim

    @property
    def mlp_gates(self) -> int:
        """Numero de projecoes de entrada do MLP: 2 para *GLU, 1 para MLP classico."""
        return 2 if self.mlp_type in ("swiglu", "geglu") else 1

    @property
    def is_moe(self) -> bool:
        return self.moe is not None

    @property
    def release_order_key(self) -> str:
        return self.release_date or "0000-00-00"

    def param_count(self) -> int:
        """Contagem analitica de parametros. Base do teste-ouro E-001."""
        d, L, I, V = self.hidden_size, self.num_layers, self.intermediate_size, self.vocab_size
        embed = V * d
        out_head = 0 if self.tie_word_embeddings else V * d

        attn = d * self.q_dim + 2 * d * self.kv_dim + self.q_dim * d
        if self.qkv_bias:
            attn += self.q_dim + 2 * self.kv_dim
        if self.o_bias:
            attn += d

        if self.moe is not None:
            m = self.moe
            per_expert = (m.expert_intermediate_size * d) * (self.mlp_gates + 1)
            mlp = m.num_experts * per_expert + d * m.num_experts  # + router
            if m.shared_experts:
                mlp += m.shared_experts * (I * d) * (self.mlp_gates + 1)
        else:
            mlp = (I * d) * (self.mlp_gates + 1)
        if self.mlp_bias:
            mlp += I * self.mlp_gates + d

        norms = self.norms_per_layer * d
        return embed + out_head + L * (attn + mlp + norms) + d

    def param_finding(self) -> Finding:
        p = self.provenance
        return Finding(
            name=f"{self.id}.params",
            value=self.param_count(),
            status=Status(min(int(Status.MODEL), int(p.status))),
            unit="params",
            assumptions=("A-001",) + (("A-009",) if not p.verified else ()),
            gaps=("G-001",) + p.gaps,
            note="derivado analiticamente do config; ver ADR-0001",
        )

    # -- serializacao ---------------------------------------------------------------
    def as_dict(self) -> dict[str, Any]:
        out = {
            k: v
            for k, v in self.__dict__.items()
            if k not in ("raw_config", "provenance", "moe")
        }
        out["attention_type"] = self.attention_type
        out["provenance"] = self.provenance.__dict__
        out["moe"] = self.moe.__dict__ if self.moe else None
        out["derived_params"] = self.param_count()
        return out


# --------------------------------------------------------------------------------------
# Normalizacao de config.json por familia
# --------------------------------------------------------------------------------------

_MLP_BY_HIDDEN_ACT = {
    "silu": "swiglu",
    "swish": "swiglu",
    "gelu": "geglu",
    "gelu_pytorch_tanh": "geglu",
    "gelu_new": "geglu",
    "relu": "mlp",
    "relu2": "mlp",
}

#: Arquiteturas HF cobertas pelo construtor de IR (ADR-0001).
SUPPORTED_ARCHITECTURES = {
    "LlamaForCausalLM",
    "MistralForCausalLM",
    "MixtralForCausalLM",
    "Qwen2ForCausalLM",
    "Phi3ForCausalLM",
    "Gemma2ForCausalLM",
}


def normalize_config(config: Mapping[str, Any], meta: Mapping[str, Any]) -> ModelSpec:
    """Converte um `config.json` estilo Hugging Face em ``ModelSpec``.

    Levanta ``UnsupportedArchitecture`` quando a arquitetura nao tem mapeamento conhecido,
    em vez de adivinhar campos.
    """
    archs = config.get("architectures") or []
    arch = archs[0] if archs else config.get("model_type", "unknown")
    if arch not in SUPPORTED_ARCHITECTURES:
        raise UnsupportedArchitecture(
            f"{meta.get('id', '?')}: arquitetura {arch!r} sem construtor de IR. "
            f"Suportadas: {sorted(SUPPORTED_ARCHITECTURES)}"
        )

    d = int(config["hidden_size"])
    heads = int(config["num_attention_heads"])
    kv_heads = int(config.get("num_key_value_heads", heads))
    head_dim = int(config.get("head_dim") or d // heads)

    hidden_act = str(config.get("hidden_act") or config.get("hidden_activation") or "silu")
    mlp_type = _MLP_BY_HIDDEN_ACT.get(hidden_act, "swiglu")

    moe = None
    if config.get("num_local_experts") or config.get("num_experts"):
        n_exp = int(config.get("num_local_experts") or config["num_experts"])
        top_k = int(config.get("num_experts_per_tok") or config.get("num_experts_per_token") or 2)
        exp_i = int(config.get("moe_intermediate_size") or config["intermediate_size"])
        moe = MoESpec(n_exp, top_k, exp_i, int(config.get("n_shared_experts") or 0))

    # Gemma-2 aplica pre e post norm em atencao e em MLP.
    norms_per_layer = 4 if arch == "Gemma2ForCausalLM" else 2
    # Qwen2 usa bias em Q/K/V e nao em O.
    qkv_bias = bool(config.get("attention_bias", False)) or arch == "Qwen2ForCausalLM"

    prov = Provenance(
        source_url=meta.get("source_url"),
        provenance=meta.get("provenance", ProvenanceStatus.TRANSCRIBED_UNVERIFIED),
        sha256=meta.get("sha256"),
        retrieved_at=meta.get("retrieved_at"),
    )

    return ModelSpec(
        id=str(meta["id"]),
        family=str(meta["family"]),
        version_label=str(meta.get("version_label", "")),
        architecture=arch,
        hidden_size=d,
        num_layers=int(config["num_hidden_layers"]),
        num_heads=heads,
        num_kv_heads=kv_heads,
        head_dim=head_dim,
        intermediate_size=int(config["intermediate_size"]),
        vocab_size=int(config["vocab_size"]),
        max_position=int(config.get("max_position_embeddings", 0)),
        norm_type="rmsnorm" if "rms_norm_eps" in config else "layernorm",
        norms_per_layer=norms_per_layer,
        mlp_type=mlp_type,
        position_type="rope",
        rope_theta=float(config.get("rope_theta", 10000.0)),
        tie_word_embeddings=bool(config.get("tie_word_embeddings", False)),
        qkv_bias=qkv_bias,
        o_bias=bool(config.get("attention_bias", False)) and arch != "Qwen2ForCausalLM",
        mlp_bias=bool(config.get("mlp_bias", False)),
        sliding_window=config.get("sliding_window"),
        moe=moe,
        release_date=meta.get("release_date"),
        license=meta.get("license"),
        published_params=meta.get("published_params"),
        hf_repo=meta.get("hf_repo"),
        default_dtype=meta.get("default_dtype", "bf16"),
        provenance=prov,
        raw_config=dict(config),
    )


# --------------------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------------------

CORPUS_DIR = project_root("silicon-atlas") / "corpus" / "models"


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Registry:
    """Indice de modelos registrados, carregado de arquivos JSON do corpus."""

    specs: dict[str, ModelSpec] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, corpus_dir: Path | None = None) -> "Registry":
        corpus = Path(corpus_dir or CORPUS_DIR)
        reg = cls()
        for path in sorted(corpus.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            meta = dict(doc.get("douvras") or {})
            meta.setdefault("id", path.stem)
            try:
                spec = normalize_config(doc["config"], meta)
            except (UnsupportedArchitecture, KeyError) as exc:
                reg.errors[str(meta["id"])] = str(exc)
                continue
            reg.specs[spec.id] = spec
        return reg

    def __iter__(self) -> Iterator[ModelSpec]:
        return iter(self.sorted())

    def __len__(self) -> int:
        return len(self.specs)

    def __getitem__(self, model_id: str) -> ModelSpec:
        if model_id not in self.specs:
            raise KeyError(
                f"modelo {model_id!r} nao registrado. Disponiveis: {sorted(self.specs)}"
            )
        return self.specs[model_id]

    def sorted(self) -> list[ModelSpec]:
        return sorted(self.specs.values(), key=lambda s: (s.family, s.release_order_key, s.id))

    def family(self, name: str) -> list[ModelSpec]:
        """Versoes de uma familia em ordem cronologica de release."""
        return sorted(
            (s for s in self.specs.values() if s.family == name),
            key=lambda s: s.release_order_key,
        )

    def families(self) -> list[str]:
        return sorted({s.family for s in self.specs.values()})

    def unverified(self) -> list[ModelSpec]:
        return [s for s in self.specs.values() if not s.provenance.verified]


# --------------------------------------------------------------------------------------
# Watcher: busca de config upstream (opcional, exige rede)
# --------------------------------------------------------------------------------------

HF_CONFIG_URL = "https://huggingface.co/{repo}/resolve/main/config.json"


def hf_token() -> str | None:
    """Token do Hugging Face, se houver.

    Modelos com licenca restrita (`meta-llama/*`, `google/gemma-*`) devolvem 401 sem token,
    **mesmo para o `config.json`**. Ler o token do ambiente permite fechar `G-008` para eles
    sem mudar codigo — mas exige que a conta tenha aceitado a licenca de cada repositorio.
    Contornar o gate nao e opcao: a restricao e do detentor do modelo.
    """
    import os
    from pathlib import Path as _P

    for var in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    cache = _P.home() / ".cache" / "huggingface" / "token"
    return cache.read_text(encoding="utf-8").strip() if cache.exists() else None


def fetch_hf_config(repo: str, timeout: float = 20.0) -> tuple[dict[str, Any], str, str]:
    """Baixa `config.json` de um repositorio Hugging Face.

    Devolve ``(config, sha256, url)``. Usado por ``atlas registry verify`` para fechar
    a lacuna G-008. Requer rede; nao e chamado no caminho principal.
    """
    import urllib.request

    url = HF_CONFIG_URL.format(repo=repo)
    headers = {"User-Agent": "douvras-silicon-atlas/0.1"}
    tok = hf_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - url fixa
        text = resp.read().decode("utf-8")
    return json.loads(text), sha256_of(text), url


#: Campos do `ModelSpec` que descrevem a arquitetura e alimentam a IR. Sao eles que a
#: verificacao compara — nao as chaves cruas do `config.json`. Metadados de catalogo
#: (`license`, `release_date`, `hf_repo`, proveniencia) ficam de fora porque nao entram em
#: nenhum numero derivado.
ARCHITECTURAL_FIELDS: tuple[str, ...] = (
    "architecture",
    "hidden_size",
    "num_layers",
    "num_heads",
    "num_kv_heads",
    "head_dim",
    "intermediate_size",
    "vocab_size",
    "max_position",
    "norm_type",
    "norms_per_layer",
    "mlp_type",
    "position_type",
    "rope_theta",
    "tie_word_embeddings",
    "qkv_bias",
    "o_bias",
    "mlp_bias",
    "sliding_window",
)


def verify_spec(spec: ModelSpec, repo: str | None = None) -> dict[str, Any]:
    """Confronta a transcricao local com o `config.json` upstream.

    A comparacao **nao** e byte a byte entre os dois JSON, e a razao importa. O corpus e uma
    transcricao deliberadamente parcial: registra o que o construtor de IR consome e ignora
    `bos_token_id`, `torch_dtype`, `transformers_version` e afins (decisao `D-006`). Comparar a
    uniao das chaves faria `matches` ser sempre falso — uma verificacao que estruturalmente nao
    pode passar nao fecha lacuna nenhuma, so produz a aparencia de rigor.

    O que se compara e o **`ModelSpec` normalizado** dos dois lados. Se os dois normalizam para
    a mesma arquitetura, a transcricao e fiel em tudo que o sistema usa — e a contagem de
    parametros, o roofline e a particao a jusante sao os mesmos que sairiam do arquivo original.
    Campos presentes upstream e ausentes localmente aparecem como contexto, nunca como falha.

    Recusa modelos marcados como ``CLIENT_SUPPLIED``: enviar a arquitetura de um cliente para um
    servico externo seria exatamente a ameaca S-003 do THREAT_MODEL, e nenhuma conveniencia de
    verificacao justifica.
    """
    if spec.provenance.provenance == ProvenanceStatus.CLIENT_SUPPLIED:
        raise PermissionError(
            f"{spec.id}: modelo fornecido por cliente nao pode ser verificado contra servico "
            f"externo (THREAT_MODEL S-003). Verifique a proveniencia junto ao proprio cliente."
        )
    repo = repo or spec.hf_repo
    if not repo:
        raise ValueError(
            f"{spec.id}: sem repositorio upstream. Declare `hf_repo` no bloco douvras do corpus "
            f"ou passe --repo <org/nome>."
        )
    upstream, digest, url = fetch_hf_config(repo)

    meta = {"id": spec.id, "family": spec.family, "version_label": spec.version_label}
    try:
        upstream_spec = normalize_config(upstream, meta)
    except UnsupportedArchitecture as exc:
        return {
            "model": spec.id,
            "repo": repo,
            "url": url,
            "sha256": digest,
            "retrieved_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
            "matches": False,
            "divergences": {"architecture": {"local": spec.architecture, "upstream": str(exc)}},
            "not_transcribed": [],
            "derived_params": {"local": spec.param_count(), "upstream": None},
        }

    divergences = {
        f: {"local": getattr(spec, f), "upstream": getattr(upstream_spec, f)}
        for f in ARCHITECTURAL_FIELDS
        if getattr(spec, f) != getattr(upstream_spec, f)
    }
    if (spec.moe is None) != (upstream_spec.moe is None) or (
        spec.moe and upstream_spec.moe and spec.moe.__dict__ != upstream_spec.moe.__dict__
    ):
        divergences["moe"] = {
            "local": spec.moe.__dict__ if spec.moe else None,
            "upstream": upstream_spec.moe.__dict__ if upstream_spec.moe else None,
        }

    local_params, upstream_params = spec.param_count(), upstream_spec.param_count()
    return {
        "model": spec.id,
        "repo": repo,
        "url": url,
        "sha256": digest,
        "retrieved_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "matches": not divergences,
        "divergences": divergences,
        # Contexto, nao falha: chaves que o upstream tem e a transcricao nao precisa.
        "not_transcribed": sorted(set(upstream) - set(spec.raw_config)),
        "derived_params": {
            "local": local_params,
            "upstream": upstream_params,
            "equal": local_params == upstream_params,
        },
    }


def record_verification(
    model_id: str, result: Mapping[str, Any], corpus_dir: Path | None = None
) -> Path:
    """Grava a proveniencia conferida no arquivo do corpus.

    Sem isto a verificacao seria um comando que imprime e esquece: a lacuna `G-008` fala do
    **corpus**, e so fecha quando o proprio corpus registra que foi conferido, com hash e data.
    Grava apenas quando `matches` e verdadeiro — registrar proveniencia de uma conferencia que
    divergiu seria pior que nao registrar nada.
    """
    if not result.get("matches"):
        raise ValueError(f"{model_id}: verificacao divergiu; proveniencia nao registrada")
    d = Path(corpus_dir or CORPUS_DIR)
    caminho = d / f"{model_id}.json"
    doc = json.loads(caminho.read_text(encoding="utf-8"))
    bloco = doc.setdefault("douvras", {})
    bloco["provenance"] = ProvenanceStatus.FETCHED
    bloco["source_url"] = result["url"]
    bloco["sha256"] = result["sha256"]
    bloco["retrieved_at"] = result["retrieved_at"]
    caminho.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return caminho


def corpus_integrity(registry: Registry) -> Finding:
    """Verificacao interna: parametros derivados vs. publicados (evidencia E-001).

    Sem nenhum modelo com contagem publicada o resultado e ``None``, nunca 0.0: um corpus em que
    nada foi verificado nao pode reportar "erro maximo 0,00 %" e fazer o portao O1 passar.
    """
    checked, worst, worst_id = 0, 0.0, ""
    for spec in registry:
        if not spec.published_params:
            continue
        checked += 1
        err = abs(spec.param_count() - spec.published_params) / spec.published_params
        if err > worst:
            worst, worst_id = err, spec.id
    if not checked:
        return Finding(
            name="corpus.param_error_max",
            value=None,
            status=Status.OPEN_GAP,
            unit="fracao",
            gaps=("G-008",),
            note=(
                f"nenhum dos {len(registry)} modelos declara contagem publicada: a integridade "
                f"do corpus nao foi verificada"
            ),
        )
    return Finding(
        name="corpus.param_error_max",
        value=worst,
        status=Status.COMPUTATIONAL_EVIDENCE,
        unit="fracao",
        note=(
            f"{checked} de {len(registry)} modelos com contagem publicada; "
            f"pior caso: {worst_id or 'n/a'}"
        ),
    )


__all__ = [
    "ModelSpec",
    "MoESpec",
    "Provenance",
    "ProvenanceStatus",
    "Registry",
    "UnsupportedArchitecture",
    "SUPPORTED_ARCHITECTURES",
    "normalize_config",
    "fetch_hf_config",
    "verify_spec",
    "corpus_integrity",
    "sha256_of",
    "CORPUS_DIR",
]
