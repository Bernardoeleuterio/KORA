"""Servidor FastAPI do KORA: rota HTTP simples de chat por texto."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend import config
from backend.brain import llm, tools

app = FastAPI(title="KORA")


class MensagemChat(BaseModel):
    mensagem: str


class RespostaChat(BaseModel):
    resposta: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=RespostaChat)
def chat(corpo: MensagemChat) -> RespostaChat:
    resposta = llm.perguntar(corpo.mensagem, tools=tools.FERRAMENTAS)
    return RespostaChat(resposta=resposta.text)


@app.websocket("/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    """Streama a resposta do Gemini em pedacos de texto conforme sao gerados."""
    await websocket.accept()
    try:
        while True:
            dados = await websocket.receive_json()
            mensagem = dados.get("mensagem", "")
            async for pedaco in llm.perguntar_stream(mensagem):
                await websocket.send_json({"tipo": "pedaco", "texto": pedaco})
            await websocket.send_json({"tipo": "fim"})
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.PORT, reload=True)
