"""Instalador do KORA para rodar local (Windows, Linux ou macOS) — um comando so.

O que faz, sem nunca sobrescrever o que ja existe:
1. Cria o ambiente virtual .venv e instala o requirements.txt nele.
2. Cria o .env a partir do .env.example (se ainda nao existir).
3. Gera sozinho os segredos aleatorios (KORA_ACCESS_TOKEN e TELEGRAM_WEBHOOK_SECRET).
4. Pergunta as chaves que so voce tem (Telegram, Gemini, caminho do Vault).
   Chaves sao digitadas sem aparecer na tela e nunca sao impressas.

Uso (na pasta do KORA):
    python scripts/instalar.py               # instala dependencias + configura .env
    python scripts/instalar.py --so-env      # so configura o .env
"""

import argparse
import getpass
import os
import re
import secrets
import subprocess
import sys
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERSAO_MINIMA = (3, 11)

# Gerados automaticamente quando vazios.
SEGREDOS_GERADOS = ("KORA_ACCESS_TOKEN", "TELEGRAM_WEBHOOK_SECRET")


def _token_telegram_valido(valor: str) -> bool:
    return bool(re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{30,}", valor))


def _id_valido(valor: str) -> bool:
    return valor.isdigit() and int(valor) > 0


def _vault_valido(valor: str) -> bool:
    return Path(valor).expanduser().is_dir()


# (variavel, pergunta, secreta?, validador, mensagem de erro)
PERGUNTAS = (
    ("TELEGRAM_TOKEN", "Token do bot (@BotFather -> /newbot)", True, _token_telegram_valido,
     "formato esperado: 123456789:AAH... (numeros, dois-pontos, letras)"),
    ("TELEGRAM_DONO_ID", "Seu user_id do Telegram (fale com @userinfobot)", False, _id_valido,
     "deve ser so numeros"),
    ("GEMINI_API_KEY", "Chave do Gemini (aistudio.google.com/apikey)", True, lambda v: len(v) >= 20,
     "chave curta demais"),
    ("OBSIDIAN_VAULT_PATH", "Caminho da pasta do seu Vault do Obsidian", False, _vault_valido,
     "pasta nao encontrada"),
)


# ---------------------------------------------------------------- .env


def ler_env(texto: str) -> dict[str, str]:
    """Le pares CHAVE=valor, ignorando comentarios e linhas em branco."""
    valores = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip()
    return valores


def aplicar_valores(texto: str, novos: dict[str, str]) -> str:
    """Preenche as chaves de `novos` no texto do .env, preservando comentarios e ordem.

    So altera chaves vazias; chaves que nao existem no texto sao acrescentadas no fim.
    """
    pendentes = dict(novos)
    linhas = []
    for linha in texto.splitlines():
        chave, sep, valor = linha.partition("=")
        chave = chave.strip()
        if sep and not chave.startswith("#") and chave in pendentes and not valor.strip():
            linha = f"{chave}={pendentes.pop(chave)}"
        elif sep and chave in pendentes:
            pendentes.pop(chave)  # ja tinha valor: nunca sobrescreve
        linhas.append(linha)
    linhas += [f"{chave}={valor}" for chave, valor in pendentes.items()]
    return "\n".join(linhas) + "\n"


def gerar_segredos(atuais: dict[str, str]) -> dict[str, str]:
    return {nome: secrets.token_urlsafe(32) for nome in SEGREDOS_GERADOS if not atuais.get(nome)}


def perguntar(atuais: dict[str, str], entrada=input, entrada_secreta=getpass.getpass) -> dict[str, str]:
    respostas = {}
    for nome, pergunta, secreta, valido, erro in PERGUNTAS:
        if atuais.get(nome):
            print(f"  {nome}: ja configurado, mantendo.")
            continue
        while True:
            ler = entrada_secreta if secreta else entrada
            valor = ler(f"  {pergunta} (Enter para pular): ").strip().strip('"')
            if not valor:
                print(f"  {nome}: pulado (preencha no .env depois).")
                break
            if valido(valor):
                respostas[nome] = valor
                break
            print(f"  Valor invalido: {erro}. Tente de novo.")
    return respostas


def configurar_env(caminho_env: Path, caminho_exemplo: Path) -> None:
    print("\n[2/2] Configurando o .env")
    if not caminho_env.exists():
        caminho_env.write_text(caminho_exemplo.read_text(encoding="utf-8"), encoding="utf-8")
        print("  .env criado a partir do .env.example")

    texto = caminho_env.read_text(encoding="utf-8")
    atuais = ler_env(texto)
    novos = gerar_segredos(atuais)
    for nome in novos:
        print(f"  {nome}: gerado automaticamente.")
    novos |= perguntar(atuais)

    caminho_env.write_text(aplicar_valores(texto, novos), encoding="utf-8")
    if os.name != "nt":
        caminho_env.chmod(0o600)  # so o seu usuario le o arquivo


# ---------------------------------------------------------------- dependencias


def python_do_venv(pasta_venv: Path) -> Path:
    if os.name == "nt":
        return pasta_venv / "Scripts" / "python.exe"
    return pasta_venv / "bin" / "python"


def instalar_dependencias() -> None:
    print("[1/2] Instalando dependencias em .venv (pode levar alguns minutos)")
    pasta_venv = RAIZ / ".venv"
    if not pasta_venv.exists():
        venv.create(pasta_venv, with_pip=True)
        print("  .venv criado")
    python = python_do_venv(pasta_venv)
    subprocess.run([python, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run([python, "-m", "pip", "install", "-q", "-r", RAIZ / "requirements.txt"], check=True)
    print("  dependencias instaladas")


def proximos_passos() -> None:
    ativar = r".venv\Scripts\activate" if os.name == "nt" else "source .venv/bin/activate"
    print(f"""
Pronto. Proximos passos:
  1. {ativar}
  2. python -m pytest -q                      (todos os testes devem passar)
  3. python -m backend.canais.telegram        (KORA no Telegram, modo local)
     ou: python -m backend.main               (app web em http://localhost:8000)

Para o Render: copie do .env os valores de KORA_ACCESS_TOKEN e TELEGRAM_WEBHOOK_SECRET
para as variaveis de ambiente do servico. O KORA_ACCESS_TOKEN tambem vai no secret
de mesmo nome do GitHub (Settings > Secrets > Actions), usado pelo briefing diario.
Nunca commite o .env (ele ja esta no .gitignore).""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Instala e configura o KORA localmente.")
    parser.add_argument("--so-env", action="store_true", help="pula a instalacao de dependencias")
    args = parser.parse_args()

    if sys.version_info < VERSAO_MINIMA:
        sys.exit(f"Python {'.'.join(map(str, VERSAO_MINIMA))}+ necessario (voce tem {sys.version.split()[0]}).")

    if not args.so_env:
        instalar_dependencias()
    configurar_env(RAIZ / ".env", RAIZ / ".env.example")
    proximos_passos()


if __name__ == "__main__":
    main()
