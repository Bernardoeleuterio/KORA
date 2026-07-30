import pytest

from backend.brain import obsidian_tool as ot


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Projetos" / "IA").mkdir(parents=True)
    (tmp_path / "Diario").mkdir()
    (tmp_path / "Projetos" / "IA" / "nota.md").write_text("# Nota de teste\nConteudo.", encoding="utf-8")
    (tmp_path / "Diario" / "2026-07-30.md").write_text("Diario de hoje.", encoding="utf-8")
    (tmp_path / "Projetos" / "leia.txt").write_text("nao e markdown", encoding="utf-8")
    return tmp_path


def test_read_note(vault):
    conteudo = ot.read_note("Projetos/IA/nota.md", vault_path=str(vault))
    assert "Nota de teste" in conteudo


def test_read_note_inexistente(vault):
    with pytest.raises(FileNotFoundError):
        ot.read_note("Projetos/IA/nao-existe.md", vault_path=str(vault))


def test_read_note_fora_do_vault(vault):
    with pytest.raises(ot.VaultError):
        ot.read_note("../fora.md", vault_path=str(vault))


def test_list_notes(vault):
    notas = ot.list_notes(vault_path=str(vault))
    assert notas == ["Diario/2026-07-30.md", "Projetos/IA/nota.md"]


def test_list_notes_subpasta(vault):
    notas = ot.list_notes("Projetos", vault_path=str(vault))
    assert notas == ["Projetos/IA/nota.md"]


def test_list_folder_raiz(vault):
    resultado = ot.list_folder(vault_path=str(vault))
    assert resultado == {"pastas": ["Diario", "Projetos"], "arquivos": []}


def test_list_folder_subpasta(vault):
    resultado = ot.list_folder("Projetos", vault_path=str(vault))
    assert resultado == {"pastas": ["IA"], "arquivos": ["leia.txt"]}


def test_list_notes_pasta_inexistente(vault):
    with pytest.raises(FileNotFoundError):
        ot.list_notes("NaoExiste", vault_path=str(vault))
