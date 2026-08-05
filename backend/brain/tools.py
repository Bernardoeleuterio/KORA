"""Registro das ferramentas do Vault do Obsidian para uso via Function Calling no Gemini.

Cada funcao aqui e exposta ao llm.py como uma tool: o SDK google-genai gera o
schema a partir da assinatura e da docstring (secao "Args") e chama a funcao
Python automaticamente quando o modelo decide usa-la.
"""

from datetime import datetime, timedelta

from backend.brain import busca_semantica, google_agenda, obsidian_tool


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


def listar_eventos_agenda(dias: int = 1) -> list[dict]:
    """Lista os proximos eventos do Google Agenda dentro dos proximos N dias, a partir de agora.

    Args:
        dias: quantidade de dias a frente para buscar eventos (padrao: 1, ou seja, so as proximas 24h).
    """
    agora = datetime.now().astimezone()
    return google_agenda.listar_eventos(agora, agora + timedelta(days=dias))


def criar_evento_agenda(titulo: str, inicio: str, fim: str, descricao: str = "") -> dict:
    """Cria um evento no Google Agenda.

    Args:
        titulo: titulo do evento.
        inicio: data/hora de inicio em ISO 8601, ex: "2026-08-10T14:00:00-03:00".
        fim: data/hora de fim em ISO 8601, ex: "2026-08-10T15:00:00-03:00".
        descricao: descricao opcional do evento.
    """
    return google_agenda.criar_evento(titulo, datetime.fromisoformat(inicio), datetime.fromisoformat(fim), descricao)


def remover_evento_agenda(evento_id: str) -> str:
    """Remove um evento do Google Agenda pelo id.

    Args:
        evento_id: id do evento a remover (retornado por listar_eventos_agenda ou criar_evento_agenda).
    """
    google_agenda.remover_evento(evento_id)
    return f"Evento {evento_id} removido"


FERRAMENTAS = [
    ler_nota,
    listar_notas,
    listar_pasta,
    criar_ou_editar_nota,
    buscar_notas_por_nome,
    buscar_notas_por_conteudo,
    buscar_notas_por_significado,
    listar_eventos_agenda,
    criar_evento_agenda,
    remover_evento_agenda,
]
