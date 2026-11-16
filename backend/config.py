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

# Credenciais OAuth do Google Agenda (Etapa 19). GOOGLE_CLIENT_ID/SECRET vem
# da credencial "Desktop app" criada no Google Cloud Console; GOOGLE_REFRESH_TOKEN
# e gerado uma unica vez pelo scripts/autorizar_google_agenda.py (autorizacao
# manual pelo navegador) e depois reutilizado pelo backend sem interacao, do
# mesmo jeito que o GITHUB_TOKEN (Etapa 14).
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")

# Canal do Telegram. TELEGRAM_TOKEN vem do @BotFather; TELEGRAM_DONO_ID e o
# user_id numerico do Bernardo (unico usuario atendido). TELEGRAM_WEBHOOK_SECRET
# protege a rota /telegram/webhook; KORA_URL_PUBLICA (ex:
# https://kora-ez58.onrender.com) e usada para registrar o webhook no start.
# Sem TOKEN/DONO_ID, o canal fica desligado e o resto do KORA funciona normal.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_DONO_ID = int(os.getenv("TELEGRAM_DONO_ID", "0") or 0)
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
KORA_URL_PUBLICA = os.getenv("KORA_URL_PUBLICA", "").rstrip("/")
