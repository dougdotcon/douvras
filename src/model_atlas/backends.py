"""Execucao real: um modelo local respondendo o BR-Agent-Bench.

Fecha `G-101` (nenhuma execucao real) e `G-102` (sem telemetria). Fica fora do caminho
principal por decisao (`ADR-0006`): o ciclo inteiro roda sem isto.

## Por que `llama-server` e nao `llama-cli`

Parsear a saida de terminal de um binario interativo e frageis por natureza — banner, barra de
progresso e o proprio prompt ecoado se misturam ao texto gerado. O servidor devolve JSON com o
texto **e** com `timings` (prompt_ms, predicted_ms, tokens por segundo), que e exatamente a
telemetria que `G-102` pede. Medicao de latencia extraida de regex sobre stdout seria numero de
aparencia respeitavel com procedencia ruim.

## O prompt e parte do instrumento

Um escore de agente depende do prompt tanto quanto do modelo. Trocar "responda em JSON" por
"responda apenas com JSON, sem explicacao" move o resultado de `structured_output` sozinho. Por
isso o prompt e **versionado** (`PROMPT_VERSION`) e entra no relatorio: comparar escores de
prompts diferentes e comparar instrumentos diferentes.

Nenhuma tentativa de reparo. Se o modelo devolve algo que nao da para interpretar como acao, o
passo vira uma resposta em texto e o grader julga — que e o comportamento honesto. Repetir a
chamada ate sair JSON valido mediria a persistencia do harness, nao a capacidade do modelo.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from douvras_core.paths import REPO_ROOT

from .tasks import EvalTask, Step, StepKind

#: Versao do prompt de agente. Muda o escore; portanto muda o instrumento.
#:
#: `v1` punha o contrato de resposta no inicio e a lista de ferramentas no fim. O modelo
#: continuava a lista — `"- enviar_e-mail\n- enviar_e-mail_com_resposta"` — em vez de agir:
#: o contexto imediato antes da geracao era um enumerado, e ele enumerou. `v2` move o
#: contrato para o fim, colado na geracao.
#:
#: A revisao foi feita **antes** de qualquer execucao completa, por defeito estrutural
#: observado em quatro tarefas, e esta declarada aqui. Iterar o prompt olhando o escore ate
#: ele subir seria outra coisa: seria ajustar o instrumento ao resultado.
PROMPT_VERSION = "agent-ptbr-v2"

#: Onde o binario e o modelo ficam por padrao. Fora do versionamento (ver `.gitignore`).
LOCAL_BIN = REPO_ROOT / ".local" / "bin"
LOCAL_MODELS = REPO_ROOT / ".local" / "models"


class BackendUnavailable(RuntimeError):
    """Runtime ou pesos ausentes. Nao e falha do modelo: e ausencia de execucao."""


def find_server() -> Path:
    env = os.environ.get("LLAMA_SERVER")
    if env and Path(env).is_file():
        return Path(env)
    for nome in ("llama-server.exe", "llama-server"):
        p = LOCAL_BIN / nome
        if p.is_file():
            return p
    raise BackendUnavailable(
        f"llama-server nao encontrado em {LOCAL_BIN}. Baixe o release do llama.cpp ou "
        f"aponte LLAMA_SERVER para o executavel."
    )


def find_model(nome: str) -> Path:
    p = Path(nome)
    if p.is_file():
        return p
    achados = sorted(LOCAL_MODELS.glob(f"*{nome}*.gguf")) if LOCAL_MODELS.is_dir() else []
    if not achados:
        raise BackendUnavailable(f"nenhum .gguf casando com {nome!r} em {LOCAL_MODELS}")
    return achados[0]


# --------------------------------------------------------------------------------------
# Servidor
# --------------------------------------------------------------------------------------


@dataclass
class Timings:
    """Telemetria acumulada da execucao. E o que fecha `G-102`."""

    prompt_ms: float = 0.0
    predict_ms: float = 0.0
    prompt_tokens: int = 0
    predicted_tokens: int = 0
    calls: int = 0
    ttft_samples: list[float] = field(default_factory=list)

    def add(self, t: Mapping[str, Any]) -> None:
        self.prompt_ms += float(t.get("prompt_ms", 0.0))
        self.predict_ms += float(t.get("predicted_ms", 0.0))
        self.prompt_tokens += int(t.get("prompt_n", 0) or 0)
        self.predicted_tokens += int(t.get("predicted_n", 0) or 0)
        self.calls += 1
        # TTFT aproximado pelo tempo de processamento do prompt: e o intervalo entre enviar e
        # o primeiro token sair. Sem streaming nao da para medir direto, e chamar isso de
        # "TTFT medido" sem a ressalva seria vender precisao que nao existe.
        if t.get("prompt_ms"):
            self.ttft_samples.append(float(t["prompt_ms"]) / 1000.0)

    @property
    def tokens_per_s(self) -> float | None:
        return (self.predicted_tokens / (self.predict_ms / 1000.0)) if self.predict_ms else None

    @property
    def ttft_s(self) -> float | None:
        return sum(self.ttft_samples) / len(self.ttft_samples) if self.ttft_samples else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "chamadas": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "tokens_gerados": self.predicted_tokens,
            "tokens_por_segundo": round(self.tokens_per_s, 2) if self.tokens_per_s else None,
            "ttft_s": round(self.ttft_s, 3) if self.ttft_s else None,
            "tempo_total_s": round((self.prompt_ms + self.predict_ms) / 1000.0, 1),
        }


class LlamaServer:
    """Sobe `llama-server`, fala HTTP, derruba no fim."""

    def __init__(self, model: Path, port: int = 8177, ctx: int = 4096, threads: int | None = None):
        self.model = model
        self.port = port
        self.ctx = ctx
        self.threads = threads or max(1, (os.cpu_count() or 4) - 1)
        self.proc: subprocess.Popen | None = None
        self.timings = Timings()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "LlamaServer":
        exe = find_server()
        self.proc = subprocess.Popen(
            [
                str(exe), "-m", str(self.model),
                "--port", str(self.port), "-c", str(self.ctx),
                "-t", str(self.threads), "--no-warmup",
                # Sem `--jinja` o servidor **ignora** o template embutido no GGUF e adivinha um
                # formato conhecido. O Tucano usa `<instruction>...</instruction>`, que nao esta
                # entre os palpites: o resultado era repeticao degenerada, e o escore colhido
                # assim mediria o palpite do harness, nao o modelo.
                "--jinja",
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(180):
            if self.proc.poll() is not None:
                raise BackendUnavailable("llama-server encerrou durante a inicializacao")
            try:
                with urllib.request.urlopen(f"{self.url}/health", timeout=2) as r:
                    if r.status == 200:
                        return self
            except (urllib.error.URLError, OSError):
                time.sleep(1)
        self.__exit__(None, None, None)
        raise BackendUnavailable("llama-server nao respondeu /health em 180 s")

    def __exit__(self, *exc: object) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:  # pragma: no cover
                self.proc.kill()
        self.proc = None

    def complete(self, prompt: str, max_tokens: int = 256) -> str:
        """Completa um prompt **cru**, sem passar por template de chat.

        Deliberado: o template embutido no GGUF do Tucano-2b4-Instruct esta errado (ver
        `TUCANO_FORMAT_NOTE`), e usar `/v1/chat/completions` significa aceitar esse template.
        O formato correto e montado por `render_tucano_prompt`.
        """
        corpo = json.dumps(
            {
                "prompt": prompt,
                "n_predict": max_tokens,
                # Temperatura zero: o benchmark precisa ser reexecutavel. Amostragem faria o
                # escore variar entre execucoes e `F4` disparar por construcao.
                "temperature": 0.0,
                "seed": 20260815,
                "cache_prompt": True,
                # Sem EOS confiavel, o modelo continua ate o teto de tokens e o tempo por
                # tarefa triplica. Estas paradas cortam no limite natural do turno; o parser
                # ja usa o primeiro objeto JSON, entao nao alteram o veredicto.
                "stop": ["<instruction>", "\nObservacao:", "\nTarefa:"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/completion", data=corpo, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            doc = json.loads(r.read().decode("utf-8"))
        if doc.get("timings"):
            self.timings.add(doc["timings"])
        return doc.get("content") or ""

    def chat(self, messages: Sequence[Mapping[str, str]], max_tokens: int = 256) -> str:
        """Deixa o servidor aplicar o template do proprio GGUF.

        So e legitimo para modelos cujo template foi **verificado** (`RB-102`). Para o Tucano
        este caminho produz repeticao degenerada, e o escore mediria o template, nao o modelo.
        """
        corpo = json.dumps(
            {
                "messages": list(messages),
                "max_tokens": max_tokens,
                "temperature": 0.0,
                "seed": 20260815,
                "cache_prompt": True,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/v1/chat/completions",
            data=corpo,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            doc = json.loads(r.read().decode("utf-8"))
        if doc.get("timings"):
            self.timings.add(doc["timings"])
        return doc["choices"][0]["message"]["content"] or ""


# --------------------------------------------------------------------------------------
# Prompt e parser
# --------------------------------------------------------------------------------------

CABECALHO = "Voce e um agente que executa tarefas usando ferramentas."

CONTRATO = """Responda com UM objeto JSON e nada mais, em uma destas quatro formas:

