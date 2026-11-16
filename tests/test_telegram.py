import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from telegram import Chat, Message, Update, User

from backend import main
from backend.canais import telegram as tg

DONO = 111
ESTRANHO = 999
SEGREDO = "segredo-webhook"


@pytest.fixture(autouse=True)
def config_telegram(monkeypatch, tmp_path):
    monkeypatch.setattr(tg.config, "TELEGRAM_TOKEN", "123:token-falso")
    monkeypatch.setattr(tg.config, "TELEGRAM_DONO_ID", DONO)
    monkeypatch.setattr(tg.config, "TELEGRAM_WEBHOOK_SECRET", SEGREDO)
    monkeypatch.setattr(tg.config, "KORA_ACCESS_TOKEN", "segredo-teste")
    monkeypatch.setattr(tg.config, "HISTORICO_DB_PATH", str(tmp_path / "historico.db"))
    monkeypatch.setattr(main, "aplicacao_telegram", None)


def criar_update(user_id: int, texto: str = "oi") -> Update:
    usuario = User(id=user_id, first_name="x", is_bot=False)
    mensagem = Message(
        message_id=1, date=datetime.now(), chat=Chat(user_id, "private"), from_user=usuario, text=texto
    )
    return Update(update_id=1, message=mensagem)


# ------------------------------------------------------------ seguranca


def test_estranho_cai_no_bloqueio_antes_de_tudo():
    aplicacao = tg.criar_aplicacao(webhook=True)

    assert min(aplicacao.handlers) == -1
    assert aplicacao.handlers[-1][0].check_update(criar_update(ESTRANHO))
    assert not aplicacao.handlers[-1][0].check_update(criar_update(DONO))


@pytest.mark.parametrize("texto", ["oi", "/start", "/briefing"])
def test_nenhum_handler_atende_estranho(texto):
    aplicacao = tg.criar_aplicacao(webhook=True)

    assert not any(h.check_update(criar_update(ESTRANHO, texto)) for h in aplicacao.handlers[0])
    assert any(h.check_update(criar_update(DONO, texto)) for h in aplicacao.handlers[0])


def test_webhook_secreto_valido(monkeypatch):
    assert tg.webhook_secreto_valido(SEGREDO)
    assert not tg.webhook_secreto_valido("errado")
    assert not tg.webhook_secreto_valido(None)
    monkeypatch.setattr(tg.config, "TELEGRAM_WEBHOOK_SECRET", "")
    assert not tg.webhook_secreto_valido("")


@pytest.mark.parametrize("cabecalho", [{}, {"X-Telegram-Bot-Api-Secret-Token": "errado"}])
def test_webhook_recusa_sem_segredo_correto(cabecalho):
    resposta = TestClient(main.app).post("/telegram/webhook", json={"update_id": 1}, headers=cabecalho)

    assert resposta.status_code == 401


def test_webhook_503_quando_canal_desligado():
    resposta = TestClient(main.app).post(
        "/telegram/webhook", json={"update_id": 1}, headers={"X-Telegram-Bot-Api-Secret-Token": SEGREDO}
    )

    assert resposta.status_code == 503


def test_webhook_com_segredo_correto_enfileira_update(monkeypatch):
    aplicacao = tg.criar_aplicacao(webhook=True)
    monkeypatch.setattr(main, "aplicacao_telegram", aplicacao)

    resposta = TestClient(main.app).post(
        "/telegram/webhook",
        json=criar_update(DONO).to_dict(),
        headers={"X-Telegram-Bot-Api-Secret-Token": SEGREDO},
    )

    assert resposta.status_code == 200
    update = aplicacao.update_queue.get_nowait()
    assert update.effective_user.id == DONO


# ------------------------------------------------------------ envio proativo


def test_enviar_ao_dono_desligado_sem_configuracao(monkeypatch):
    monkeypatch.setattr(tg.config, "TELEGRAM_TOKEN", "")
    assert asyncio.run(tg.enviar_ao_dono("oi")) is False


def test_enviar_ao_dono_divide_e_envia_para_o_dono(monkeypatch):
    enviados = []

    class BotFalso:
        def __init__(self, token):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def send_message(self, chat_id, text):
            enviados.append((chat_id, text))

    monkeypatch.setattr(tg, "Bot", BotFalso)
    monkeypatch.setattr(tg, "LIMITE_TELEGRAM", 10)

    assert asyncio.run(tg.enviar_ao_dono("a" * 25)) is True
    assert {chat for chat, _ in enviados} == {DONO}
    assert "".join(texto for _, texto in enviados) == "a" * 25


def test_enviar_ao_dono_nao_propaga_erro(monkeypatch):
    class BotQuebrado:
        def __init__(self, token):
            raise RuntimeError("rede fora")

    monkeypatch.setattr(tg, "Bot", BotQuebrado)
    assert asyncio.run(tg.enviar_ao_dono("oi")) is False


def test_briefing_e_enviado_ao_telegram(monkeypatch):
    enviados = []

    async def enviar_falso(texto):
        enviados.append(texto)
        return True

    monkeypatch.setattr(main.briefing, "gerar_briefing", lambda: "bom dia")
    monkeypatch.setattr(main.telegram, "enviar_ao_dono", enviar_falso)

    resposta = TestClient(main.app).post("/agente/briefing", headers={"Authorization": "Bearer segredo-teste"})

    assert resposta.status_code == 200
    assert resposta.json()["enviado_telegram"] is True
    assert enviados == ["bom dia"]


# ------------------------------------------------------------ ciclo de vida


def test_start_registra_webhook_com_segredo(monkeypatch):
    chamadas = []

    class BotFalso:
        async def set_webhook(self, **kwargs):
            chamadas.append(kwargs)

    class AplicacaoFalsa:
        bot = BotFalso()

        async def initialize(self):
            chamadas.append("initialize")

        async def start(self):
            chamadas.append("start")

        async def stop(self):
            chamadas.append("stop")

        async def shutdown(self):
            chamadas.append("shutdown")

    monkeypatch.setattr(main.telegram, "criar_aplicacao", lambda webhook: AplicacaoFalsa())
    monkeypatch.setattr(tg.config, "KORA_URL_PUBLICA", "https://kora.exemplo.com")

    with TestClient(main.app):
        assert main.aplicacao_telegram is not None

    webhook = next(c for c in chamadas if isinstance(c, dict))
    assert webhook["url"] == "https://kora.exemplo.com/telegram/webhook"
    assert webhook["secret_token"] == SEGREDO
    assert chamadas[-2:] == ["stop", "shutdown"]


def test_sem_segredo_de_webhook_canal_nao_sobe(monkeypatch):
    monkeypatch.setattr(tg.config, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(main.telegram, "criar_aplicacao", lambda webhook: pytest.fail("nao deveria criar"))

    with TestClient(main.app):
        assert main.aplicacao_telegram is None


# ------------------------------------------------------------ utilitarios


def test_dividir_mensagem_respeita_limite():
    texto = ("a" * 10 + "\n") * 10
    partes = tg.dividir_mensagem(texto, limite=25)
    assert all(len(p) <= 25 for p in partes)
    assert "".join(partes).replace("\n", "") == "a" * 100
