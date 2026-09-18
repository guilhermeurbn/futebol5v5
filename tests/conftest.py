import os
import glob
import json
import pytest

FILES_TO_PRESERVE = [
    "clubes.json",
    "jogadores.json",
    "users.json",
    "partidas.json",
    "historico.json",
    "presencas.json",
    "votacoes_partidas.json",
]


@pytest.fixture(scope="session", autouse=True)
def preservar_dados_locais_durante_testes():
    """
    Salva uma cópia de segurança dos dados locais antes do início da sessão de testes
    e restaura o estado original ao término, garantindo que testes nunca poluam o
    banco de dados local de desenvolvimento.
    """
    backup = {}
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    for fname in FILES_TO_PRESERVE:
        fpath = os.path.join(data_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    backup[fname] = json.load(f)
            except Exception:
                pass

    yield

    for fname, content in backup.items():
        fpath = os.path.join(data_dir, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Remove qualquer arquivo gerado de clube temporário durante os testes
    for fpath in glob.glob(os.path.join(data_dir, "clube_0*")):
        if "clube_001" not in fpath:
            try:
                os.remove(fpath)
            except OSError:
                pass

    for fpath in glob.glob(os.path.join(data_dir, "*test_*")):
        try:
            os.remove(fpath)
        except OSError:
            pass

    from services.db import clear_db_cache
    clear_db_cache()
