#!/usr/bin/env python3
"""
Script para popular o banco de dados no Railway com dados iniciais.
Uso: python seed_railway.py
"""
import json
import os
from pathlib import Path
from services.db import load_json_data, save_json_data

def seed_database():
    """Carrega dados dos arquivos JSON locais e os salva no banco de dados."""
    repo_root = Path(__file__).resolve().parent
    
    namespaces = [
        "jogadores",
        "users",
        "partidas",
        "historico",
        "votacoes_partidas",
        "favoritos",
        "admin_notificacoes",
        "sorteios_stack",
    ]
    
    for namespace in namespaces:
        # Tenta carregar do arquivo local
        json_file = repo_root / f"{namespace}.json"
        if not json_file.exists():
            json_file = repo_root / "data" / f"{namespace}.json"
        
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                save_json_data(namespace, data)
                print(f"✓ Seeded {namespace}: {len(data) if isinstance(data, list) else 'dict'} records")
            except Exception as e:
                print(f"✗ Error seeding {namespace}: {e}")
        else:
            print(f"⊘ File not found: {namespace}.json")
    
    print("\n✓ Seed complete!")

if __name__ == "__main__":
    seed_database()
