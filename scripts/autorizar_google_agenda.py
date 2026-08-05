"""Autorizacao unica do Google Agenda (Etapa 19) — roda localmente, uma vez so.

Pre-requisito: GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET ja preenchidos no .env,
gerados no Google Cloud Console (console.cloud.google.com) numa credencial
OAuth "Desktop app", com a "Google Calendar API" ativada no projeto.

Abre o navegador para o login/consentimento do Google e, ao final, imprime o
GOOGLE_REFRESH_TOKEN a ser colado no .env (e nas variaveis de ambiente do
Render, em producao) — depois disso o backend nunca mais precisa de navegador
para usar a agenda.

Uso: python scripts/autorizar_google_agenda.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from backend import config  # noqa: E402

ESCOPOS = ["https://www.googleapis.com/auth/calendar"]


def main() -> None:
    if not (config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET):
        print("Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env antes de rodar este script.")
        raise SystemExit(1)

    configuracao_cliente = {
        "installed": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    fluxo = InstalledAppFlow.from_client_config(configuracao_cliente, ESCOPOS)
    credenciais = fluxo.run_local_server(port=0)

    print("\nAutorizacao concluida. Adicione esta linha ao seu .env (e ao Render, em producao):\n")
    print(f"GOOGLE_REFRESH_TOKEN={credenciais.refresh_token}\n")


if __name__ == "__main__":
    main()
