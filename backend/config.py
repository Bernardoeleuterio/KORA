"""Configuracoes centrais do KORA, carregadas a partir de variaveis de ambiente."""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")
KORA_ACCESS_TOKEN = os.getenv("KORA_ACCESS_TOKEN", "")
PORT = int(os.getenv("PORT", "8000"))
