from backend.brain import tools


def test_ler_nota_chama_obsidian_tool(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.obsidian_tool, "read_note", lambda caminho: chamadas.append(caminho) or "conteudo da nota"
    )

    resultado = tools.ler_nota("Projetos/IA/IA.md")

    assert resultado == "conteudo da nota"
    assert chamadas == ["Projetos/IA/IA.md"]


def test_listar_notas_chama_obsidian_tool(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.obsidian_tool, "list_notes", lambda subpasta: chamadas.append(subpasta) or ["a.md", "b.md"]
    )

    resultado = tools.listar_notas("Projetos")

    assert resultado == ["a.md", "b.md"]
    assert chamadas == ["Projetos"]


def test_listar_pasta_chama_obsidian_tool(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.obsidian_tool,
        "list_folder",
        lambda subpasta: chamadas.append(subpasta) or {"pastas": [], "arquivos": ["a.md"]},
    )

    resultado = tools.listar_pasta()

    assert resultado == {"pastas": [], "arquivos": ["a.md"]}
    assert chamadas == [""]


def test_criar_ou_editar_nota_chama_obsidian_tool(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.obsidian_tool,
        "write_note",
        lambda caminho, conteudo: chamadas.append((caminho, conteudo)),
    )

    resultado = tools.criar_ou_editar_nota("Diario/2026-07-30.md", "conteudo novo")

    assert resultado == "Nota salva em Diario/2026-07-30.md"
    assert chamadas == [("Diario/2026-07-30.md", "conteudo novo")]


def test_buscar_notas_por_nome_chama_obsidian_tool(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.obsidian_tool, "buscar_por_nome", lambda termo: chamadas.append(termo) or ["a.md"]
    )

    resultado = tools.buscar_notas_por_nome("IA")

    assert resultado == ["a.md"]
    assert chamadas == ["IA"]


def test_buscar_notas_por_conteudo_chama_obsidian_tool(monkeypatch):
    chamadas = []
    resultado_esperado = [{"caminho": "a.md", "linha": 1, "trecho": "algo sobre IA"}]
    monkeypatch.setattr(
        tools.obsidian_tool,
        "buscar_por_conteudo",
        lambda termo: chamadas.append(termo) or resultado_esperado,
    )

    resultado = tools.buscar_notas_por_conteudo("IA")

    assert resultado == resultado_esperado
    assert chamadas == ["IA"]


def test_buscar_notas_por_significado_chama_busca_semantica(monkeypatch):
    chamadas = []
    resultado_esperado = [{"caminho": "a.md", "pontuacao": 0.9}]
    monkeypatch.setattr(
        tools.busca_semantica,
        "buscar_por_significado",
        lambda consulta: chamadas.append(consulta) or resultado_esperado,
    )

    resultado = tools.buscar_notas_por_significado("assunto sobre IA")

    assert resultado == resultado_esperado
    assert chamadas == ["assunto sobre IA"]


def test_listar_eventos_agenda_chama_google_agenda(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.google_agenda,
        "listar_eventos",
        lambda inicio, fim: chamadas.append((inicio, fim)) or [{"titulo": "Reuniao"}],
    )

    resultado = tools.listar_eventos_agenda(dias=3)

    assert resultado == [{"titulo": "Reuniao"}]
    assert len(chamadas) == 1
    inicio, fim = chamadas[0]
    assert (fim - inicio).days == 3


def test_criar_evento_agenda_chama_google_agenda(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        tools.google_agenda,
        "criar_evento",
        lambda titulo, inicio, fim, descricao="": chamadas.append((titulo, inicio, fim, descricao))
        or {"id": "evt1", "titulo": titulo},
    )

    resultado = tools.criar_evento_agenda(
        "Dentista", "2026-08-10T14:00:00-03:00", "2026-08-10T15:00:00-03:00", "Consulta"
    )

    assert resultado == {"id": "evt1", "titulo": "Dentista"}
    assert chamadas == [
        (
            "Dentista",
            tools.datetime.fromisoformat("2026-08-10T14:00:00-03:00"),
            tools.datetime.fromisoformat("2026-08-10T15:00:00-03:00"),
            "Consulta",
        )
    ]


def test_ferramentas_registra_todas_as_funcoes():
    assert tools.FERRAMENTAS == [
        tools.ler_nota,
        tools.listar_notas,
        tools.listar_pasta,
        tools.criar_ou_editar_nota,
        tools.buscar_notas_por_nome,
        tools.buscar_notas_por_conteudo,
        tools.buscar_notas_por_significado,
        tools.listar_eventos_agenda,
        tools.criar_evento_agenda,
    ]
