import asyncio

from backend.voice import tts


class FakeCommunicate:
    def __init__(self, texto, voz):
        self.texto = texto
        self.voz = voz

    async def stream(self):
        yield {"type": "audio", "data": b"abc"}
        yield {"type": "SentenceBoundary", "data": b"ignorar"}
        yield {"type": "audio", "data": b"def"}


def test_sintetizar_concatena_apenas_chunks_de_audio(monkeypatch):
    monkeypatch.setattr(tts.edge_tts, "Communicate", FakeCommunicate)

    audio = asyncio.run(tts.sintetizar("ola, eu sou a kora"))

    assert audio == b"abcdef"


def test_sintetizar_usa_voz_informada(monkeypatch):
    instancias = []

    class FakeCommunicateRegistrado(FakeCommunicate):
        def __init__(self, texto, voz):
            super().__init__(texto, voz)
            instancias.append((texto, voz))

    monkeypatch.setattr(tts.edge_tts, "Communicate", FakeCommunicateRegistrado)

    asyncio.run(tts.sintetizar("oi", voz="pt-BR-AntonioNeural"))

    assert instancias == [("oi", "pt-BR-AntonioNeural")]


def test_sintetizar_usa_voz_padrao_por_padrao(monkeypatch):
    instancias = []

    class FakeCommunicateRegistrado(FakeCommunicate):
        def __init__(self, texto, voz):
            super().__init__(texto, voz)
            instancias.append((texto, voz))

    monkeypatch.setattr(tts.edge_tts, "Communicate", FakeCommunicateRegistrado)

    asyncio.run(tts.sintetizar("oi"))

    assert instancias == [("oi", tts.VOZ_PADRAO)]
