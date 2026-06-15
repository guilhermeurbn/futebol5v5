"""
migrate_nivel_float.py
─────────────────────
Converte todos os jogadores existentes de nivel int → float e
inicializa o campo historico_nivel se ausente.

Uso:
    python scripts/migrate_nivel_float.py

Seguro para rodar múltiplas vezes (idempotente).
"""
import json
import os
import sys
import shutil
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "jogadores.json")


def _backup(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dest = path + f".bak_{ts}"
    shutil.copy2(path, dest)
    return dest


def migrar():
    path = os.path.abspath(DATA_FILE)
    if not os.path.exists(path):
        print(f"[SKIP] {path} não encontrado.")
        return

    with open(path, "r", encoding="utf-8") as f:
        dados = json.load(f)

    if not isinstance(dados, list):
        print("[ERROR] Formato inesperado em jogadores.json")
        sys.exit(1)

    backup = _backup(path)
    print(f"[OK]   Backup criado: {backup}")

    alterados = 0
    for jogador in dados:
        nivel_raw = jogador.get("nivel")

        # Garantir float arredondado a 2 casas
        try:
            nivel_float = round(float(nivel_raw), 2)
        except (TypeError, ValueError):
            nivel_float = 5.0  # fallback razoável

        changed = jogador.get("nivel") != nivel_float
        jogador["nivel"] = nivel_float

        # Garantir campo historico_nivel
        if "historico_nivel" not in jogador or jogador["historico_nivel"] is None:
            jogador["historico_nivel"] = []
            changed = True

        if changed:
            alterados += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    print(f"[OK]   Migração concluída: {alterados} de {len(dados)} jogadores alterados.")


if __name__ == "__main__":
    migrar()
