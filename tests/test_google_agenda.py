from datetime import datetime

import pytest

from backend.brain import google_agenda


class FakeEventosExecutor:
    def __init__(self, resposta):
        self._resposta = resposta

    def execute(self):
        return self._resposta


class FakeEventos:
    def __init__(self, resposta_list=None):
        self.resposta_list = resposta_list or {"items": []}
        self.chamadas_insert = []

    def list(self, **kwargs):
        return FakeEventosExecutor(self.resposta_list)

    def insert(self, calendarId, body):
        self.chamadas_insert.append((calendarId, body))
        return FakeEventosExecutor({"id": "evt123", "summary": body["summary"], "start": body["start"], "end": body["end"]})


class FakeServico:
    def __init__(self, eventos):
        self._eventos = eventos

    def events(self):
        return self._eventos


def _configurar_credenciais(monkeypatch):
    monkeypatch.setattr(google_agenda.config, "GOOGLE_CLIENT_ID", "id-teste")
    monkeypatch.setattr(google_agenda.config, "GOOGLE_CLIENT_SECRET", "secret-teste")
    monkeypatch.setattr(google_agenda.config, "GOOGLE_REFRESH_TOKEN", "refresh-teste")


def test_listar_eventos_sem_credenciais_configuradas(monkeypatch):
    monkeypatch.setattr(google_agenda.config, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(google_agenda.config, "GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setattr(google_agenda.config, "GOOGLE_REFRESH_TOKEN", "")

    with pytest.raises(google_agenda.GoogleAgendaError):
        google_agenda.listar_eventos()


def test_listar_eventos_formata_resposta_da_api(monkeypatch):
    _configurar_credenciais(monkeypatch)
    eventos_fake = FakeEventos(
        resposta_list={
            "items": [
                {
                    "id": "evt1",
                    "summary": "Reuniao",
                    "start": {"dateTime": "2026-08-05T10:00:00-03:00"},
                    "end": {"dateTime": "2026-08-05T11:00:00-03:00"},
                    "description": "Pauta X",
                }
            ]
        }
    )
    monkeypatch.setattr(google_agenda, "_servico", lambda: FakeServico(eventos_fake))

    resultado = google_agenda.listar_eventos()

    assert resultado == [
        {
            "id": "evt1",
            "titulo": "Reuniao",
            "inicio": "2026-08-05T10:00:00-03:00",
            "fim": "2026-08-05T11:00:00-03:00",
            "descricao": "Pauta X",
        }
    ]


def test_listar_eventos_evento_de_dia_inteiro_usa_data_sem_horario(monkeypatch):
    _configurar_credenciais(monkeypatch)
    eventos_fake = FakeEventos(
        resposta_list={"items": [{"id": "evt2", "summary": "Feriado", "start": {"date": "2026-08-05"}, "end": {"date": "2026-08-06"}}]}
    )
    monkeypatch.setattr(google_agenda, "_servico", lambda: FakeServico(eventos_fake))

    resultado = google_agenda.listar_eventos()

    assert resultado[0]["inicio"] == "2026-08-05"
    assert resultado[0]["fim"] == "2026-08-06"
    assert resultado[0]["descricao"] == ""


def test_listar_eventos_sem_titulo_usa_texto_padrao(monkeypatch):
    _configurar_credenciais(monkeypatch)
    eventos_fake = FakeEventos(
        resposta_list={"items": [{"id": "evt3", "start": {"date": "2026-08-05"}, "end": {"date": "2026-08-06"}}]}
    )
    monkeypatch.setattr(google_agenda, "_servico", lambda: FakeServico(eventos_fake))

    resultado = google_agenda.listar_eventos()

    assert resultado[0]["titulo"] == "(sem titulo)"


def test_criar_evento_envia_corpo_correto_e_retorna_evento_criado(monkeypatch):
    _configurar_credenciais(monkeypatch)
    eventos_fake = FakeEventos()
    monkeypatch.setattr(google_agenda, "_servico", lambda: FakeServico(eventos_fake))

    resultado = google_agenda.criar_evento(
        "Dentista", datetime(2026, 8, 10, 14, 0), datetime(2026, 8, 10, 15, 0), "Consulta de rotina"
    )

    calendar_id, corpo = eventos_fake.chamadas_insert[0]
    assert calendar_id == "primary"
    assert corpo["summary"] == "Dentista"
    assert corpo["description"] == "Consulta de rotina"
    assert corpo["start"]["dateTime"] == datetime(2026, 8, 10, 14, 0).isoformat()
    assert corpo["end"]["dateTime"] == datetime(2026, 8, 10, 15, 0).isoformat()
    assert resultado["id"] == "evt123"
    assert resultado["titulo"] == "Dentista"


def test_criar_evento_sem_credenciais_configuradas(monkeypatch):
    monkeypatch.setattr(google_agenda.config, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(google_agenda.config, "GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setattr(google_agenda.config, "GOOGLE_REFRESH_TOKEN", "")

    with pytest.raises(google_agenda.GoogleAgendaError):
        google_agenda.criar_evento("Dentista", datetime(2026, 8, 10, 14, 0), datetime(2026, 8, 10, 15, 0))
