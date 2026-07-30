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
