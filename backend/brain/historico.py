"""Historico de conversa persistido em SQLite, para o KORA manter contexto entre sessoes.

As entradas ficam separadas por `camada`: "conversa" para o historico bruto
de mensagens (usado nesta etapa) e "fato" reservado para insights/fatos
extraidos no futuro (Etapa 17/18), sem precisar redesenhar o schema depois.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend import config

CAMADA_CONVERSA = "conversa"
CAMADA_FATO = "fato"


def _caminho_banco(caminho_banco: str | None = None) -> Path:
    return Path(caminho_banco or config.HISTORICO_DB_PATH)


def _conectar(caminho_banco: str | None = None) -> sqlite3.Connection:
    conexao = sqlite3.connect(_caminho_banco(caminho_banco))
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            papel TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            camada TEXT NOT NULL DEFAULT 'conversa',
            criado_em TEXT NOT NULL
        )
        """
    )
    return conexao


def salvar_turno(
    papel: str,
    conteudo: str,
    camada: str = CAMADA_CONVERSA,
    caminho_banco: str | None = None,
) -> None:
    """Grava uma mensagem (`papel` = "usuario" ou "kora") no historico."""
    with _conectar(caminho_banco) as conexao:
        conexao.execute(
            "INSERT INTO historico (papel, conteudo, camada, criado_em) VALUES (?, ?, ?, ?)",
            (papel, conteudo, camada, datetime.now(UTC).isoformat()),
        )


def carregar_recentes(
    limite: int = 20,
    camada: str = CAMADA_CONVERSA,
    caminho_banco: str | None = None,
) -> list[dict]:
    """Le as `limite` mensagens mais recentes da camada informada, em ordem cronologica."""
    with _conectar(caminho_banco) as conexao:
        cursor = conexao.execute(
            "SELECT papel, conteudo FROM historico WHERE camada = ? ORDER BY id DESC LIMIT ?",
            (camada, limite),
        )
        linhas = cursor.fetchall()
    linhas.reverse()
    return [{"papel": papel, "conteudo": conteudo} for papel, conteudo in linhas]
