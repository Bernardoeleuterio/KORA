"""Configuracoes centrais do KORA, carregadas a partir de variaveis de ambiente."""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")
KORA_ACCESS_TOKEN = os.getenv("KORA_ACCESS_TOKEN", "")
PORT = int(os.getenv("PORT", "8000"))

# Pastas do Vault que o assistente nunca le, escreve, lista ou inclui em
# buscas (nem sequer aparecem como existentes). Lista separada por virgulas.
VAULT_PASTAS_BLOQUEADAS = [
    pasta.strip() for pasta in os.getenv("VAULT_PASTAS_BLOQUEADAS", "Pessoal").split(",") if pasta.strip()
]
