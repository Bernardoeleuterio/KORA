import importlib.util
from pathlib import Path

_caminho = Path(__file__).resolve().parent.parent / "scripts" / "instalar.py"
_spec = importlib.util.spec_from_file_location("instalar", _caminho)
instalar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(instalar)

EXEMPLO = """# comentario
GEMINI_API_KEY=
KORA_ACCESS_TOKEN=
TELEGRAM_TOKEN=ja-tinha
"""


def test_ler_env_ignora_comentarios():
    assert instalar.ler_env(EXEMPLO) == {"GEMINI_API_KEY": "", "KORA_ACCESS_TOKEN": "", "TELEGRAM_TOKEN": "ja-tinha"}


def test_aplicar_valores_preenche_vazios_e_preserva_comentarios():
    texto = instalar.aplicar_valores(EXEMPLO, {"GEMINI_API_KEY": "abc", "NOVA": "x"})

    assert texto.startswith("# comentario\n")
    assert "GEMINI_API_KEY=abc\n" in texto
    assert texto.endswith("NOVA=x\n")


def test_aplicar_valores_nunca_sobrescreve():
    texto = instalar.aplicar_valores(EXEMPLO, {"TELEGRAM_TOKEN": "outro"})

    assert "TELEGRAM_TOKEN=ja-tinha" in texto
    assert "outro" not in texto


def test_gerar_segredos_so_para_vazios():
    novos = instalar.gerar_segredos({"KORA_ACCESS_TOKEN": "existente"})

    assert set(novos) == {"TELEGRAM_WEBHOOK_SECRET"}
    assert len(novos["TELEGRAM_WEBHOOK_SECRET"]) >= 40


def test_validadores():
    assert instalar._token_telegram_valido("123456789:AAH" + "x" * 32)
    assert not instalar._token_telegram_valido("sem-formato")
    assert instalar._id_valido("12345")
    assert not instalar._id_valido("-5")
    assert not instalar._id_valido("abc")


def test_perguntar_repete_valor_invalido_e_pula_os_ja_configurados(tmp_path, capsys):
    respostas = iter(["invalido", "987654321"])
    secretas = iter(["", "", ""])  # pula as chaves secretas

    resultado = instalar.perguntar(
        {"OBSIDIAN_VAULT_PATH": str(tmp_path)},
        entrada=lambda _: next(respostas),
        entrada_secreta=lambda _: next(secretas),
    )

    assert resultado == {"TELEGRAM_DONO_ID": "987654321"}
    assert "Valor invalido" in capsys.readouterr().out


def test_configurar_env_cria_arquivo_sem_vazar_segredos(tmp_path, monkeypatch, capsys):
    exemplo = tmp_path / ".env.example"
    exemplo.write_text("KORA_ACCESS_TOKEN=\nTELEGRAM_WEBHOOK_SECRET=\n", encoding="utf-8")
    env = tmp_path / ".env"
    monkeypatch.setattr(instalar, "perguntar", lambda atuais: {})

    instalar.configurar_env(env, exemplo)

    valores = instalar.ler_env(env.read_text(encoding="utf-8"))
    assert valores["KORA_ACCESS_TOKEN"] and valores["TELEGRAM_WEBHOOK_SECRET"]
    saida = capsys.readouterr().out
    assert valores["KORA_ACCESS_TOKEN"] not in saida  # segredos nunca vao para a tela

    # rodar de novo nao troca os segredos ja gerados
    instalar.configurar_env(env, exemplo)
    assert instalar.ler_env(env.read_text(encoding="utf-8")) == valores
