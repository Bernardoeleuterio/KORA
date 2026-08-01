"""Registro das ferramentas do Vault do Obsidian para uso via Function Calling no Gemini.

Cada funcao aqui e exposta ao llm.py como uma tool: o SDK google-genai gera o
schema a partir da assinatura e da docstring (secao "Args") e chama a funcao
Python automaticamente quando o modelo decide usa-la.
"""

from backend.brain import busca_semantica, obsidian_tool


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


def buscar_notas_por_nome(termo: str) -> list[str]:
    """Busca notas do Vault pelo nome do arquivo ou caminho, sem precisar do caminho exato.

    Use esta ferramenta quando o usuario mencionar uma nota pelo assunto ou
    nome aproximado (ex: "a nota sobre IA") em vez do caminho completo.

    Args:
        termo: parte do nome do arquivo ou caminho a procurar; pode usar curingas glob (*, ?).
    """
    return obsidian_tool.buscar_por_nome(termo)


def buscar_notas_por_conteudo(termo: str) -> list[dict]:
    """Busca notas do Vault cujo conteudo contem o termo, retornando caminho, linha e trecho.

    Use esta ferramenta quando o usuario descrever o assunto de uma nota mas
    o termo nao aparecer no nome/caminho do arquivo.

    Args:
        termo: palavra ou trecho a procurar no conteudo das notas.
    """
    return obsidian_tool.buscar_por_conteudo(termo)


def buscar_notas_por_significado(consulta: str) -> list[dict]:
    """Busca as notas do Vault mais relevantes por significado (RAG), nao so por palavra exata.

    Use esta ferramenta quando buscar_notas_por_nome e buscar_notas_por_conteudo
    nao encontrarem nada, ou quando o usuario descrever um assunto/ideia em vez
    de citar uma palavra especifica que deveria estar na nota.

    Args:
        consulta: pergunta ou descricao do assunto a procurar no Vault.
    """
    return busca_semantica.buscar_por_significado(consulta)


FERRAMENTAS = [
    ler_nota,
    listar_notas,
    listar_pasta,
    criar_ou_editar_nota,
    buscar_notas_por_nome,
    buscar_notas_por_conteudo,
    buscar_notas_por_significado,
]
