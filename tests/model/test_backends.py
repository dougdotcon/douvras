"""O harness de execução real — a parte que não precisa de modelo para ser verificada.

`backends.py` entrou no ciclo C-003 sem teste, com a desculpa de que "precisa de pesos". Só que
a peça que decide todo escore — `parse_action`, que transforma texto em passo — é função pura, e
o mesmo vale para a montagem dos dois envelopes de conversa. Ficaram sem cobertura por hábito,
não por necessidade: exatamente o `G-014` do Silicon Atlas, agora do lado do harness.

O que estes testes protegem, em uma frase: **o harness não conserta a saída do modelo**. Toda
tentação de reparo (completar JSON truncado, adivinhar a ferramenta a partir do texto, repetir a
chamada até sair válida) melhora o escore medindo o harness.
"""

from __future__ import annotations

import json

import pytest

from model_atlas.backends import (
    CABECALHO,
    CONTRATO,
    ConversationFormat,
    LlamaCppRespondent,
    build_messages,
    parse_action,
    render_tucano_prompt,
    strip_closing_tag,
)
from model_atlas.tasks import Capability, EvalTask, Step, StepKind


@pytest.fixture
def tarefa() -> EvalTask:
    """Tarefa mínima. O que importa aqui é o envelope, não o conteúdo do corpus."""
    return EvalTask(
        id="T-1",
        capability=Capability.TOOL_SELECTION,
        difficulty=1,
        language="pt-BR",
        prompt="Qual e o valor do pedido 1040?",
        tools=("consultar_pedido", "consultar_saldo"),
        environment={},
        rules={},
        failure_modes=(),
        gold=(),
    )


# ------------------------------------------------------------------ parse_action ---


def test_acao_de_chamada_vira_passo_de_chamada() -> None:
    s = parse_action('{"acao": "chamar", "ferramenta": "consultar_pedido", "argumentos": {"id": 1040}}')
    assert s.kind is StepKind.CALL
    assert s.tool == "consultar_pedido"
    assert dict(s.args) == {"id": 1040}


@pytest.mark.parametrize(
    "acao,esperado",
    [
        ("responder", StepKind.ANSWER),
        ("perguntar", StepKind.ASK),
        ("desistir", StepKind.GIVE_UP),
    ],
)
def test_as_outras_tres_acoes(acao: str, esperado: StepKind) -> None:
    s = parse_action(json.dumps({"acao": acao, "texto": "algo"}, ensure_ascii=False))
    assert s.kind is esperado
    assert s.text == "algo"


def test_json_embutido_em_prosa_e_encontrado() -> None:
    """Modelo pequeno raramente devolve JSON limpo. Achar o objeto não é reparo."""
    s = parse_action('Claro! Aqui vai:\n{"acao": "chamar", "ferramenta": "x", "argumentos": {}}\nPronto.')
    assert s.kind is StepKind.CALL and s.tool == "x"


def test_texto_sem_json_vira_resposta_crua_e_nao_erro() -> None:
    s = parse_action("Nao sei fazer isso.")
    assert s.kind is StepKind.ANSWER
    assert s.text == "Nao sei fazer isso."


def test_json_malformado_vira_resposta_crua() -> None:
    """Sem tentativa de conserto: o texto cru vai ao grader como está."""
    bruto = '{"acao": "chamar", "ferramenta": '
    assert parse_action(bruto).kind is StepKind.ANSWER


def test_acao_desconhecida_nao_e_adivinhada() -> None:
    """`call` em inglês foi o que o Tucano emitiu. Mapear para `chamar` seria consertar."""
    s = parse_action('{"acao": "call", "ferramenta": "consultar_pedido", "argumentos": {}}')
    assert s.kind is StepKind.ANSWER, "traduzir a acao do modelo mediria o harness"


def test_chamada_sem_ferramenta_permanece_sem_ferramenta() -> None:
    """O grader precisa ver a chamada vazia para registrar `FAIL_TOOL_SELECTION`."""
    s = parse_action('{"acao": "chamar", "argumentos": {}}')
    assert s.kind is StepKind.CALL and s.tool == ""


def test_strip_closing_tag_so_remove_no_inicio() -> None:
    assert strip_closing_tag("</instruction>Paris") == "Paris"
    assert strip_closing_tag("Paris </instruction> fim") == "Paris </instruction> fim"


# ------------------------------------------------- os dois envelopes de conversa ---


def test_prompt_cru_deixa_o_ultimo_turno_aberto(tarefa: EvalTask) -> None:
    """O modelo é quem fecha a tag. Fechá-la no prompt produz saída degenerada (G-114)."""
    p = render_tucano_prompt(tarefa, [])
    assert p.startswith("<instruction>")
    assert not p.endswith("</instruction>")
    assert p.count("<instruction>") == 1


