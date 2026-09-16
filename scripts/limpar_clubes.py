"""
Script para limpar clubes legados e preservar apenas o Clube 001 (NaTrave).
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from services.db import load_json_data, save_json_data, clear_db_cache
from services.clube_service import ClubeService


def resetar_clubes():
    print("[RESET_CLUBES] Iniciando limpeza de clubes...")
    clear_db_cache()
    
    clube_001 = {
        "id": 1,
        "id_num": 1,
        "code": "001",
        "codigo_formatado": "001",
        "nome": "NaTrave",
        "slug": "natrave",
        "schema": "schema_natrave",
        "theme": "neon",
        "ativo": True,
        "created_at": "2026-01-01T00:00:00Z",
        "admin_user_ids": ["admin"]
    }
    
    save_json_data("clubes", [clube_001])
    clear_db_cache()
    
    todos = ClubeService.obter_todos_clubes()
    print(f"[RESET_CLUBES] Concluído! Total de clubes no sistema: {len(todos)}")
    for c in todos:
        print(f"  - [{c.get('codigo_formatado')}] {c.get('nome')} (slug: {c.get('slug')})")


if __name__ == "__main__":
    resetar_clubes()
