from backend.brain import historico


def _banco(tmp_path):
    return str(tmp_path / "teste_historico.db")


def test_salvar_e_carregar_turno(tmp_path):
    caminho = _banco(tmp_path)

    historico.salvar_turno("usuario", "ola", caminho_banco=caminho)
    historico.salvar_turno("kora", "ola, como posso ajudar?", caminho_banco=caminho)

    turnos = historico.carregar_recentes(caminho_banco=caminho)

    assert turnos == [
        {"papel": "usuario", "conteudo": "ola"},
        {"papel": "kora", "conteudo": "ola, como posso ajudar?"},
    ]


def test_carregar_recentes_retorna_em_ordem_cronologica(tmp_path):
    caminho = _banco(tmp_path)

    for i in range(5):
        historico.salvar_turno("usuario", f"mensagem {i}", caminho_banco=caminho)

    turnos = historico.carregar_recentes(caminho_banco=caminho)

    assert [t["conteudo"] for t in turnos] == [f"mensagem {i}" for i in range(5)]


def test_carregar_recentes_respeita_o_limite(tmp_path):
    caminho = _banco(tmp_path)

    for i in range(30):
        historico.salvar_turno("usuario", f"mensagem {i}", caminho_banco=caminho)

    turnos = historico.carregar_recentes(limite=5, caminho_banco=caminho)

    assert [t["conteudo"] for t in turnos] == [f"mensagem {i}" for i in range(25, 30)]


def test_carregar_recentes_filtra_por_camada(tmp_path):
    caminho = _banco(tmp_path)

    historico.salvar_turno("usuario", "mensagem normal", camada=historico.CAMADA_CONVERSA, caminho_banco=caminho)
    historico.salvar_turno("kora", "fato extraido", camada=historico.CAMADA_FATO, caminho_banco=caminho)

    turnos_conversa = historico.carregar_recentes(camada=historico.CAMADA_CONVERSA, caminho_banco=caminho)
    turnos_fato = historico.carregar_recentes(camada=historico.CAMADA_FATO, caminho_banco=caminho)

    assert turnos_conversa == [{"papel": "usuario", "conteudo": "mensagem normal"}]
    assert turnos_fato == [{"papel": "kora", "conteudo": "fato extraido"}]


def test_carregar_recentes_sem_historico_retorna_lista_vazia(tmp_path):
    caminho = _banco(tmp_path)

    assert historico.carregar_recentes(caminho_banco=caminho) == []
