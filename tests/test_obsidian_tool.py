import git
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


def test_buscar_por_nome_com_termo_simples(vault):
    resultado = ot.buscar_por_nome("nota", vault_path=str(vault))
    assert resultado == ["Projetos/IA/nota.md"]


def test_buscar_por_nome_ignora_maiusculas_minusculas(vault):
    resultado = ot.buscar_por_nome("NOTA", vault_path=str(vault))
    assert resultado == ["Projetos/IA/nota.md"]


def test_buscar_por_nome_com_padrao_glob_explicito(vault):
    resultado = ot.buscar_por_nome("Diario/*.md", vault_path=str(vault))
    assert resultado == ["Diario/2026-07-30.md"]


def test_buscar_por_nome_sem_correspondencia(vault):
    resultado = ot.buscar_por_nome("naoexiste", vault_path=str(vault))
    assert resultado == []


def test_buscar_por_conteudo_encontra_trecho(vault):
    resultado = ot.buscar_por_conteudo("teste", vault_path=str(vault))
    assert resultado == [{"caminho": "Projetos/IA/nota.md", "linha": 1, "trecho": "# Nota de teste"}]


def test_buscar_por_conteudo_ignora_maiusculas_minusculas(vault):
    resultado = ot.buscar_por_conteudo("HOJE", vault_path=str(vault))
    assert resultado == [{"caminho": "Diario/2026-07-30.md", "linha": 1, "trecho": "Diario de hoje."}]


def test_buscar_por_conteudo_sem_correspondencia(vault):
    resultado = ot.buscar_por_conteudo("inexistente", vault_path=str(vault))
    assert resultado == []


@pytest.fixture
def vault_git(tmp_path):
    remote_path = tmp_path / "remote.git"
    git.Repo.init(str(remote_path), bare=True)

    vault_path = tmp_path / "vault"
    repo = git.Repo.init(str(vault_path))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "KORA Test")
        cw.set_value("user", "email", "kora-test@example.com")
    repo.create_remote("origin", str(remote_path))

    (vault_path / "nota.md").write_text("conteudo inicial", encoding="utf-8")
    repo.index.add(["nota.md"])
    repo.index.commit("commit inicial")
    repo.git.push("--set-upstream", "origin", repo.active_branch.name)

    return vault_path


def test_write_note_cria_arquivo_e_commita(vault_git):
    caminho = ot.write_note("Diario/nova.md", "# Nova nota\nConteudo.", vault_path=str(vault_git))

    assert caminho.is_file()
    assert caminho.read_text(encoding="utf-8") == "# Nova nota\nConteudo."

    repo = git.Repo(vault_git)
    assert not repo.is_dirty(untracked_files=True)
    assert "cria nota" in repo.head.commit.message


def test_write_note_edita_arquivo_existente(vault_git):
    ot.write_note("nota.md", "conteudo atualizado", vault_path=str(vault_git))

    repo = git.Repo(vault_git)
    assert (vault_git / "nota.md").read_text(encoding="utf-8") == "conteudo atualizado"
    assert "atualiza nota" in repo.head.commit.message


def test_write_note_faz_push_para_o_remote(vault_git):
    ot.write_note("Diario/nova.md", "conteudo", vault_path=str(vault_git))

    repo = git.Repo(vault_git)
    branch = repo.active_branch.name
    repo.remotes.origin.fetch()
    assert repo.head.commit.hexsha == repo.remotes.origin.refs[branch].commit.hexsha


def test_write_note_pull_rebase_antes_de_editar(vault_git):
    repo_local = git.Repo(vault_git)
    remote_url = repo_local.remotes.origin.url

    outro_clone_path = vault_git.parent / "outro_clone"
    outro = git.Repo.clone_from(remote_url, str(outro_clone_path))
    with outro.config_writer() as cw:
        cw.set_value("user", "name", "Outro Clone")
        cw.set_value("user", "email", "outro@example.com")
    (outro_clone_path / "concorrente.md").write_text("mudanca concorrente", encoding="utf-8")
    outro.index.add(["concorrente.md"])
    outro.index.commit("mudanca concorrente")
    outro.remotes.origin.push()

    ot.write_note("Diario/nova.md", "conteudo novo", vault_path=str(vault_git))

    assert (vault_git / "concorrente.md").is_file()
    assert (vault_git / "Diario" / "nova.md").is_file()
