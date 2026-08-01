from backend.brain import briefing


class FakeResposta:
    def __init__(self, text):
        self.text = text


def test_gerar_briefing_le_notas_recentes_e_gera_texto(monkeypatch):
    monkeypatch.setattr(
        briefing.obsidian_tool, "list_notes", lambda pasta, vault_path=None: ["Diario/2026-07-30.md", "Diario/2026-07-31.md"]
    )
    monkeypatch.setattr(
        briefing.obsidian_tool,
        "read_note",
        lambda caminho, vault_path=None: {"Diario/2026-07-30.md": "reuniao as 10h", "Diario/2026-07-31.md": "estudar IA"}[
            caminho
        ],
    )
    monkeypatch.setattr(briefing.obsidian_tool, "write_note", lambda *a, **k: None)

    chamadas = []

    def fake_perguntar(pergunta, system_instruction=None):
        chamadas.append((pergunta, system_instruction))
        return FakeResposta("Bom dia! Voce tem uma reuniao as 10h e quer estudar IA.")

    monkeypatch.setattr(briefing.llm, "perguntar", fake_perguntar)

    texto = briefing.gerar_briefing()

    assert texto == "Bom dia! Voce tem uma reuniao as 10h e quer estudar IA."
    assert "reuniao as 10h" in chamadas[0][0]
    assert "estudar IA" in chamadas[0][0]
    assert chamadas[0][1] == briefing.INSTRUCAO_BRIEFING


def test_gerar_briefing_considera_so_as_notas_mais_recentes(monkeypatch):
    caminhos_todos = [f"Diario/2026-07-{dia:02d}.md" for dia in range(1, 11)]
    monkeypatch.setattr(briefing.obsidian_tool, "list_notes", lambda pasta, vault_path=None: caminhos_todos)
    lidos = []
    monkeypatch.setattr(
        briefing.obsidian_tool, "read_note", lambda caminho, vault_path=None: lidos.append(caminho) or "conteudo"
    )
    monkeypatch.setattr(briefing.obsidian_tool, "write_note", lambda *a, **k: None)
    monkeypatch.setattr(briefing.llm, "perguntar", lambda pergunta, system_instruction=None: FakeResposta("ok"))

    briefing.gerar_briefing()

    assert lidos == caminhos_todos[-briefing.QUANTIDADE_NOTAS_RECENTES :]


def test_gerar_briefing_sem_notas_no_diario(monkeypatch):
    monkeypatch.setattr(briefing.obsidian_tool, "list_notes", lambda pasta, vault_path=None: [])
    monkeypatch.setattr(briefing.obsidian_tool, "write_note", lambda *a, **k: None)

    chamadas = []

    def fake_perguntar(pergunta, system_instruction=None):
        chamadas.append(pergunta)
        return FakeResposta("Sem novidades no Diario hoje.")

    monkeypatch.setattr(briefing.llm, "perguntar", fake_perguntar)

    texto = briefing.gerar_briefing()

    assert texto == "Sem novidades no Diario hoje."
    assert "nenhuma nota encontrada" in chamadas[0]


def test_gerar_briefing_salva_nota_no_vault_por_padrao(monkeypatch):
    monkeypatch.setattr(briefing.obsidian_tool, "list_notes", lambda pasta, vault_path=None: [])
    monkeypatch.setattr(briefing.llm, "perguntar", lambda pergunta, system_instruction=None: FakeResposta("briefing de teste"))

    chamadas = []
    monkeypatch.setattr(
        briefing.obsidian_tool,
        "write_note",
        lambda caminho, conteudo, commit_message=None, vault_path=None: chamadas.append(
            (caminho, conteudo, commit_message)
        ),
    )

    briefing.gerar_briefing()

    assert len(chamadas) == 1
    caminho, conteudo, _ = chamadas[0]
    assert caminho.startswith("Diario/Briefing-")
    assert caminho.endswith(".md")
    assert "briefing de teste" in conteudo


def test_gerar_briefing_nao_salva_quando_desativado(monkeypatch):
    monkeypatch.setattr(briefing.obsidian_tool, "list_notes", lambda pasta, vault_path=None: [])
    monkeypatch.setattr(briefing.llm, "perguntar", lambda pergunta, system_instruction=None: FakeResposta("ok"))

    def falha_se_chamado(*args, **kwargs):
        raise AssertionError("write_note nao deveria ser chamado quando salvar_no_vault=False")

    monkeypatch.setattr(briefing.obsidian_tool, "write_note", falha_se_chamado)

    briefing.gerar_briefing(salvar_no_vault=False)
