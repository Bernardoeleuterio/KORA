"""Registro das ferramentas do Vault do Obsidian para uso via Function Calling no Gemini.

Cada funcao aqui e exposta ao llm.py como uma tool: o SDK google-genai gera o
schema a partir da assinatura e da docstring (secao "Args") e chama a funcao
Python automaticamente quando o modelo decide usa-la.
"""

from backend.brain import obsidian_tool


def ler_nota(caminho_relativo: str) -> str:
    """Le o conteudo de uma nota Markdown existente no Vault do Obsidian.

    Args:
        caminho_relativo: caminho da nota a partir da raiz do Vault, ex: "Projetos/IA/IA.md".
    """
    return obsidian_tool.read_note(caminho_relativo)


def listar_notas(subpasta: str = "") -> list[str]:
    """Lista, recursivamente, os caminhos de todas as notas .md a partir de uma subpasta do Vault.

    Args:
        subpasta: subpasta do Vault onde comecar a busca; deixe vazio para o Vault inteiro.
    """
    return obsidian_tool.list_notes(subpasta)


def listar_pasta(subpasta: str = "") -> dict:
    """Lista os arquivos e subpastas imediatos de uma pasta do Vault.

    Args:
        subpasta: subpasta do Vault a listar; deixe vazio para a raiz do Vault.
    """
    return obsidian_tool.list_folder(subpasta)


def criar_ou_editar_nota(caminho_relativo: str, conteudo: str) -> str:
    """Cria uma nota nova ou edita uma nota existente no Vault, sincronizando via Git (pull, commit, push).

    Args:
        caminho_relativo: caminho da nota a partir da raiz do Vault, ex: "Diario/2026-07-30.md".
        conteudo: conteudo Markdown completo que a nota deve ter apos a operacao.
    """
    obsidian_tool.write_note(caminho_relativo, conteudo)
    return f"Nota salva em {caminho_relativo}"


FERRAMENTAS = [ler_nota, listar_notas, listar_pasta, criar_ou_editar_nota]