{"acao": "chamar", "ferramenta": "nome_da_ferramenta", "argumentos": {"campo": valor}}
{"acao": "responder", "texto": "sua resposta final"}
{"acao": "perguntar", "texto": "o que voce precisa saber"}
{"acao": "desistir", "texto": "por que nao foi possivel"}

Regras:
- Use apenas as ferramentas listadas acima, com o nome exato.
- Nunca invente o resultado de uma ferramenta: chame e espere a observacao.
- Quando a tarefa pedir um JSON como resposta, coloque esse JSON dentro do campo "texto".
- Responda em portugues do Brasil.

JSON da proxima acao:"""

#: Mantido para compatibilidade de leitura; o prompt efetivo e montado por `render_tucano_prompt`.
SYSTEM_PROMPT = f"{CABECALHO}\n\n{CONTRATO}"

#: exemplo demonstrado para o modo **diagnostico** (`G-112`). Nao pertence ao corpus: usa um
#: dominio e ferramentas que nenhuma tarefa do BR-Agent-Bench menciona, para que o exemplo nao
#: entregue nenhuma resposta.
#:
#: Serve a uma pergunta so: o escore zero-shot mede o modelo ou mede a elicitacao? Se um unico
#: exemplo demonstrado tira o modelo do zero, o zero media o prompt. O resultado deste modo
#: **nao** substitui o escore publicado — e diagnostico, como `probe_sensitivity` e para o
#: `CE-101`.
EXEMPLO_DEMONSTRADO = """Exemplo de uma tarefa ja executada, com outras ferramentas:

Tarefa: Qual a temperatura da sala 3?
Ferramentas disponiveis:
- ler_sensor
- ligar_ar

Acao: {"acao": "chamar", "ferramenta": "ler_sensor", "argumentos": {"sala": "3"}}
Observacao: {"temperatura": 24.5}
Acao: {"acao": "responder", "texto": "A sala 3 esta com 24.5 graus."}

Fim do exemplo."""


#: Defeito verificado no artefato publicado, e a razao de este modulo nao usar template de chat.
TUCANO_FORMAT_NOTE = """O template de chat embutido no GGUF do Tucano-2b4-Instruct fecha a tag
de instrucao dentro do prompt (`<instruction>` + conteudo + `</instruction>`). O modelo foi
treinado para **emitir** essa tag de fechamento ele mesmo. Medido nesta maquina, com
temperatura 0:

    <instruction>Qual e a capital da Franca?
      -> "</instruction>A capital da Franca e Paris. ..."          coerente

    <instruction>Qual e a capital da Franca?</instruction>
      -> "FFQuala</</. A PerguntQualfQualaQual e Pergunt: ..."     degenerado

O tokenizer esta correto — `<instruction>` e `</instruction>` sao tokens especiais unicos — e o
comportamento independe de BOS. Consequencia pratica: qualquer ferramenta que aplique o template
publicado (llama-server com --jinja, `apply_chat_template` do transformers, Ollama, LM Studio)
recebe saida degenerada deste modelo. Um benchmark que rodasse pelo caminho padrao publicaria
zero e atribuiria ao modelo."""


def render_tucano_prompt(
    task: EvalTask, history: Sequence[Step], fewshot: bool = False
) -> str:
    """Monta o prompt no formato que o modelo realmente aprendeu.

    Turnos concluidos levam a tag de fechamento; o ultimo turno fica **aberto**, para que o
    modelo produza `</instruction>` e siga com a resposta — que e o que ele faz.
    """
    ferramentas = "\n".join(f"- {t}" for t in task.tools) or "- (nenhuma)"
    exemplo = f"{EXEMPLO_DEMONSTRADO}\n\n" if fewshot else ""
    turnos: list[str] = [
        f"{CABECALHO}\n\n{exemplo}Tarefa:\n{task.prompt}\n\n"
        f"Ferramentas disponiveis:\n{ferramentas}\n\n{CONTRATO}"
    ]
    respostas: list[str] = []
    for s in history:
        if s.kind is StepKind.CALL:
            respostas.append(
                json.dumps(
                    {"acao": "chamar", "ferramenta": s.tool, "argumentos": dict(s.args)},
                    ensure_ascii=False,
                )
            )
            obs = f"ERRO: {s.error}" if s.error else json.dumps(s.observation, ensure_ascii=False)
            turnos.append(f"Observacao: {obs}\n\n{CONTRATO}")
        else:
            respostas.append(s.text)

    partes: list[str] = []
    for i, pergunta in enumerate(turnos):
        partes.append(f"<instruction>{pergunta}")
        if i < len(respostas):
            partes.append(f"</instruction>{respostas[i]}")
    return "".join(partes)


def strip_closing_tag(texto: str) -> str:
    """O modelo abre a resposta fechando a tag; isso nao e conteudo."""
    t = texto.lstrip()
    return t[len("</instruction>"):].lstrip() if t.startswith("</instruction>") else t


def build_messages(
    task: EvalTask, history: Sequence[Step], fewshot: bool = False, sistema: str = ""
) -> list[dict[str, str]]:
    """Conversa em `role`/`content`, para modelos cujo template embutido funciona.

    O conteudo do prompt e **o mesmo** do caminho cru — mesmo `CABECALHO`, mesmo `CONTRATO`,
    mesma ordem. So o envelope muda. Isso e o que torna dois modelos comparaveis: o formato de
    conversa e imposto pelo treino de cada um e nao ha escolha, mas o texto dentro dele e
    identico e versionado por `PROMPT_VERSION`.
    """
    ferramentas = "\n".join(f"- {t}" for t in task.tools) or "- (nenhuma)"
    exemplo = f"{EXEMPLO_DEMONSTRADO}\n\n" if fewshot else ""
    msgs: list[dict[str, str]] = []
    if sistema:
        msgs.append({"role": "system", "content": sistema})
    msgs.append(
        {
            "role": "user",
            "content": f"{CABECALHO}\n\n{exemplo}Tarefa:\n{task.prompt}\n\n"
            f"Ferramentas disponiveis:\n{ferramentas}\n\n{CONTRATO}",
        }
    )
    for s in history:
        if s.kind is StepKind.CALL:
            msgs.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {"acao": "chamar", "ferramenta": s.tool, "argumentos": dict(s.args)},
                        ensure_ascii=False,
                    ),
                }
            )
            obs = f"ERRO: {s.error}" if s.error else json.dumps(s.observation, ensure_ascii=False)
            msgs.append({"role": "user", "content": f"Observacao: {obs}\n\n{CONTRATO}"})
        else:
            msgs.append({"role": "assistant", "content": s.text})
    return msgs


class ConversationFormat(str, Enum):
    """Como a conversa chega ao modelo. E parte do instrumento, e por isso e declarado.

    Nao ha um formato certo universal: cada modelo aprendeu o seu, e usar o errado produz
    repeticao degenerada em vez de capacidade baixa (ver `TUCANO_FORMAT_NOTE`). Antes de medir
    qualquer modelo novo, o `RB-102` manda verificar qual dos dois se aplica.
    """

    #: Prompt cru montado a mao. Necessario quando o template publicado esta **errado**.
    RAW_INSTRUCTION = "raw-instruction"
    #: `/v1/chat/completions` com `--jinja`: o servidor aplica o template do proprio GGUF.
    CHAT_TEMPLATE = "chat-template"


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_ACOES = {
    "chamar": StepKind.CALL,
    "responder": StepKind.ANSWER,
    "perguntar": StepKind.ASK,
    "desistir": StepKind.GIVE_UP,
}


def parse_action(texto: str) -> Step:
    """Interpreta a saida do modelo como um passo.

    Sem reparo e sem nova tentativa. Saida que nao vira acao interpretavel vira uma **resposta
    em texto** com o conteudo cru — e o grader decide. Um harness que insiste ate sair JSON
    valido mede a propria persistencia, e um que corrige o JSON mede a si mesmo.
    """
    bruto = texto.strip()
    m = _JSON_RE.search(bruto)
    if m:
        try:
            doc = json.loads(m.group(0))
        except json.JSONDecodeError:
            doc = None
        if isinstance(doc, dict) and doc.get("acao") in _ACOES:
            kind = _ACOES[str(doc["acao"])]
            if kind is StepKind.CALL:
                return Step(
                    kind=kind,
                    tool=str(doc.get("ferramenta", "")),
                    args=dict(doc.get("argumentos") or {}),
                )
            return Step(kind=kind, text=str(doc.get("texto", "")).strip() or bruto)
    return Step(kind=StepKind.ANSWER, text=bruto)


@dataclass
class LlamaCppRespondent:
    """Um modelo real respondendo. `synthetic=False` — e o que autoriza capacidade medida."""

    server: LlamaServer
    id: str
    synthetic: bool = False
    #: Modo diagnostico de `G-112`: injeta um exemplo demonstrado. O escore resultante nao e
    #: publicavel como capacidade do modelo — serve para saber o que o zero-shot mediu.
    fewshot: bool = False
    #: Qual envelope de conversa este modelo entende. Ver `ConversationFormat`.
    fmt: ConversationFormat = ConversationFormat.RAW_INSTRUCTION
    #: Mensagem de sistema, quando o template do modelo aceita uma. Vazia por padrao: o
    #: conteudo do prompt vive no turno de usuario, igual nos dois caminhos.
    system: str = ""
    #: Teto de tokens por passo. Modelos de raciocinio hibrido gastam boa parte do orcamento
    #: pensando antes de responder; com teto baixo a acao seria cortada e o grader registraria
    #: `FAIL_FORMAT` por truncamento do harness, nao por defeito do modelo.
    max_tokens: int = 256

    def act(self, task: EvalTask, history: Sequence[Step]) -> Step:
        if self.fmt is ConversationFormat.CHAT_TEMPLATE:
            msgs = build_messages(task, history, self.fewshot, self.system)
            return parse_action(self.server.chat(msgs, self.max_tokens))
        bruto = self.server.complete(
            render_tucano_prompt(task, history, self.fewshot), self.max_tokens
        )
        return parse_action(strip_closing_tag(bruto))


__all__ = [
    "LlamaServer",
    "LlamaCppRespondent",
    "Timings",
    "BackendUnavailable",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "TUCANO_FORMAT_NOTE",
    "ConversationFormat",
    "build_messages",
    "render_tucano_prompt",
    "strip_closing_tag",
    "parse_action",
    "find_server",
    "find_model",
    "LOCAL_BIN",
    "LOCAL_MODELS",
]
