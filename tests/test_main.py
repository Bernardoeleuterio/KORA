from fastapi.testclient import TestClient

from backend import main
from backend.brain import llm


class FakeResponse:
    def __init__(self, text):
        self.text = text


def test_health():
    cliente = TestClient(main.app)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_chat_retorna_resposta_do_gemini(monkeypatch):
    chamadas = []

    def fake_perguntar(mensagem, tools=None):
        chamadas.append((mensagem, tools))
        return FakeResponse("resposta de teste")

    monkeypatch.setattr(main.llm, "perguntar", fake_perguntar)

    cliente = TestClient(main.app)
    resposta = cliente.post("/chat", json={"mensagem": "ola kora"})

    assert resposta.status_code == 200
    assert resposta.json() == {"resposta": "resposta de teste"}
    assert chamadas == [("ola kora", main.tools.FERRAMENTAS)]


def test_chat_valida_corpo_da_requisicao():
    cliente = TestClient(main.app)

    resposta = cliente.post("/chat", json={})

    assert resposta.status_code == 422


def test_frontend_index_e_arquivos_estaticos_servidos():
    cliente = TestClient(main.app)

    pagina = cliente.get("/")
    assert pagina.status_code == 200
    assert "KORA" in pagina.text

    script = cliente.get("/js/app.js")
    assert script.status_code == 200
    assert "WebSocket" in script.text


def test_websocket_streama_pedacos_e_avisa_o_fim(monkeypatch):
    chamadas = []

    async def fake_perguntar_stream(mensagem):
        chamadas.append(mensagem)
        for pedaco in ["Ola", " mundo"]:
            yield pedaco

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream)

    cliente = TestClient(main.app)
    with cliente.websocket_connect("/ws") as websocket:
        websocket.send_json({"mensagem": "oi"})
        pedaco1 = websocket.receive_json()
        pedaco2 = websocket.receive_json()
        fim = websocket.receive_json()

    assert chamadas == ["oi"]
    assert pedaco1 == {"tipo": "pedaco", "texto": "Ola"}
    assert pedaco2 == {"tipo": "pedaco", "texto": " mundo"}
    assert fim == {"tipo": "fim"}


def test_websocket_avisa_erro_sem_derrubar_a_conexao(monkeypatch):
    async def fake_perguntar_stream_com_erro(mensagem):
        raise RuntimeError("cota da API excedida")
        yield  # pragma: no cover - torna a funcao um gerador async

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream_com_erro)

    cliente = TestClient(main.app)
    with cliente.websocket_connect("/ws") as websocket:
        websocket.send_json({"mensagem": "oi"})
        erro = websocket.receive_json()

        # a conexao continua utilizavel apos o erro
        async def fake_perguntar_stream_ok(mensagem):
            yield "tudo bem agora"

        monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream_ok)
        websocket.send_json({"mensagem": "oi de novo"})
        pedaco = websocket.receive_json()
        fim = websocket.receive_json()

    assert erro == {"tipo": "erro", "mensagem": "cota da API excedida"}
    assert pedaco == {"tipo": "pedaco", "texto": "tudo bem agora"}
    assert fim == {"tipo": "fim"}
