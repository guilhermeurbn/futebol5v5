#!/usr/bin/env python3
"""
Script para testar se o seed funciona localmente.
Uso: python3 test_seed.py
"""
import json
from pathlib import Path
from services.db import load_json_data, save_json_data, get_database_count, _candidate_paths

def test_paths():
    """Testa se consegue encontrar os arquivos JSON."""
    print("=" * 60)
    print("TEST 1: Procurando arquivos JSON locais")
    print("=" * 60)
    
    namespaces = ["jogadores", "users", "partidas"]
    
    for namespace in namespaces:
        print(f"\n{namespace}:")
        for candidate in _candidate_paths(f"{namespace}.json"):
            exists = candidate.exists()
            status = "✓ FOUND" if exists else "✗ NOT FOUND"
            print(f"  {candidate} - {status}")
            if exists:
                with open(candidate) as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else "dict"
                    print(f"    → Loaded {count} records")
                break

def test_load_data():
    """Testa se consegue carregar dados dos JSONs."""
    print("\n" + "=" * 60)
    print("TEST 2: Carregando dados dos JSONs")
    print("=" * 60)
    
    namespaces = ["jogadores", "users", "partidas"]
    
    for namespace in namespaces:
        data = load_json_data(namespace, None)
        if data:
            count = len(data) if isinstance(data, list) else "dict"
            print(f"✓ {namespace}: Loaded {count} records")
        else:
            print(f"✗ {namespace}: Failed to load")

def test_database_status():
    """Testa o status do banco de dados."""
    print("\n" + "=" * 60)
    print("TEST 3: Status do Banco de Dados")
    print("=" * 60)
    
    count = get_database_count()
    print(f"Database records count: {count}")
    
    if count == 0:
        print("✓ Database is empty - ready for seed!")
    else:
        print("✗ Database already has data - will not auto-seed")
        print("\nTo reset and reseed:")
        print("  1. Delete all data in Railway PostgreSQL")
        print("  2. Trigger a redeploy")

def test_full_seed():
    """Testa fazer o seed completo."""
    print("\n" + "=" * 60)
    print("TEST 4: Full Seed Test")
    print("=" * 60)
    
    if get_database_count() > 0:
        print("⚠ Database not empty - skipping full seed test")
        return
    
    from services.db import auto_seed_on_init
    
    try:
        auto_seed_on_init()
        count = get_database_count()
        print(f"✓ Seed completed! Database now has {count} namespaces")
    except Exception as e:
        print(f"✗ Seed failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_paths()
    test_load_data()
    test_database_status()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
If all tests pass:
  ✓ Your local setup is correct
  
If TEST 1 or 2 fails:
  ✗ JSON files not found - check file paths
  
If TEST 3 shows database not empty:
  ✗ Clear Railway database and redeploy
  
For Railway debugging:
  1. Check the deployment logs
  2. Open Railway shell and run: python test_seed.py
  3. Check the actual error messages
    """)