def test_prompt_cru_fecha_os_turnos_ja_concluidos(tarefa: EvalTask) -> None:
    hist = [
        Step(kind=StepKind.CALL, tool="consultar_pedido", args={"id": 1040}, observation={"v": 10})
    ]
    p = render_tucano_prompt(tarefa, hist)
    assert p.count("<instruction>") == 2
    assert p.count("</instruction>") == 1, "só o turno respondido fecha"
    assert p.endswith(CONTRATO)


def test_conversa_por_template_alterna_papeis(tarefa: EvalTask) -> None:
    hist = [
        Step(kind=StepKind.CALL, tool="consultar_pedido", args={"id": 1040}, observation={"v": 10})
    ]
    msgs = build_messages(tarefa, hist)
    papeis = [m["role"] for m in msgs]
    assert papeis == ["user", "assistant", "user"], "alternância estrita, sem system por padrão"


def test_mensagem_de_sistema_e_opcional_e_vem_primeiro(tarefa: EvalTask) -> None:
    msgs = build_messages(tarefa, [], sistema="/no_think")
    assert msgs[0] == {"role": "system", "content": "/no_think"}


def test_os_dois_envelopes_carregam_o_mesmo_conteudo(tarefa: EvalTask) -> None:
    """A comparação entre dois modelos só vale se o texto for o mesmo nos dois caminhos.

    O envelope é imposto pelo treino de cada modelo e não há escolha; o conteúdo é escolha, é
    versionado por `PROMPT_VERSION`, e tem de ser idêntico.
    """
    cru = render_tucano_prompt(tarefa, [])
    chat = build_messages(tarefa, [])[0]["content"]
    miolo = cru[len("<instruction>"):]
    assert miolo == chat
    for pedaco in (CABECALHO, tarefa.prompt, "consultar_pedido", CONTRATO):
        assert pedaco in chat and pedaco in cru


def test_o_exemplo_do_modo_diagnostico_entra_nos_dois(tarefa: EvalTask) -> None:
    assert "Exemplo" in render_tucano_prompt(tarefa, [], fewshot=True)
    assert "Exemplo" in build_messages(tarefa, [], fewshot=True)[0]["content"]
    assert "Exemplo" not in build_messages(tarefa, [], fewshot=False)[0]["content"]


def test_o_exemplo_nao_entrega_nenhuma_ferramenta_do_corpus(tasks_corpus) -> None:
    """Se o exemplo citasse uma ferramenta real, o diagnóstico vazaria resposta."""
    from model_atlas.backends import EXEMPLO_DEMONSTRADO

    do_corpus = {f for t in tasks_corpus for f in t.tools}
    citadas = {"ler_sensor", "ligar_ar"}
    assert citadas.isdisjoint(do_corpus)
    for f in do_corpus:
        assert f not in EXEMPLO_DEMONSTRADO


# ------------------------------------------------------------------- despacho ---


class _ServidorFalso:
    """Registra por qual caminho o respondente falou."""

    def __init__(self, resposta: str) -> None:
        self.resposta = resposta
        self.via: str = ""
        self.recebido: object = None

    def complete(self, prompt: str, max_tokens: int = 256) -> str:
        self.via, self.recebido = "complete", prompt
        return self.resposta

    def chat(self, messages, max_tokens: int = 256) -> str:  # noqa: ANN001
        self.via, self.recebido = "chat", list(messages)
        return self.resposta


def test_formato_cru_usa_completion_e_remove_a_tag(tarefa: EvalTask) -> None:
    srv = _ServidorFalso('</instruction>{"acao": "responder", "texto": "ok"}')
    r = LlamaCppRespondent(server=srv, id="x", fmt=ConversationFormat.RAW_INSTRUCTION)
    passo = r.act(tarefa, [])
    assert srv.via == "complete"
    assert passo.kind is StepKind.ANSWER and passo.text == "ok"


def test_formato_de_template_usa_chat_completions(tarefa: EvalTask) -> None:
    srv = _ServidorFalso('{"acao": "responder", "texto": "ok"}')
    r = LlamaCppRespondent(server=srv, id="x", fmt=ConversationFormat.CHAT_TEMPLATE)
    passo = r.act(tarefa, [])
    assert srv.via == "chat"
    assert isinstance(srv.recebido, list) and srv.recebido[0]["role"] == "user"
    assert passo.text == "ok"


def test_o_respondente_real_nao_e_sintetico(tarefa: EvalTask) -> None:
    """`synthetic=False` é o que autoriza `CapabilityFingerprint` a publicar capacidade."""
    assert LlamaCppRespondent(server=_ServidorFalso(""), id="x").synthetic is False
