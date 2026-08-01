"""Busca semantica (RAG) sobre as notas do Vault, via embeddings do Gemini.

Mantem um indice em SQLite (caminho, hash do conteudo, vetor). Reindexar e
incremental: so gera embedding novo para notas que sao novas ou mudaram de
conteudo desde a ultima vez (comparando hash), o que mantem o custo baixo em
buscas repetidas. O indice reutiliza obsidian_tool.list_notes()/read_note(),
entao pastas bloqueadas (config.VAULT_PASTAS_BLOQUEADAS) nunca sao indexadas.
"""

import hashlib
import json
import math
import sqlite3
from pathlib import Path

from google.genai import types

from backend import config
from backend.brain import llm, obsidian_tool

MODELO_EMBEDDING = "gemini-embedding-001"
DIMENSOES_EMBEDDING = 768


def _caminho_banco(caminho_banco: str | None = None) -> Path:
    return Path(caminho_banco or config.INDICE_SEMANTICO_DB_PATH)


def _conectar(caminho_banco: str | None = None) -> sqlite3.Connection:
    conexao = sqlite3.connect(_caminho_banco(caminho_banco))
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS indice_semantico (
            caminho TEXT PRIMARY KEY,
            hash_conteudo TEXT NOT NULL,
            vetor TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        )
        """
    )
    return conexao


def _hash(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _embedding(texto: str, task_type: str) -> list[float]:
    client = llm._get_client()
    cfg = types.EmbedContentConfig(output_dimensionality=DIMENSOES_EMBEDDING, task_type=task_type)
    resposta = client.models.embed_content(model=MODELO_EMBEDDING, contents=texto, config=cfg)
    return list(resposta.embeddings[0].values)


def _similaridade_cosseno(a: list[float], b: list[float]) -> float:
    produto = sum(x * y for x, y in zip(a, b, strict=True))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return produto / (norma_a * norma_b)


def reindexar(vault_path: str | None = None, caminho_banco: str | None = None) -> dict:
    """Atualiza o indice: gera embedding so para notas novas/alteradas, remove as que sumiram."""
    notas_atuais = obsidian_tool.list_notes(vault_path=vault_path)

    with _conectar(caminho_banco) as conexao:
        existentes = dict(conexao.execute("SELECT caminho, hash_conteudo FROM indice_semantico").fetchall())

        removidas = 0
        for caminho_removido in set(existentes) - set(notas_atuais):
            conexao.execute("DELETE FROM indice_semantico WHERE caminho = ?", (caminho_removido,))
            removidas += 1

        novas = atualizadas = 0
        for caminho in notas_atuais:
            conteudo = obsidian_tool.read_note(caminho, vault_path=vault_path)
            hash_atual = _hash(conteudo)
            if existentes.get(caminho) == hash_atual:
                continue

            vetor = _embedding(conteudo, task_type="RETRIEVAL_DOCUMENT")
            conexao.execute(
                """
                INSERT INTO indice_semantico (caminho, hash_conteudo, vetor, atualizado_em)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(caminho) DO UPDATE SET
                    hash_conteudo = excluded.hash_conteudo,
                    vetor = excluded.vetor,
                    atualizado_em = excluded.atualizado_em
                """,
                (caminho, hash_atual, json.dumps(vetor)),
            )
            if caminho in existentes:
                atualizadas += 1
            else:
                novas += 1

    return {"novas": novas, "atualizadas": atualizadas, "removidas": removidas, "total": len(notas_atuais)}


def buscar_por_significado(
    consulta: str,
    top_k: int = 5,
    vault_path: str | None = None,
    caminho_banco: str | None = None,
) -> list[dict]:
    """Reindexa (incremental) e retorna as `top_k` notas mais proximas da consulta por significado."""
    reindexar(vault_path=vault_path, caminho_banco=caminho_banco)

    vetor_consulta = _embedding(consulta, task_type="RETRIEVAL_QUERY")

    with _conectar(caminho_banco) as conexao:
        linhas = conexao.execute("SELECT caminho, vetor FROM indice_semantico").fetchall()

    resultados = [
        {"caminho": caminho, "pontuacao": round(_similaridade_cosseno(vetor_consulta, json.loads(vetor_json)), 4)}
        for caminho, vetor_json in linhas
    ]
    resultados.sort(key=lambda r: r["pontuacao"], reverse=True)
    return resultados[:top_k]
