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
