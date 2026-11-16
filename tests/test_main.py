import pytest
from fastapi import status
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend import main
from backend.brain import llm


TOKEN_TESTE = "segredo-teste"
CABECALHO_AUTH = {"Authorization": f"Bearer {TOKEN_TESTE}"}
URL_WS = f"/ws?token={TOKEN_TESTE}"


def cliente_autenticado() -> TestClient:
    return TestClient(main.app, headers=CABECALHO_AUTH)


class FakeResponse:
    def __init__(self, text):
        self.text = text


@pytest.fixture(autouse=True)
def token_de_acesso_de_teste(monkeypatch):
    """Torna os testes independentes do KORA_ACCESS_TOKEN configurado no .env real."""
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", TOKEN_TESTE)


@pytest.fixture(autouse=True)
def banco_de_historico_isolado(monkeypatch, tmp_path):
    """Evita que os testes leiam/escrevam no banco de historico real do projeto."""
    monkeypatch.setattr(main.config, "HISTORICO_DB_PATH", str(tmp_path / "teste_historico.db"))


def test_health():
    cliente = TestClient(main.app)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_chat_retorna_resposta_do_gemini(monkeypatch):
    chamadas = []

    def fake_perguntar(mensagem, tools=None, historico=None):
        chamadas.append((mensagem, tools, historico))
        return FakeResponse("resposta de teste")

    monkeypatch.setattr(main.llm, "perguntar", fake_perguntar)

    cliente = cliente_autenticado()
    resposta = cliente.post("/chat", json={"mensagem": "ola kora"})

    assert resposta.status_code == 200
    assert resposta.json() == {"resposta": "resposta de teste"}
    assert chamadas == [("ola kora", main.tools.FERRAMENTAS, [])]

    turnos_salvos = main.historico.carregar_recentes()
    assert turnos_salvos == [
        {"papel": "usuario", "conteudo": "ola kora"},
        {"papel": "kora", "conteudo": "resposta de teste"},
    ]


def test_chat_valida_corpo_da_requisicao():
    cliente = cliente_autenticado()

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
    assert "webkitSpeechRecognition" in script.text
    assert "botao-voz" in script.text
    assert "kora_token" in script.text

    visualizador = cliente.get("/js/visualizer.js")
    assert visualizador.status_code == 200
    assert "OrbeVisualizer" in visualizador.text

    estilos = cliente.get("/css/styles.css")
    assert estilos.status_code == 200
    assert "--cor-neon" in estilos.text

    assert "manifest.json" in pagina.text
    manifesto = cliente.get("/manifest.json")
    assert manifesto.status_code == 200
    assert manifesto.json()["name"] == "KORA"
    assert manifesto.json()["display"] == "standalone"

    service_worker = cliente.get("/sw.js")
    assert service_worker.status_code == 200
    assert "addEventListener" in service_worker.text

    icone = cliente.get("/icons/icon-192.png")
    assert icone.status_code == 200
    assert icone.headers["content-type"] == "image/png"


def test_websocket_streama_pedacos_e_avisa_o_fim(monkeypatch):
    chamadas = []

    async def fake_perguntar_stream(mensagem, historico=None):
        chamadas.append((mensagem, historico))
        for pedaco in ["Ola", " mundo"]:
            yield pedaco

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream)

    cliente = cliente_autenticado()
    with cliente.websocket_connect(URL_WS) as websocket:
        websocket.send_json({"mensagem": "oi"})
        pedaco1 = websocket.receive_json()
        pedaco2 = websocket.receive_json()
        fim = websocket.receive_json()

    assert chamadas == [("oi", [])]
    assert pedaco1 == {"tipo": "pedaco", "texto": "Ola"}
    assert pedaco2 == {"tipo": "pedaco", "texto": " mundo"}
    assert fim == {"tipo": "fim"}

    turnos_salvos = main.historico.carregar_recentes()
    assert turnos_salvos == [
        {"papel": "usuario", "conteudo": "oi"},
        {"papel": "kora", "conteudo": "Ola mundo"},
    ]


def test_websocket_avisa_erro_sem_derrubar_a_conexao(monkeypatch):
    async def fake_perguntar_stream_com_erro(mensagem, historico=None):
        raise RuntimeError("cota da API excedida")
        yield  # pragma: no cover - torna a funcao um gerador async

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream_com_erro)

    cliente = cliente_autenticado()
    with cliente.websocket_connect(URL_WS) as websocket:
        websocket.send_json({"mensagem": "oi"})
        erro = websocket.receive_json()

        # a conexao continua utilizavel apos o erro
        async def fake_perguntar_stream_ok(mensagem, historico=None):
            yield "tudo bem agora"

        monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream_ok)
        websocket.send_json({"mensagem": "oi de novo"})
        pedaco = websocket.receive_json()
        fim = websocket.receive_json()

    assert erro == {"tipo": "erro", "mensagem": "cota da API excedida"}
    assert pedaco == {"tipo": "pedaco", "texto": "tudo bem agora"}
    assert fim == {"tipo": "fim"}


def test_websocket_envia_audio_quando_voz_e_pedida(monkeypatch):
    async def fake_perguntar_stream(mensagem, historico=None):
        for pedaco in ["Ola", " mundo"]:
            yield pedaco

    chamadas_tts = []

    async def fake_sintetizar(texto):
        chamadas_tts.append(texto)
        return b"audio-fake"

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream)
    monkeypatch.setattr(main.tts, "sintetizar", fake_sintetizar)

    cliente = cliente_autenticado()
    with cliente.websocket_connect(URL_WS) as websocket:
        websocket.send_json({"mensagem": "oi", "voz": True})
        websocket.receive_json()
        websocket.receive_json()
        fim = websocket.receive_json()
        audio = websocket.receive_bytes()

    assert fim == {"tipo": "fim"}
    assert audio == b"audio-fake"
    assert chamadas_tts == ["Ola mundo"]


