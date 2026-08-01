import asyncio

import pytest
from google.genai import errors

from backend.brain import llm


def _texto_dos_conteudos(conteudo):
    return [(c.role, c.parts[0].text) for c in conteudo]


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


class FakeModelsComErro:
    def __init__(self, erro):
        self._erro = erro

    def generate_content(self, model, contents, config):
        raise self._erro


class FakeClientComErro:
    def __init__(self, erro):
        self.models = FakeModelsComErro(erro)


class FakeAsyncModelsComErro:
    def __init__(self, erro):
        self._erro = erro

    async def generate_content_stream(self, model, contents, config):
        raise self._erro


class FakeStreamClientComErro:
    def __init__(self, erro):
        self.aio = type("FakeAio", (), {})()
        self.aio.models = FakeAsyncModelsComErro(erro)


class FakeCompletions:
    def __init__(self, texto):
        self._texto = texto
        self.chamadas = []

    def create(self, model, messages):
        self.chamadas.append({"model": model, "messages": messages})
        mensagem = type("FakeMensagem", (), {"content": self._texto})()
        escolha = type("FakeEscolha", (), {"message": mensagem})()
        return type("FakeChatCompletion", (), {"choices": [escolha]})()


class FakeOpenAIClient:
    def __init__(self, texto):
        self.chat = type("FakeChat", (), {})()
        self.chat.completions = FakeCompletions(texto)


class FakeAsyncCompletions:
    def __init__(self, pedacos):
        self._pedacos = pedacos
        self.chamadas = []

    async def create(self, model, messages, stream):
        self.chamadas.append({"model": model, "messages": messages, "stream": stream})

        async def gerador():
            for pedaco in self._pedacos:
                delta = type("FakeDelta", (), {"content": pedaco})()
                escolha = type("FakeEscolha", (), {"delta": delta})()
                yield type("FakeChunkOpenAI", (), {"choices": [escolha]})()

        return gerador()


class FakeAsyncOpenAIClient:
    def __init__(self, pedacos):
        self.chat = type("FakeChat", (), {})()
        self.chat.completions = FakeAsyncCompletions(pedacos)


def erro_cota() -> errors.ClientError:
    return errors.ClientError(429, {"error": {"message": "cota excedida", "status": "RESOURCE_EXHAUSTED"}})


def erro_nao_cota() -> errors.ClientError:
    return errors.ClientError(400, {"error": {"message": "requisicao invalida", "status": "INVALID_ARGUMENT"}})


@pytest.fixture(autouse=True)
def resetar_estado_global():
    llm._client = None
    llm._client_fallback = None
    llm._client_fallback_async = None
    llm.uso = llm.UsoGemini()
    llm.total_chamadas_fallback = 0
    yield
    llm._client = None
    llm._client_fallback = None
    llm._client_fallback_async = None
    llm.uso = llm.UsoGemini()
    llm.total_chamadas_fallback = 0


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
    assert _texto_dos_conteudos(chamada["contents"]) == [("user", "qual e a capital da franca?")]


def test_perguntar_inclui_historico_antes_da_pergunta(monkeypatch):
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", "chave-fake")
    fake_client = FakeClient(FakeResponse())
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    historico = [
        {"papel": "usuario", "conteudo": "meu cachorro se chama Rex"},
        {"papel": "kora", "conteudo": "legal, vou lembrar do Rex"},
    ]
    llm.perguntar("qual e o nome do meu cachorro?", historico=historico)

    chamada = fake_client.models.chamadas[0]
    assert _texto_dos_conteudos(chamada["contents"]) == [
        ("user", "meu cachorro se chama Rex"),
        ("model", "legal, vou lembrar do Rex"),
        ("user", "qual e o nome do meu cachorro?"),
    ]


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
    assert _texto_dos_conteudos(chamada["contents"]) == [("user", "oi")]
    assert chamada["config"].tools is None


def test_perguntar_stream_inclui_historico_antes_da_pergunta(monkeypatch):
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", "chave-fake")
    chunks = [FakeStreamChunk("ok", FakeUsageMetadata(5, 3))]
    fake_client = FakeStreamClient(chunks)
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    historico = [{"papel": "usuario", "conteudo": "oi"}, {"papel": "kora", "conteudo": "ola!"}]

    async def coletar():
        return [pedaco async for pedaco in llm.perguntar_stream("tudo bem?", historico=historico)]

    asyncio.run(coletar())

    chamada = fake_client.aio.models.chamadas[0]
    assert _texto_dos_conteudos(chamada["contents"]) == [
        ("user", "oi"),
        ("model", "ola!"),
        ("user", "tudo bem?"),
    ]


def test_eh_erro_de_cota():
    assert llm._eh_erro_de_cota(erro_cota()) is True
    assert llm._eh_erro_de_cota(erro_nao_cota()) is False
    assert llm._eh_erro_de_cota(ValueError("outra coisa")) is False


def test_perguntar_cai_para_fallback_quando_cota_do_gemini_esgota(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClientComErro(erro_cota()))
    fake_fallback = FakeOpenAIClient("resposta do fallback")
    monkeypatch.setattr(llm, "_get_client_fallback", lambda: fake_fallback)

    resposta = llm.perguntar("oi", tools=["tool-fake"], system_instruction="seja direto")

    assert resposta.text == "resposta do fallback"
    assert llm.total_chamadas_fallback == 1

    chamada = fake_fallback.chat.completions.chamadas[0]
    assert chamada["model"] == llm.MODELO_FALLBACK
    assert chamada["messages"] == [
        {"role": "system", "content": "seja direto"},
        {"role": "user", "content": "oi"},
    ]


def test_perguntar_propaga_erro_que_nao_e_de_cota(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClientComErro(erro_nao_cota()))

    with pytest.raises(errors.ClientError):
        llm.perguntar("oi")


def test_perguntar_fallback_sem_api_key_configurada(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClientComErro(erro_cota()))
    monkeypatch.setattr(llm.config, "OPENROUTER_API_KEY", "")

    with pytest.raises(RuntimeError):
        llm.perguntar("oi")


def test_perguntar_stream_cai_para_fallback_quando_cota_do_gemini_esgota(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: FakeStreamClientComErro(erro_cota()))
    fake_fallback = FakeAsyncOpenAIClient(["Ola", " fallback"])
    monkeypatch.setattr(llm, "_get_client_fallback_async", lambda: fake_fallback)

    async def coletar():
        return [pedaco async for pedaco in llm.perguntar_stream("oi")]

    pedacos = asyncio.run(coletar())

    assert pedacos == ["Ola", " fallback"]
    assert llm.total_chamadas_fallback == 1

    chamada = fake_fallback.chat.completions.chamadas[0]
    assert chamada["model"] == llm.MODELO_FALLBACK
    assert chamada["messages"] == [
        {"role": "system", "content": llm.INSTRUCAO_SISTEMA_PADRAO},
        {"role": "user", "content": "oi"},
    ]
    assert chamada["stream"] is True


def test_perguntar_stream_propaga_erro_que_nao_e_de_cota(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: FakeStreamClientComErro(erro_nao_cota()))

    async def coletar():
        return [pedaco async for pedaco in llm.perguntar_stream("oi")]

    with pytest.raises(errors.ClientError):
        asyncio.run(coletar())
