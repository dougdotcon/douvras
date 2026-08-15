"""Registro de modelos reais do Hub, com proveniencia declarada.

A diferenca em relacao ao `registry` do Silicon Atlas nao e estrutural, e de honestidade sobre
a fonte. La, um `config.json` transcrito podia ser conferido contra a contagem de parametros
publicada — havia um falsificador barato. Aqui, os numeros vieram de documentos internos
(`docs/01`, `docs/02`), que por sua vez citam posts e cards de modelo. Sao **aproximados por
construcao**: "cerca de 0,5B" nao vira `500_000_000` sem alguem inventar sete digitos.

Por isso:

- `params_b` e declaradamente aproximado e carrega `A-101`;
- campos que a fonte nao afirma ficam `None`, nunca preenchidos por plausibilidade;
- `provenance` distingue o que foi conferido no upstream do que foi transcrito;
- enquanto nada for conferido, `G-108` fica aberta e todo derivado para em
  `CONDITIONAL_RESULT`.

`matlas registry verify` fecha `G-108` — e exige rede, portanto esta fora do caminho principal.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from douvras_core.paths import project_root
from douvras_core.status import Finding, Status

MODELS_DIR = project_root("model-atlas") / "corpus" / "models"


class Provenance(StrEnum):
    """De onde veio a ficha do modelo. Nunca inferida: declarada no corpus."""

    DOCUMENT_SECONDARY = "DOCUMENT_SECONDARY"
    UPSTREAM_VERIFIED = "UPSTREAM_VERIFIED"
    CLIENT_SUPPLIED = "CLIENT_SUPPLIED"


#: Bytes por parametro por esquema de quantizacao (media efetiva, incluindo escalas).
#: Valores de engenharia do formato GGUF, nao medicao — carregam `A-102`.
BYTES_PER_PARAM: dict[str, float] = {
    "f16": 2.0,
    "q8": 1.06,
    "q6": 0.82,
    "q5": 0.69,
    "q4": 0.56,
    "q3": 0.44,
}


class UnknownQuantization(KeyError):
    """Esquema de quantizacao fora da tabela declarada."""


@dataclass(frozen=True)
class HFModelSpec:
    id: str
    repo: str
    family: str
    provenance: Provenance
    source: str
    revision: str = "main"
    params_b: float | None = None
    architecture: str = ""
    context_len: int | None = None
    license: str = ""
    quantizations: tuple[str, ...] = ()
    weights_local: bool = False
    note: str = ""

    @property
    def params(self) -> int | None:
        """Contagem absoluta de parametros, quando a fonte permite. Aproximada (`A-101`)."""
        return int(self.params_b * 1e9) if self.params_b is not None else None

    def weights_bytes(self, quant: str) -> float | None:
        """Footprint dos pesos residentes. Nao inclui KV cache nem ativacoes.

        A omissao e deliberada e declarada: estimar KV cache exige numero de camadas e de
        cabecas KV, que este corpus nao tem com proveniencia. Publicar o total como se fosse
        o consumo real do processo seria o erro que o Silicon Atlas cometeu com `embed_tokens`
        e levou um ciclo para achar.
        """
        if quant not in BYTES_PER_PARAM:
            raise UnknownQuantization(quant)
        p = self.params
        return None if p is None else p * BYTES_PER_PARAM[quant]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "repo": self.repo,
            "revision": self.revision,
            "family": self.family,
            "params_b": self.params_b,
            "architecture": self.architecture,
            "context_len": self.context_len,
            "license": self.license,
            "provenance": str(self.provenance),
            "quantizations": list(self.quantizations),
            "weights_local": self.weights_local,
            "source": self.source,
        }


def _parse(doc: dict[str, Any]) -> HFModelSpec:
    d = doc.get("douvras", doc)
    return HFModelSpec(
        id=str(d["id"]),
        repo=str(d.get("repo", "")),
        family=str(d.get("family", "")),
        provenance=Provenance(d.get("provenance", "DOCUMENT_SECONDARY")),
        source=str(d.get("source", "")),
        revision=str(d.get("revision", "main")),
        params_b=(None if d.get("params_b") is None else float(d["params_b"])),
        architecture=str(d.get("architecture", "")),
        context_len=(None if d.get("context_len") is None else int(d["context_len"])),
        license=str(d.get("license", "")),
        quantizations=tuple(d.get("quantizations", ())),
        weights_local=bool(d.get("weights_local", False)),
        note=str(d.get("note", "")),
    )


class Registry:
    def __init__(self, specs: Sequence[HFModelSpec]):
        self.specs = list(specs)

    @classmethod
    def load(cls, directory: Path | None = None) -> "Registry":
        d = Path(directory or MODELS_DIR)
        return cls([_parse(json.loads(f.read_text(encoding="utf-8")))
                    for f in sorted(d.glob("*.json"))])

    def __len__(self) -> int:
        return len(self.specs)

    def __iter__(self) -> Iterator[HFModelSpec]:
        return iter(self.specs)

    def __getitem__(self, model_id: str) -> HFModelSpec:
        for s in self.specs:
            if s.id == model_id:
                return s
        raise KeyError(model_id)


# --------------------------------------------------------------------------------------
# Verificacao upstream (exige rede; fecha G-108)
# --------------------------------------------------------------------------------------

HF_API_URL = "https://huggingface.co/api/models/{repo}"
HF_CONFIG_URL = "https://huggingface.co/{repo}/resolve/main/config.json"

#: Erro relativo tolerado entre `params_b` declarado e a contagem real do checkpoint.
#: A ficha vem de documento que diz "cerca de"; exigir igualdade exata reprovaria uma
#: transcricao honesta. 5 % separa "arredondado" de "errado".
PARAM_TOLERANCE = 0.05


class UpstreamUnavailable(RuntimeError):
    """O repositorio nao respondeu, nao existe, ou exige credencial."""


def _fetch_json(url: str, timeout: float = 20.0) -> tuple[dict[str, Any], str]:
    import urllib.error
    import urllib.request

    from silicon_atlas.registry import hf_token, sha256_of

    headers = {"User-Agent": "douvras-model-atlas/0.1"}
    tok = hf_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        with urllib.request.urlopen(  # noqa: S310 - host fixo
            urllib.request.Request(url, headers=headers), timeout=timeout
        ) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise UpstreamUnavailable(f"HTTP {exc.code} em {url}") from exc
    except OSError as exc:
        raise UpstreamUnavailable(f"rede indisponivel: {exc}") from exc
    return json.loads(text), sha256_of(text)


def verify_spec(spec: HFModelSpec) -> dict[str, Any]:
    """Confronta a ficha local com o Hub.

    A ficha deste corpus veio de documento secundario e tem campos deliberadamente nulos
    (`D-108`): preencher `context_len` ou `license` por plausibilidade seria inventar
    proveniencia. Entao a verificacao faz duas coisas distintas, e o resultado as separa:

    - **confere** os campos que a ficha afirma — divergencia aqui e erro de transcricao;
    - **descobre** os campos que a ficha deixou nulos — nao e divergencia, e a lacuna fechando.

    `params_b` e comparado com tolerancia (`PARAM_TOLERANCE`), porque a fonte diz "cerca de"
    e exigir igualdade exata reprovaria uma transcricao correta.
    """
    if spec.provenance is Provenance.CLIENT_SUPPLIED:
        raise PermissionError(
            f"{spec.id}: modelo de cliente nao vai para servico externo (THREAT_MODEL S-101)."
        )
    if not spec.repo:
        raise ValueError(f"{spec.id}: sem `repo` declarado no corpus.")

    info, digest = _fetch_json(HF_API_URL.format(repo=spec.repo))
    try:
        config, _ = _fetch_json(HF_CONFIG_URL.format(repo=spec.repo))
    except UpstreamUnavailable:
        config = {}

    params_up = (info.get("safetensors") or {}).get("total")
    archs = (info.get("config") or {}).get("architectures") or config.get("architectures") or []
    upstream = {
        "params_b": round(params_up / 1e9, 4) if params_up else None,
        "architecture": archs[0] if archs else None,
        "context_len": config.get("max_position_embeddings"),
        "license": (info.get("cardData") or {}).get("license") or "",
    }

    divergencias: dict[str, Any] = {}
    descobertos: dict[str, Any] = {}
    for campo, valor_up in upstream.items():
        local = getattr(spec, campo)
        vazio = local in (None, "")
        if valor_up in (None, ""):
            continue
        if vazio:
            descobertos[campo] = valor_up
        elif campo == "params_b":
            erro = abs(float(local) - float(valor_up)) / float(valor_up)
            if erro > PARAM_TOLERANCE:
                divergencias[campo] = {
                    "local": local, "upstream": valor_up, "erro_relativo": round(erro, 4)
                }
        elif str(local) != str(valor_up):
            divergencias[campo] = {"local": local, "upstream": valor_up}

    return {
        "model": spec.id,
        "repo": spec.repo,
        "url": HF_API_URL.format(repo=spec.repo),
        "sha256": digest,
        "retrieved_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "matches": not divergencias,
        "divergences": divergencias,
        "discovered": descobertos,
        "params_upstream": params_up,
    }


def record_verification(
    model_id: str, result: Mapping[str, Any], directory: Path | None = None
) -> Path:
    """Grava a ficha conferida no corpus: proveniencia, hash, data e campos descobertos.

    `G-108` fala do **corpus**; ela so fecha quando o corpus registra a conferencia. Recusa
    gravar se a verificacao divergiu — registrar proveniencia de uma conferencia reprovada
    seria pior que nao registrar nada.
    """
    if not result.get("matches"):
        raise ValueError(f"{model_id}: verificacao divergiu; proveniencia nao registrada")
    caminho = Path(directory or MODELS_DIR) / f"{model_id}.json"
    doc = json.loads(caminho.read_text(encoding="utf-8"))
    bloco = doc.setdefault("douvras", {})
    bloco.update(result.get("discovered") or {})
    bloco["provenance"] = str(Provenance.UPSTREAM_VERIFIED)
    bloco["source"] = result["url"]
    bloco["sha256"] = result["sha256"]
    bloco["retrieved_at"] = result["retrieved_at"]
    caminho.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return caminho


def corpus_provenance(reg: Registry) -> Finding:
    """Fracao do corpus conferida contra o upstream.

    Devolve `0.0` **declarado**, nao ausencia: zero verificado e um fato sobre o corpus, e o
    numero que deve envergonhar o proximo ciclo ate subir.
    """
    if not len(reg):
        return Finding("proveniencia_verificada", None, Status.OPEN_GAP, gaps=("G-108",))
    verificados = sum(1 for s in reg if s.provenance is Provenance.UPSTREAM_VERIFIED)
    frac = verificados / len(reg)
    return Finding(
        "proveniencia_verificada",
        round(frac, 4),
        Status.OBSERVATION if frac == 1.0 else Status.CONDITIONAL_RESULT,
        gaps=() if frac == 1.0 else ("G-108",),
        note=f"{verificados}/{len(reg)} fichas conferidas na fonte",
    )


def weights_available(reg: Registry) -> Finding:
    """Ha pesos baixados para executar alguma coisa?

    E o `Finding` do qual todo o resto depende: sem pesos, nenhuma capacidade e medida, e o
    assessment inteiro sai como ausencia declarada em vez de numero bonito.
    """
    n = sum(1 for s in reg if s.weights_local)
    return Finding(
        "modelos_com_pesos_locais",
        n,
        Status.OBSERVATION,
        unit="modelos",
        note="execucao real exige o extra [run] e download; ver ADR-0006",
    )


__all__ = [
    "HFModelSpec",
    "Registry",
    "Provenance",
    "BYTES_PER_PARAM",
    "UnknownQuantization",
    "corpus_provenance",
    "weights_available",
    "MODELS_DIR",
]