def test_websocket_nao_sintetiza_audio_sem_pedido_de_voz(monkeypatch):
    async def fake_perguntar_stream(mensagem, historico=None):
        yield "Ola"

    async def tts_nao_deveria_ser_chamado(texto):
        raise AssertionError("tts.sintetizar nao deveria ser chamado quando voz nao foi pedida")

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream)
    monkeypatch.setattr(main.tts, "sintetizar", tts_nao_deveria_ser_chamado)

    cliente = cliente_autenticado()
    with cliente.websocket_connect(URL_WS) as websocket:
        websocket.send_json({"mensagem": "oi"})
        websocket.receive_json()
        fim = websocket.receive_json()

    assert fim == {"tipo": "fim"}


def test_chat_sem_token_e_rejeitado_quando_token_esta_configurado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")

    cliente = TestClient(main.app)
    resposta = cliente.post("/chat", json={"mensagem": "oi"})

    assert resposta.status_code == 401


def test_chat_com_token_errado_e_rejeitado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")

    cliente = TestClient(main.app)
    resposta = cliente.post(
        "/chat", json={"mensagem": "oi"}, headers={"Authorization": "Bearer errado"}
    )

    assert resposta.status_code == 401


def test_chat_com_token_correto_funciona(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")
    monkeypatch.setattr(main.llm, "perguntar", lambda mensagem, tools=None, historico=None: FakeResponse("ok"))

    cliente = TestClient(main.app)
    resposta = cliente.post(
        "/chat", json={"mensagem": "oi"}, headers={"Authorization": "Bearer segredo-teste"}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"resposta": "ok"}


def test_agente_briefing_sem_token_e_rejeitado_quando_token_esta_configurado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")

    cliente = TestClient(main.app)
    resposta = cliente.post("/agente/briefing")

    assert resposta.status_code == 401


def test_agente_briefing_com_token_correto_gera_e_retorna_o_briefing(monkeypatch):
    chamadas = []
    monkeypatch.setattr(main.briefing, "gerar_briefing", lambda: chamadas.append(1) or "briefing de teste")

    cliente = cliente_autenticado()
    resposta = cliente.post("/agente/briefing")

    assert resposta.status_code == 200
    assert resposta.json() == {"briefing": "briefing de teste", "audio_base64": None}
    assert len(chamadas) == 1


def test_agente_briefing_com_voz_inclui_audio_em_base64(monkeypatch):
    import base64

    monkeypatch.setattr(main.briefing, "gerar_briefing", lambda: "briefing de teste")

    chamadas_tts = []

    async def fake_sintetizar(texto):
        chamadas_tts.append(texto)
        return b"audio-fake"

    monkeypatch.setattr(main.tts, "sintetizar", fake_sintetizar)

    cliente = cliente_autenticado()
    resposta = cliente.post("/agente/briefing?voz=true")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["briefing"] == "briefing de teste"
    assert base64.b64decode(corpo["audio_base64"]) == b"audio-fake"
    assert chamadas_tts == ["briefing de teste"]


def test_websocket_sem_token_e_recusado_quando_token_esta_configurado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")

    cliente = TestClient(main.app)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with cliente.websocket_connect("/ws") as websocket:
            websocket.receive_json()

    assert excinfo.value.code == status.WS_1008_POLICY_VIOLATION


def test_websocket_com_token_errado_e_recusado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")

    cliente = TestClient(main.app)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with cliente.websocket_connect("/ws?token=errado") as websocket:
            websocket.receive_json()

    assert excinfo.value.code == status.WS_1008_POLICY_VIOLATION


def test_websocket_com_token_correto_funciona(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "segredo-teste")

    async def fake_perguntar_stream(mensagem, historico=None):
        yield "ok"

    monkeypatch.setattr(main.llm, "perguntar_stream", fake_perguntar_stream)

    cliente = TestClient(main.app)
    with cliente.websocket_connect("/ws?token=segredo-teste") as websocket:
        websocket.send_json({"mensagem": "oi"})
        pedaco = websocket.receive_json()
        fim = websocket.receive_json()

    assert pedaco == {"tipo": "pedaco", "texto": "ok"}
    assert fim == {"tipo": "fim"}


def test_chat_recusado_quando_token_nao_esta_configurado(monkeypatch):
    """Fail-closed: deploy sem KORA_ACCESS_TOKEN nao pode deixar o Vault aberto."""
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "")

    resposta = TestClient(main.app).post("/chat", json={"mensagem": "oi"})

    assert resposta.status_code == 503


def test_agente_briefing_recusado_quando_token_nao_esta_configurado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "")
    monkeypatch.setattr(main.briefing, "gerar_briefing", lambda: pytest.fail("nao deveria gerar"))

    resposta = TestClient(main.app).post("/agente/briefing", headers={"Authorization": "Bearer "})

    assert resposta.status_code == 503


def test_websocket_recusado_quando_token_nao_esta_configurado(monkeypatch):
    monkeypatch.setattr(main.config, "KORA_ACCESS_TOKEN", "")

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with TestClient(main.app).websocket_connect("/ws?token=") as websocket:
            websocket.receive_json()

    assert excinfo.value.code == status.WS_1008_POLICY_VIOLATION


def test_header_sem_prefixo_bearer_e_rejeitado():
    resposta = TestClient(main.app).post(
        "/chat", json={"mensagem": "oi"}, headers={"Authorization": TOKEN_TESTE}
    )

    assert resposta.status_code == 401
