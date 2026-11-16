"""Um turno de conversa com o KORA, compartilhado por todos os canais (HTTP e Telegram).

Usa as ferramentas do Vault/Agenda (Function Calling) e grava o turno no
historico, para que a conversa continue de um canal para o outro.
"""

from backend.brain import historico, llm, tools


def responder(mensagem: str) -> str:
    turnos_anteriores = historico.carregar_recentes()
    resposta = llm.perguntar(mensagem, tools=tools.FERRAMENTAS, historico=turnos_anteriores)
    texto = (resposta.text or "").strip()
    historico.salvar_turno("usuario", mensagem)
    historico.salvar_turno("kora", texto)
    return texto
