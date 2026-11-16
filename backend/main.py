"""Servidor FastAPI do KORA: rotas de chat (texto e WebSocket) e frontend estatico."""

import base64
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config
from backend.brain import briefing, conversa, historico, llm, tools
from backend.canais import telegram
from backend.voice import tts

DIRETORIO_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

logger = logging.getLogger("kora.main")

# Aplicacao do Telegram em modo webhook (None quando o canal esta desligado).
aplicacao_telegram = None


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    global aplicacao_telegram
    if telegram.configurado() and config.TELEGRAM_WEBHOOK_SECRET:
        aplicacao_telegram = telegram.criar_aplicacao(webhook=True)
        await aplicacao_telegram.initialize()
        await aplicacao_telegram.start()
        if config.KORA_URL_PUBLICA:
            await aplicacao_telegram.bot.set_webhook(
                url=config.KORA_URL_PUBLICA + telegram.CAMINHO_WEBHOOK,
                secret_token=config.TELEGRAM_WEBHOOK_SECRET,
                allowed_updates=["message", "edited_message", "callback_query"],
            )
            logger.info("Webhook do Telegram registrado")
    elif telegram.configurado():
        logger.warning("Telegram configurado sem TELEGRAM_WEBHOOK_SECRET: webhook desligado por seguranca")
    try:
        yield
    finally:
        if aplicacao_telegram is not None:
            await aplicacao_telegram.stop()
            await aplicacao_telegram.shutdown()
            aplicacao_telegram = None


app = FastAPI(title="KORA", lifespan=ciclo_de_vida)


class MensagemChat(BaseModel):
    mensagem: str


class RespostaChat(BaseModel):
    resposta: str


class RespostaBriefing(BaseModel):
    briefing: str
    audio_base64: str | None = None
    enviado_telegram: bool = False


def token_valido(recebido: str | None) -> bool:
    """Compara o token recebido com KORA_ACCESS_TOKEN em tempo constante.

    Sem KORA_ACCESS_TOKEN configurado, NADA e aceito (fail-closed): um deploy
    esquecido sem a variavel nao pode deixar o Vault aberto para a internet.
    """
    esperado = config.KORA_ACCESS_TOKEN
    if not esperado or not recebido:
        return False
    return secrets.compare_digest(recebido.encode(), esperado.encode())


def exigir_token_http(authorization: str | None = Header(default=None)) -> None:
    """Exige o header `Authorization: Bearer <token>` valido em todas as rotas protegidas."""
    if not config.KORA_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KORA_ACCESS_TOKEN nao configurado no servidor",
        )
    prefixo = "Bearer "
    recebido = authorization[len(prefixo):] if authorization and authorization.startswith(prefixo) else None
    if not token_valido(recebido):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso invalido ou ausente")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=RespostaChat, dependencies=[Depends(exigir_token_http)])
def chat(corpo: MensagemChat) -> RespostaChat:
    return RespostaChat(resposta=conversa.responder(corpo.mensagem))


@app.post("/agente/briefing", response_model=RespostaBriefing, dependencies=[Depends(exigir_token_http)])
async def agente_briefing(voz: bool = False) -> RespostaBriefing:
    """Gera o briefing diario (le o Diario recente, resume via Gemini, salva no Vault).

    Pensado para ser chamado por um agendador externo (Etapa 18) — o Render
    free tier hiberna e nao roda cron interno de forma confiavel sozinho.
    Com `?voz=true`, sintetiza o audio do texto ja gerado (Etapa 12) e retorna
    junto em base64 — sem depender de Function Calling, que nao funciona no
    modo streaming usado pelo `/ws` (limitacao da Etapa 8).
    """
    texto = briefing.gerar_briefing()
    enviado = await telegram.enviar_ao_dono(texto)
    audio_base64 = None
    if voz:
        audio = await tts.sintetizar(texto)
        audio_base64 = base64.b64encode(audio).decode("ascii")
    return RespostaBriefing(briefing=texto, audio_base64=audio_base64, enviado_telegram=enviado)


@app.post(telegram.CAMINHO_WEBHOOK, include_in_schema=False)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """Recebe updates do Telegram. Responde rapido e processa em segundo plano (fila do PTB)."""
    if not telegram.webhook_secreto_valido(x_telegram_bot_api_secret_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if aplicacao_telegram is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    dados = await request.json()
    await aplicacao_telegram.update_queue.put(telegram.Update.de_json(dados, aplicacao_telegram.bot))
    return {"ok": True}


@app.websocket("/ws")
async def chat_websocket(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    """Streama a resposta do Gemini em pedacos de texto e, se `voz` for pedido, envia o audio depois (em binario)."""
    await websocket.accept()

    if not token_valido(token):
        # O handshake do WebSocket precisa ser aceito antes de fechar com um
        # codigo especifico; fechar antes do accept() produz um encerramento
        # anormal (1006) em vez do codigo 1008 esperado pelo frontend.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        while True:
            dados = await websocket.receive_json()
            mensagem = dados.get("mensagem", "")
            voz = bool(dados.get("voz", False))
            try:
                turnos_anteriores = historico.carregar_recentes()
                pedacos_resposta = []
                async for pedaco in llm.perguntar_stream(mensagem, historico=turnos_anteriores):
                    pedacos_resposta.append(pedaco)
                    await websocket.send_json({"tipo": "pedaco", "texto": pedaco})
                await websocket.send_json({"tipo": "fim"})

                resposta_completa = "".join(pedacos_resposta)
                historico.salvar_turno("usuario", mensagem)
                historico.salvar_turno("kora", resposta_completa)

                if voz and pedacos_resposta:
                    audio = await tts.sintetizar(resposta_completa)
                    await websocket.send_bytes(audio)
            except Exception as erro:
                await websocket.send_json({"tipo": "erro", "mensagem": str(erro)})
    except WebSocketDisconnect:
        pass


app.mount("/", StaticFiles(directory=DIRETORIO_FRONTEND, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.PORT, reload=True)
