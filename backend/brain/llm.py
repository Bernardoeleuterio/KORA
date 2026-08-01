"""Conexao com a API do Gemini (SDK google-genai) e monitoramento basico de cota."""

import logging
import time
from collections import deque
from typing import AsyncIterator

from google import genai
from google.genai import errors, types
from openai import AsyncOpenAI, OpenAI

from backend import config

logger = logging.getLogger("kora.llm")

MODELO_PADRAO = "gemini-3.1-flash-lite"

# Fallback usado quando a cota do Gemini esgota: "openrouter/free" e um
# roteador da OpenRouter que escolhe automaticamente entre varios modelos
# gratuitos disponiveis, dando redundancia entre provedores sem precisar
# integrar cada um deles manualmente. Nao suporta Function Calling, entao
# conversas com `tools` perdem acesso as ferramentas do Vault nesse modo.
MODELO_FALLBACK = "openrouter/free"
URL_BASE_OPENROUTER = "https://openrouter.ai/api/v1"

INSTRUCAO_SISTEMA_PADRAO = (
    "Voce e a KORA, uma assistente pessoal de IA do genero feminino: fale de si mesma no feminino. "
    "O usuario com quem voce esta conversando se chama Bernardo: ele e o criador da KORA, "
    "responsavel pelo seu desenvolvimento."
)

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
total_chamadas_fallback = 0

_client: genai.Client | None = None
_client_fallback: OpenAI | None = None
_client_fallback_async: AsyncOpenAI | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY nao configurado")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _get_client_fallback() -> OpenAI:
    global _client_fallback
    if _client_fallback is None:
        if not config.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY nao configurado")
        _client_fallback = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=URL_BASE_OPENROUTER)
    return _client_fallback


def _get_client_fallback_async() -> AsyncOpenAI:
    global _client_fallback_async
    if _client_fallback_async is None:
        if not config.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY nao configurado")
        _client_fallback_async = AsyncOpenAI(api_key=config.OPENROUTER_API_KEY, base_url=URL_BASE_OPENROUTER)
    return _client_fallback_async


def _eh_erro_de_cota(erro: Exception) -> bool:
    return isinstance(erro, errors.ClientError) and erro.code == 429


def _montar_conteudo_gemini(pergunta: str, historico: list[dict] | None) -> list[types.Content]:
    conteudo = [
        types.Content(role="model" if turno["papel"] == "kora" else "user", parts=[types.Part(text=turno["conteudo"])])
        for turno in historico or []
    ]
    conteudo.append(types.Content(role="user", parts=[types.Part(text=pergunta)]))
    return conteudo


def _montar_mensagens(pergunta: str, system_instruction: str | None, historico: list[dict] | None = None) -> list[dict]:
    mensagens = []
    if system_instruction:
        mensagens.append({"role": "system", "content": system_instruction})
    for turno in historico or []:
        papel = "assistant" if turno["papel"] == "kora" else "user"
        mensagens.append({"role": papel, "content": turno["conteudo"]})
    mensagens.append({"role": "user", "content": pergunta})
    return mensagens


def _registrar_uso_fallback() -> None:
    global total_chamadas_fallback
    total_chamadas_fallback += 1
    logger.info("Fallback (%s): chamada #%d", MODELO_FALLBACK, total_chamadas_fallback)


class RespostaFallback:
    """Resposta do provedor de fallback, com a mesma interface minima (.text) usada no resto do KORA."""

    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = None


def _perguntar_fallback(
    pergunta: str, system_instruction: str | None = None, historico: list[dict] | None = None
) -> RespostaFallback:
    cliente = _get_client_fallback()
    resposta = cliente.chat.completions.create(
        model=MODELO_FALLBACK, messages=_montar_mensagens(pergunta, system_instruction, historico)
    )
    _registrar_uso_fallback()
    return RespostaFallback(resposta.choices[0].message.content)


