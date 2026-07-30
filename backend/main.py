"""Servidor FastAPI do KORA: rota HTTP simples de chat por texto."""

from fastapi import FastAPI
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.PORT, reload=True)
