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


def test_ferramentas_registra_todas_as_funcoes():
    assert tools.FERRAMENTAS == [
        tools.ler_nota,
        tools.listar_notas,
        tools.listar_pasta,
        tools.criar_ou_editar_nota,
        tools.buscar_notas_por_nome,
        tools.buscar_notas_por_conteudo,
    ]