async def _perguntar_fallback_stream(
    pergunta: str, system_instruction: str | None = None, historico: list[dict] | None = None
) -> AsyncIterator[str]:
    cliente = _get_client_fallback_async()
    stream = await cliente.chat.completions.create(
        model=MODELO_FALLBACK, messages=_montar_mensagens(pergunta, system_instruction, historico), stream=True
    )
    async for chunk in stream:
        pedaco = chunk.choices[0].delta.content
        if pedaco:
            yield pedaco
    _registrar_uso_fallback()


def perguntar(
    pergunta: str,
    tools: list | None = None,
    system_instruction: str | None = INSTRUCAO_SISTEMA_PADRAO,
    model: str = MODELO_PADRAO,
    historico: list[dict] | None = None,
) -> types.GenerateContentResponse:
    """Envia uma pergunta ao Gemini (com Function Calling/Tools opcional) e retorna a resposta.

    `historico`, se informado, e uma lista de turnos anteriores (formato
    `{"papel": "usuario"|"kora", "conteudo": str}`, ver backend/brain/historico.py)
    incluida antes de `pergunta`, para o modelo manter contexto entre sessoes.

    Se a cota do Gemini estiver esgotada (HTTP 429), cai automaticamente para
    o fallback (`MODELO_FALLBACK`, via OpenRouter). O fallback nao suporta
    Function Calling: se `tools` for informado, as ferramentas do Vault
    ficam indisponiveis nessa resposta.
    """
    uso.registrar_chamada()

    client = _get_client()
    cfg = types.GenerateContentConfig(tools=tools, system_instruction=system_instruction)
    conteudo = _montar_conteudo_gemini(pergunta, historico)
    try:
        resposta = client.models.generate_content(model=model, contents=conteudo, config=cfg)
    except errors.ClientError as erro:
        if not _eh_erro_de_cota(erro):
            raise
        if tools:
            logger.warning(
                "Fallback (%s) nao suporta Function Calling; ferramentas do Vault indisponiveis nesta resposta.",
                MODELO_FALLBACK,
            )
        logger.warning("Gemini indisponivel (cota excedida); usando fallback %s", MODELO_FALLBACK)
        return _perguntar_fallback(pergunta, system_instruction, historico)

    uso.registrar_uso(resposta.usage_metadata)
    return resposta


async def perguntar_stream(
    pergunta: str,
    system_instruction: str | None = INSTRUCAO_SISTEMA_PADRAO,
    model: str = MODELO_PADRAO,
    historico: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Envia uma pergunta ao Gemini e streama a resposta em pedacos de texto.

    `historico`, se informado, e uma lista de turnos anteriores (ver
    backend/brain/historico.py) incluida antes de `pergunta`, para o modelo
    manter contexto entre sessoes.

    Nao aceita `tools`: no SDK google-genai instalado, o Function Calling
    automatico perde a resposta da ferramenta quando combinado com streaming
    (o resultado da chamada e sobrescrito pelo chunk final vazio, e a
    resposta do modelo nunca chega). Para conversas que dependem das
    ferramentas do Vault, use perguntar().

    Se a cota do Gemini estiver esgotada (HTTP 429), cai automaticamente
    para o fallback (`MODELO_FALLBACK`, via OpenRouter).
    """
    uso.registrar_chamada()

    client = _get_client()
    cfg = types.GenerateContentConfig(system_instruction=system_instruction)
    conteudo = _montar_conteudo_gemini(pergunta, historico)

    try:
        stream = await client.aio.models.generate_content_stream(model=model, contents=conteudo, config=cfg)
    except errors.ClientError as erro:
        if not _eh_erro_de_cota(erro):
            raise
        logger.warning("Gemini indisponivel (cota excedida); usando fallback %s em streaming", MODELO_FALLBACK)
        async for pedaco in _perguntar_fallback_stream(pergunta, system_instruction, historico):
            yield pedaco
        return

    ultima_metadata = None
    async for chunk in stream:
        if chunk.text:
            yield chunk.text
        ultima_metadata = chunk.usage_metadata
    uso.registrar_uso(ultima_metadata)
