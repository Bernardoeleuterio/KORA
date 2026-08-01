"""Sintese de voz (Text-to-Speech) via edge-tts."""

import edge_tts

VOZ_PADRAO = "pt-BR-FranciscaNeural"


async def sintetizar(texto: str, voz: str = VOZ_PADRAO) -> bytes:
    """Gera audio (mp3) a partir de um texto, usando a voz do edge-tts informada."""
    comunicador = edge_tts.Communicate(texto, voz)
    pedacos = bytearray()
    async for chunk in comunicador.stream():
        if chunk["type"] == "audio":
            pedacos.extend(chunk["data"])
    return bytes(pedacos)
