"""Leitura, escrita e sincronizacao via Git de notas do Vault do Obsidian."""

from pathlib import Path

import git

from backend import config


class VaultError(Exception):
    """Erro de configuracao ou tentativa de acesso fora do Vault."""


def _get_vault_root(vault_path: str | None = None) -> Path:
    root = vault_path or config.OBSIDIAN_VAULT_PATH
    if not root:
        raise VaultError("OBSIDIAN_VAULT_PATH nao configurado")
    return Path(root).resolve()


def _resolve_path(relative_path: str, vault_path: str | None = None) -> tuple[Path, Path]:
    root = _get_vault_root(vault_path)
    target = (root / relative_path.replace("\\", "/")).resolve()
    if target != root and root not in target.parents:
        raise VaultError(f"Caminho fora do Vault: {relative_path}")
    return root, target


def read_note(relative_path: str, vault_path: str | None = None) -> str:
    """Le o conteudo de uma nota Markdown existente no Vault."""
    _, target = _resolve_path(relative_path, vault_path)
    if not target.is_file():
        raise FileNotFoundError(f"Nota nao encontrada: {relative_path}")
    return target.read_text(encoding="utf-8")


def list_notes(subfolder: str = "", vault_path: str | None = None) -> list[str]:
    """Lista, recursivamente, os caminhos relativos de todas as notas .md a partir de subfolder."""
    root, target = _resolve_path(subfolder, vault_path)
    if not target.is_dir():
        raise FileNotFoundError(f"Pasta nao encontrada: {subfolder}")
    return sorted(p.relative_to(root).as_posix() for p in target.rglob("*.md"))


def list_folder(subfolder: str = "", vault_path: str | None = None) -> dict:
    """Lista os arquivos e subpastas imediatos de uma pasta do Vault."""
    _, target = _resolve_path(subfolder, vault_path)
    if not target.is_dir():
        raise FileNotFoundError(f"Pasta nao encontrada: {subfolder}")
    entradas = list(target.iterdir())
    return {
        "pastas": sorted(p.name for p in entradas if p.is_dir() and not p.name.startswith(".")),
        "arquivos": sorted(p.name for p in entradas if p.is_file() and not p.name.startswith(".")),
    }


def _git_pull_rebase(root: Path) -> None:
    repo = git.Repo(root)
    repo.remotes.origin.pull(rebase=True)


def _git_commit_and_push(root: Path, target: Path, message: str) -> None:
    repo = git.Repo(root)
    repo.index.add([str(target)])
    repo.index.commit(message)
    repo.remotes.origin.push()


def write_note(
    relative_path: str,
    content: str,
    commit_message: str | None = None,
    vault_path: str | None = None,
) -> Path:
    """Cria ou edita uma nota e sincroniza a alteracao via Git (pull --rebase, add, commit, push)."""
    root, target = _resolve_path(relative_path, vault_path)
    _git_pull_rebase(root)

    ja_existia = target.is_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    acao = "atualiza" if ja_existia else "cria"
    mensagem = commit_message or f"docs: {acao} nota {relative_path}"
    _git_commit_and_push(root, target, mensagem)
    return target
