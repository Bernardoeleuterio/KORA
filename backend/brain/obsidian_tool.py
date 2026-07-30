"""Leitura de notas e listagem de arquivos/pastas do Vault do Obsidian."""

from pathlib import Path

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
