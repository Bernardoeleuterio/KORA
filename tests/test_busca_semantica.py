import pytest

from backend.brain import busca_semantica as bs


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Projetos").mkdir()
    (tmp_path / "Pessoal").mkdir()
    (tmp_path / "Projetos" / "gatos.md").write_text("Tudo sobre gatos e felinos.", encoding="utf-8")
    (tmp_path / "Projetos" / "cachorros.md").write_text("Tudo sobre cachorros e caes.", encoding="utf-8")
    (tmp_path / "Pessoal" / "segredo.md").write_text("Sobre gatos tambem, mas e segredo.", encoding="utf-8")
    return tmp_path


@pytest.fixture
def banco(tmp_path):
    return str(tmp_path / "indice_teste.db")


def _embedding_fake(texto: str, task_type: str) -> list[float]:
    # Vetores unitarios ortogonais controlados pelo conteudo do texto, para
    # que a similaridade de cosseno seja previsivel nos testes.
    if "gato" in texto.lower():
        return [1.0, 0.0, 0.0]
    if "cachorro" in texto.lower() or "cao" in texto.lower() or "caes" in texto.lower():
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


@pytest.fixture(autouse=True)
def embedding_mockado(monkeypatch):
    monkeypatch.setattr(bs, "_embedding", _embedding_fake)


def test_reindexar_cria_entradas_para_notas_novas(vault, banco):
    resultado = bs.reindexar(vault_path=str(vault), caminho_banco=banco)

    assert resultado == {"novas": 2, "atualizadas": 0, "removidas": 0, "total": 2}


def test_reindexar_ignora_pasta_bloqueada(vault, banco):
    bs.reindexar(vault_path=str(vault), caminho_banco=banco)

    with bs._conectar(banco) as conexao:
        caminhos = {linha[0] for linha in conexao.execute("SELECT caminho FROM indice_semantico")}

    assert caminhos == {"Projetos/cachorros.md", "Projetos/gatos.md"}


def test_reindexar_nao_reprocessa_nota_sem_mudanca(vault, banco, monkeypatch):
    chamadas = []

    def contando(texto, task_type):
        chamadas.append(texto)
        return _embedding_fake(texto, task_type)

    monkeypatch.setattr(bs, "_embedding", contando)

    bs.reindexar(vault_path=str(vault), caminho_banco=banco)
    assert len(chamadas) == 2

    resultado = bs.reindexar(vault_path=str(vault), caminho_banco=banco)
    assert resultado == {"novas": 0, "atualizadas": 0, "removidas": 0, "total": 2}
    assert len(chamadas) == 2


def test_reindexar_atualiza_nota_alterada(vault, banco):
    bs.reindexar(vault_path=str(vault), caminho_banco=banco)

    (vault / "Projetos" / "gatos.md").write_text("Conteudo totalmente novo sobre outra coisa.", encoding="utf-8")

    resultado = bs.reindexar(vault_path=str(vault), caminho_banco=banco)

    assert resultado == {"novas": 0, "atualizadas": 1, "removidas": 0, "total": 2}


def test_reindexar_remove_nota_apagada(vault, banco):
    bs.reindexar(vault_path=str(vault), caminho_banco=banco)

    (vault / "Projetos" / "cachorros.md").unlink()

    resultado = bs.reindexar(vault_path=str(vault), caminho_banco=banco)

    assert resultado == {"novas": 0, "atualizadas": 0, "removidas": 1, "total": 1}


def test_buscar_por_significado_ordena_por_similaridade(vault, banco):
    resultados = bs.buscar_por_significado("me fale sobre gatos", vault_path=str(vault), caminho_banco=banco)

    assert resultados[0]["caminho"] == "Projetos/gatos.md"
    assert resultados[0]["pontuacao"] == 1.0
    assert resultados[1]["caminho"] == "Projetos/cachorros.md"
    assert resultados[1]["pontuacao"] == 0.0


def test_buscar_por_significado_respeita_top_k(vault, banco):
    resultados = bs.buscar_por_significado("gatos", top_k=1, vault_path=str(vault), caminho_banco=banco)

    assert len(resultados) == 1
    assert resultados[0]["caminho"] == "Projetos/gatos.md"


def test_similaridade_cosseno_vetores_ortogonais():
    assert bs._similaridade_cosseno([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_similaridade_cosseno_vetores_identicos():
    assert bs._similaridade_cosseno([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
