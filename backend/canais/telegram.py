"""Canal do Telegram: conversar com o KORA e receber avisos proativos (ex: briefing).

Dois modos, com os mesmos handlers:
- webhook (producao/Render): o Telegram faz POST em /telegram/webhook, o que
  tambem acorda o Render se ele estiver hibernando. Ver backend/main.py.
- polling (dev local): `python -m backend.canais.telegram`. Atencao: o polling
  remove o webhook; o Render o registra de novo no proximo start.

Seguranca:
- So TELEGRAM_DONO_ID e atendido. Qualquer outro usuario e registrado no log
  e ignorado em silencio (nem descobre que o bot existe).
- O webhook so aceita requisicoes com o header secreto
  (X-Telegram-Bot-Api-Secret-Token == TELEGRAM_WEBHOOK_SECRET).
- O log do httpx e silenciado: ele imprime a URL da API, que contem o token do bot.
"""

import asyncio
import logging
import secrets
import sys

from telegram import Bot, Update
from telegram.constants import ChatAction
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from backend import config
from backend.brain import briefing, conversa

logger = logging.getLogger("kora.telegram")
logging.getLogger("httpx").setLevel(logging.WARNING)

LIMITE_TELEGRAM = 4096
CAMINHO_WEBHOOK = "/telegram/webhook"


def configurado() -> bool:
    return bool(config.TELEGRAM_TOKEN and config.TELEGRAM_DONO_ID)


def webhook_secreto_valido(recebido: str | None) -> bool:
    esperado = config.TELEGRAM_WEBHOOK_SECRET
    if not esperado or not recebido:
        return False
    return secrets.compare_digest(recebido.encode(), esperado.encode())


def dividir_mensagem(texto: str, limite: int = LIMITE_TELEGRAM) -> list[str]:
    """Quebra textos maiores que o limite do Telegram, preferindo quebras de linha."""
    partes = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte <= 0:
            corte = limite
        partes.append(texto[:corte])
        texto = texto[corte:].lstrip("\n")
    if texto:
        partes.append(texto)
    return partes


async def enviar_ao_dono(texto: str) -> bool:
    """Mensagem proativa para o dono. Nunca levanta excecao: falha no Telegram nao derruba quem chamou."""
    if not configurado() or not texto:
        return False
    try:
        async with Bot(config.TELEGRAM_TOKEN) as bot:
            for parte in dividir_mensagem(texto):
                await bot.send_message(chat_id=config.TELEGRAM_DONO_ID, text=parte)
        return True
    except Exception:
        logger.exception("Falha ao enviar mensagem proativa pelo Telegram")
        return False


# ---------------------------------------------------------------- handlers


async def _negar(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    usuario = update.effective_user
    logger.warning(
        "ACESSO NEGADO no Telegram: user_id=%s username=@%s",
        usuario.id if usuario else "?",
        usuario.username if usuario else "?",
    )


async def _cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "KORA online. Pode falar.\n\n"
        "/briefing - gera o briefing do dia agora\n"
        "Qualquer outra mensagem: converso e uso o seu Vault quando precisar."
    )


async def _cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        texto = await asyncio.to_thread(briefing.gerar_briefing)
    except Exception:
        logger.exception("Falha ao gerar briefing pelo Telegram")
        await update.message.reply_text("Nao consegui gerar o briefing agora. Veja o log do servidor.")
        return
    for parte in dividir_mensagem(texto):
        await update.message.reply_text(parte)


async def _conversar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        # llm.perguntar e sincrono (SDK + Function Calling): roda fora do event loop
        texto = await asyncio.to_thread(conversa.responder, update.message.text)
    except Exception:
        logger.exception("Falha ao responder pelo Telegram")
        await update.message.reply_text("Tive um problema para responder (IA ou Vault). Tente de novo em instantes.")
        return
    for parte in dividir_mensagem(texto or "(sem resposta)"):
        await update.message.reply_text(parte)


async def _erro(_: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Erro nao tratado no Telegram", exc_info=context.error)


def criar_aplicacao(webhook: bool) -> Application:
    construtor = ApplicationBuilder().token(config.TELEGRAM_TOKEN)
    if webhook:
        construtor = construtor.updater(None)  # updates chegam pela rota do FastAPI
    aplicacao = construtor.build()

    dono = filters.User(user_id=config.TELEGRAM_DONO_ID)
    # grupo -1 roda antes de todos: barra estranhos em qualquer tipo de update
    aplicacao.add_handler(MessageHandler(~dono, _negar), group=-1)
    aplicacao.add_handler(CommandHandler("start", _cmd_start, filters=dono))
    aplicacao.add_handler(CommandHandler("briefing", _cmd_briefing, filters=dono))
    aplicacao.add_handler(MessageHandler(dono & filters.TEXT & ~filters.COMMAND, _conversar))
    aplicacao.add_error_handler(_erro)
    return aplicacao


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if not configurado():
        sys.exit("Configure TELEGRAM_TOKEN e TELEGRAM_DONO_ID no .env")
    logger.info("Telegram em modo polling. Dono: %s", config.TELEGRAM_DONO_ID)
    criar_aplicacao(webhook=False).run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
