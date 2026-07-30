import asyncio

import pytest

from backend.brain import llm


class FakeUsageMetadata:
    def __init__(self, prompt_tokens=10, response_tokens=5):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = response_tokens


class FakeResponse:
    def __init__(self, text="ok", prompt_tokens=10, response_tokens=5):
        self.text = text
        self.usage_metadata = FakeUsageMetadata(prompt_tokens, response_tokens)


class FakeModels:
    def __init__(self, response):
        self._response = response
        self.chamadas = []

    def generate_content(self, model, contents, config):
        self.chamadas.append({"model": model, "contents": contents, "config": config})
        return self._response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


class FakeStreamChunk:
    def __init__(self, text, usage_metadata):
        self.text = text
        self.usage_metadata = usage_metadata


class FakeAsyncModels:
    def __init__(self, chunks):
        self._chunks = chunks
        self.chamadas = []

    async def generate_content_stream(self, model, contents, config):
        self.chamadas.append({"model": model, "contents": contents, "config": config})

        async def gerador():
            for chunk in self._chunks:
                yield chunk

        return gerador()


class FakeStreamClient:
    def __init__(self, chunks):
        self.aio = type("FakeAio", (), {})()
        self.aio.models = FakeAsyncModels(chunks)


@pytest.fixture(autouse=True)
def resetar_estado_global():
    llm._client = None
    llm.uso = llm.UsoGemini()
    yield
    llm._client = None
    llm.uso = llm.UsoGemini()


def test_perguntar_sem_api_key_configurada(monkeypatch):
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", "")
    with pytest.raises(RuntimeError):
        llm.perguntar("ola")


def test_perguntar_retorna_resposta_e_registra_uso(monkeypatch):
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", "chave-fake")
    fake_client = FakeClient(FakeResponse(text="resposta estruturada", prompt_tokens=12, response_tokens=7))
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    resposta = llm.perguntar("qual e a capital da franca?")

    assert resposta.text == "resposta estruturada"
    assert llm.uso.total_chamadas == 1
    assert llm.uso.total_tokens_prompt == 12
    assert llm.uso.total_tokens_resposta == 7

    chamada = fake_client.models.chamadas[0]
    assert chamada["model"] == llm.MODELO_PADRAO
    assert chamada["contents"] == "qual e a capital da franca?"


def test_perguntar_passa_tools_e_system_instruction(monkeypatch):
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", "chave-fake")
    fake_client = FakeClient(FakeResponse())
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    llm.perguntar("oi", tools=["tool-fake"], system_instruction="seja direto")

    config_usada = fake_client.models.chamadas[0]["config"]
    assert config_usada.tools == ["tool-fake"]
    assert config_usada.system_instruction == "seja direto"


def test_uso_gemini_acumula_chamadas_e_tokens():
    uso = llm.UsoGemini()

    for _ in range(2):
        uso.registrar_chamada()
        uso.registrar_uso(FakeUsageMetadata(prompt_tokens=3, response_tokens=2))

    assert uso.total_chamadas == 2
    assert uso.total_tokens_prompt == 6
    assert uso.total_tokens_resposta == 4


def test_uso_gemini_levanta_erro_acima_do_limite():
    uso = llm.UsoGemini(limite_por_minuto=3)

    for _ in range(3):
        uso.registrar_chamada()

    with pytest.raises(llm.LimiteDeUsoExcedido):
        uso.registrar_chamada()


def test_uso_gemini_janela_desliza_apos_um_minuto(monkeypatch):
    uso = llm.UsoGemini(limite_por_minuto=1)
    tempos = iter([0.0, 100.0])
    monkeypatch.setattr(llm.time, "monotonic", lambda: next(tempos))

    uso.registrar_chamada()
    uso.registrar_chamada()


def test_perguntar_stream_retorna_pedacos_e_registra_uso(monkeypatch):
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", "chave-fake")
    chunks = [
        FakeStreamChunk("Ola", FakeUsageMetadata(5, 3)),
        FakeStreamChunk(" mundo", FakeUsageMetadata(5, 6)),
        FakeStreamChunk("", FakeUsageMetadata(5, 6)),
    ]
    fake_client = FakeStreamClient(chunks)
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    async def coletar():
        return [pedaco async for pedaco in llm.perguntar_stream("oi")]

    pedacos = asyncio.run(coletar())

    assert pedacos == ["Ola", " mundo"]
    assert llm.uso.total_chamadas == 1
    assert llm.uso.total_tokens_prompt == 5
    assert llm.uso.total_tokens_resposta == 6

    chamada = fake_client.aio.models.chamadas[0]
    assert chamada["model"] == llm.MODELO_PADRAO
    assert chamada["contents"] == "oi"
    assert chamada["config"].tools is None
