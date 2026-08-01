#!/bin/sh
set -e

# O disco do plano gratuito do Render nao e persistente: a cada cold start
# (apos hibernar por inatividade) o container comeca do zero. Por isso o
# Vault e clonado aqui, em vez de ser copiado para dentro da imagem — como
# o KORA sempre commita/pusha a cada escrita (Etapa 3), nao ha estado local
# para perder entre reinicios.
if [ -n "$GITHUB_REPO" ] && [ -n "$GITHUB_TOKEN" ] && [ -n "$OBSIDIAN_VAULT_PATH" ] && [ ! -d "$OBSIDIAN_VAULT_PATH/.git" ]; then
    echo "Clonando o Vault do Obsidian ($GITHUB_REPO)..."
    git clone "https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "$OBSIDIAN_VAULT_PATH"
    git -C "$OBSIDIAN_VAULT_PATH" config user.name "KORA"
    git -C "$OBSIDIAN_VAULT_PATH" config user.email "kora@localhost"
else
    echo "Pulando clone do Vault (GITHUB_REPO/GITHUB_TOKEN/OBSIDIAN_VAULT_PATH ausentes ou Vault ja existe)."
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
