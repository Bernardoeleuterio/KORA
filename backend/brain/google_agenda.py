"""Integracao com o Google Agenda (Google Calendar API) via OAuth 2.0.

Autenticacao no modelo "installed app": o usuario autoriza uma unica vez,
rodando scripts/autorizar_google_agenda.py (abre o navegador, pede consentimento
e devolve um refresh token). Dali em diante, as chamadas aqui renovam o access
token sozinhas a partir do refresh token guardado em config.py — sem navegador,
mesmo padrao ja usado pelo GITHUB_TOKEN desde a Etapa 14. Conta de servico
(Service Account) nao serve aqui: contas pessoais @gmail.com nao suportam
delegacao de dominio, so contas Google Workspace.
"""

from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend import config

ESCOPOS = ["https://www.googleapis.com/auth/calendar"]


class GoogleAgendaError(Exception):
    """Erro de configuracao ou de chamada a API do Google Agenda."""


def _credenciais() -> Credentials:
    if not (config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET and config.GOOGLE_REFRESH_TOKEN):
        raise GoogleAgendaError(
            "Google Agenda nao configurado: defina GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e "
            "GOOGLE_REFRESH_TOKEN (veja scripts/autorizar_google_agenda.py)."
        )
    return Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=ESCOPOS,
    )


def _servico():
    return build("calendar", "v3", credentials=_credenciais(), cache_discovery=False)


def _formatar_evento(item: dict) -> dict:
    return {
        "id": item["id"],
        "titulo": item.get("summary", "(sem titulo)"),
        "inicio": item["start"].get("dateTime", item["start"].get("date")),
        "fim": item["end"].get("dateTime", item["end"].get("date")),
        "descricao": item.get("description", ""),
    }


def listar_eventos(data_inicio: datetime | None = None, data_fim: datetime | None = None, max_resultados: int = 10) -> list[dict]:
    """Lista eventos do calendario primario entre data_inicio e data_fim (padrao: proximas 24h)."""
    inicio = data_inicio or datetime.now().astimezone()
    fim = data_fim or (inicio + timedelta(days=1))

    resposta = (
        _servico()
        .events()
        .list(
            calendarId="primary",
            timeMin=inicio.isoformat(),
            timeMax=fim.isoformat(),
            maxResults=max_resultados,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return [_formatar_evento(item) for item in resposta.get("items", [])]


def criar_evento(titulo: str, inicio: datetime, fim: datetime, descricao: str = "") -> dict:
    """Cria um evento no calendario primario e retorna o evento criado (com o id gerado)."""
    corpo = {
        "summary": titulo,
        "description": descricao,
        "start": {"dateTime": inicio.isoformat()},
        "end": {"dateTime": fim.isoformat()},
    }
    item = _servico().events().insert(calendarId="primary", body=corpo).execute()
    return _formatar_evento(item)
