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

# Arquivo SQLite com o historico de conversa entre sessoes. Em producao no
# Render (disco nao persistente), esse arquivo e perdido a cada cold start
# — assim como o Vault, so que sem um "GitHub" para recuperar depois. Migrar
# para armazenamento persistente e um passo futuro se isso for um problema.
HISTORICO_DB_PATH = os.getenv("HISTORICO_DB_PATH", "kora_historico.db")

# Arquivo SQLite com o indice de embeddings das notas do Vault (busca
# semantica). Mesma limitacao de disco nao persistente em producao: e
# reconstruido automaticamente (so as notas novas/alteradas sao reprocessadas,
# por hash de conteudo) na primeira busca apos um cold start.
INDICE_SEMANTICO_DB_PATH = os.getenv("INDICE_SEMANTICO_DB_PATH", "kora_indice_semantico.db")
