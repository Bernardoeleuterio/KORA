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


def test_ferramentas_registra_as_quatro_funcoes():
    assert tools.FERRAMENTAS == [
        tools.ler_nota,
        tools.listar_notas,
        tools.listar_pasta,
        tools.criar_ou_editar_nota,
    ]
