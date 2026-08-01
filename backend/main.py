"""Servidor FastAPI do KORA: rotas de chat (texto e WebSocket) e frontend estatico."""

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config
from backend.brain import llm, tools
from backend.voice import tts

DIRETORIO_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="KORA")


class MensagemChat(BaseModel):
    mensagem: str


class RespostaChat(BaseModel):
    resposta: str


def exigir_token_http(authorization: str | None = Header(default=None)) -> None:
    """Exige o header `Authorization: Bearer <token>` quando KORA_ACCESS_TOKEN estiver configurado."""
    if not config.KORA_ACCESS_TOKEN:
        return
    if authorization != f"Bearer {config.KORA_ACCESS_TOKEN}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso invalido ou ausente")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=RespostaChat, dependencies=[Depends(exigir_token_http)])
def chat(corpo: MensagemChat) -> RespostaChat:
    resposta = llm.perguntar(corpo.mensagem, tools=tools.FERRAMENTAS)
    return RespostaChat(resposta=resposta.text)


@app.websocket("/ws")
async def chat_websocket(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    """Streama a resposta do Gemini em pedacos de texto e, se `voz` for pedido, envia o audio depois (em binario)."""
    await websocket.accept()

    if config.KORA_ACCESS_TOKEN and token != config.KORA_ACCESS_TOKEN:
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
                pedacos_resposta = []
                async for pedaco in llm.perguntar_stream(mensagem):
                    pedacos_resposta.append(pedaco)
                    await websocket.send_json({"tipo": "pedaco", "texto": pedaco})
                await websocket.send_json({"tipo": "fim"})

                if voz and pedacos_resposta:
                    audio = await tts.sintetizar("".join(pedacos_resposta))
                    await websocket.send_bytes(audio)
            except Exception as erro:
                await websocket.send_json({"tipo": "erro", "mensagem": str(erro)})
    except WebSocketDisconnect:
        pass


app.mount("/", StaticFiles(directory=DIRETORIO_FRONTEND, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.PORT, reload=True)
