"""Agente proativo: gera um briefing diario a partir das notas recentes do Diario.

O briefing e salvo como uma nota normal no Vault (via obsidian_tool.write_note,
que ja commita/pusha), entao fica automaticamente sincronizado nos outros
dispositivos e pesquisavel pelas ferramentas de busca existentes (Etapa 4/17).

Para a entrega em voz (Etapa 12), o texto ja gerado aqui e sintetizado
diretamente por quem chama gerar_briefing() (ver POST /agente/briefing em
main.py) — nao pedimos para o Gemini "achar" a nota de novo via Function
Calling, porque o modo streaming (usado no /ws) nao suporta Function Calling
(limitacao do SDK descrita na Etapa 8).

Desde a Etapa 19, o briefing tambem inclui os compromissos do Google Agenda
do dia — se GOOGLE_REFRESH_TOKEN nao estiver configurado ainda, essa parte
falha em silencio (uma frase indicando que a agenda nao esta configurada),
sem quebrar o resto do briefing.
"""

from datetime import date

from backend.brain import google_agenda, llm, obsidian_tool

PASTA_DIARIO = "Diario"
QUANTIDADE_NOTAS_RECENTES = 5

INSTRUCAO_BRIEFING = (
    "Voce e a KORA. Gere um briefing matinal curto e objetivo para o Bernardo, "
    "baseado nas notas recentes do Diario dele (anexadas abaixo). Destaque o que "
    "for relevante: compromissos, tarefas pendentes, ideias registradas. Se nao "
    "houver nada relevante, diga isso em uma frase. Responda em portugues, em "
    "texto corrido, sem markdown pesado — o texto pode ser lido em voz alta."
)


def _notas_recentes_do_diario(vault_path: str | None = None) -> list[str]:
    caminhos = obsidian_tool.list_notes(PASTA_DIARIO, vault_path=vault_path)
    return sorted(caminhos)[-QUANTIDADE_NOTAS_RECENTES:]


def _compromissos_de_hoje() -> str:
    try:
        eventos = google_agenda.listar_eventos()
    except google_agenda.GoogleAgendaError:
        return "(Google Agenda nao configurado)"
    if not eventos:
        return "(nenhum compromisso na agenda para hoje)"
    linhas = [f"- {evento['titulo']} ({evento['inicio']} - {evento['fim']})" for evento in eventos]
    return "\n".join(linhas)


def gerar_briefing(salvar_no_vault: bool = True, vault_path: str | None = None) -> str:
    """Le as notas mais recentes do Diario e a agenda de hoje, gera um briefing via Gemini e (por padrao) salva no Vault."""
    caminhos = _notas_recentes_do_diario(vault_path)
    if not caminhos:
        conteudo_notas = "(nenhuma nota encontrada em Diario/)"
    else:
        partes = [f"## {caminho}\n{obsidian_tool.read_note(caminho, vault_path=vault_path)}" for caminho in caminhos]
        conteudo_notas = "\n\n".join(partes)

    compromissos = _compromissos_de_hoje()

    resposta = llm.perguntar(
        f"Compromissos de hoje na Google Agenda:\n\n{compromissos}\n\n"
        f"Notas recentes do Diario:\n\n{conteudo_notas}\n\nGere o briefing de hoje.",
        system_instruction=INSTRUCAO_BRIEFING,
    )
    texto_briefing = resposta.text

    if salvar_no_vault:
        hoje = date.today().isoformat()
        obsidian_tool.write_note(
            f"{PASTA_DIARIO}/Briefing-{hoje}.md",
            f"# Briefing {hoje}\n\n{texto_briefing}",
            commit_message=f"feat: gera briefing diario de {hoje}",
            vault_path=vault_path,
        )

    return texto_briefing
