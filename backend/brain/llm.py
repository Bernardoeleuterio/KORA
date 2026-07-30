"""Conexao com a API do Gemini (SDK google-genai) e monitoramento basico de cota."""

import logging
import time
from collections import deque

from google import genai
from google.genai import types

from backend import config

logger = logging.getLogger("kora.llm")

MODELO_PADRAO = "gemini-flash-latest"

# Salvaguarda local (nao e o limite oficial da cota do Gemini): evita que um
# loop de erro ou uso intenso por voz dispare chamadas demais em pouco tempo.
LIMITE_CHAMADAS_POR_MINUTO = 20


class LimiteDeUsoExcedido(Exception):
    """Levantada quando o numero de chamadas por minuto excede o limite local de seguranca."""


class UsoGemini:
    """Acompanha chamadas e tokens consumidos na API do Gemini durante a sessao."""

    def __init__(self, limite_por_minuto: int = LIMITE_CHAMADAS_POR_MINUTO):
        self.limite_por_minuto = limite_por_minuto
        self._chamadas: deque[float] = deque()
        self.total_chamadas = 0
        self.total_tokens_prompt = 0
        self.total_tokens_resposta = 0

    def registrar_chamada(self) -> None:
        agora = time.monotonic()
        self._chamadas.append(agora)
        while self._chamadas and agora - self._chamadas[0] > 60:
            self._chamadas.popleft()

        if len(self._chamadas) > self.limite_por_minuto:
            raise LimiteDeUsoExcedido(
                f"Mais de {self.limite_por_minuto} chamadas ao Gemini no ultimo minuto; "
                "abortando para evitar estouro de cota."
            )

    def registrar_uso(self, usage_metadata: types.GenerateContentResponseUsageMetadata | None) -> None:
        self.total_chamadas += 1
        tokens_prompt = getattr(usage_metadata, "prompt_token_count", 0) or 0
        tokens_resposta = getattr(usage_metadata, "candidates_token_count", 0) or 0
        self.total_tokens_prompt += tokens_prompt
        self.total_tokens_resposta += tokens_resposta
        logger.info(
            "Gemini: chamada #%d | tokens prompt=%d resposta=%d (acumulado: prompt=%d resposta=%d)",
            self.total_chamadas,
            tokens_prompt,
            tokens_resposta,
            self.total_tokens_prompt,
            self.total_tokens_resposta,
        )


uso = UsoGemini()

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY nao configurado")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def perguntar(
    pergunta: str,
    tools: list | None = None,
    system_instruction: str | None = None,
    model: str = MODELO_PADRAO,
) -> types.GenerateContentResponse:
    """Envia uma pergunta ao Gemini (com Function Calling/Tools opcional) e retorna a resposta."""
    uso.registrar_chamada()

    client = _get_client()
    cfg = types.GenerateContentConfig(tools=tools, system_instruction=system_instruction)
    resposta = client.models.generate_content(model=model, contents=pergunta, config=cfg)
    uso.registrar_uso(resposta.usage_metadata)
    return resposta
