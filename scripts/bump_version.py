#!/usr/bin/env python3
"""
Script de versionamento SemVer (MAJOR.MINOR.PATCH) para o NaTrave 5v5.

Uso:
    python scripts/bump_version.py patch   # Fix de bug (ex: 1.0.0 -> 1.0.1)
    python scripts/bump_version.py minor   # Nova funcionalidade/feature (ex: 1.0.0 -> 1.1.0)
    python scripts/bump_version.py major   # Mudança estrutural grande (ex: 1.0.0 -> 2.0.0)
    python scripts/bump_version.py set 1.2.3 # Define versão específica
"""

import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(BASE_DIR, 'data', 'version.json')

def load_version():
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler version.json: {e}")
    return {"version": "1.0.0", "major": 1, "minor": 0, "patch": 0, "formatted": "v1.0.0"}

def save_version(major, minor, patch):
    version_str = f"{major}.{minor}.{patch}"
    data = {
        "version": version_str,
        "major": major,
        "minor": minor,
        "patch": patch,
        "formatted": f"v{version_str}"
    }
    os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Versão atualizada para: v{version_str}")

def main():
    if len(sys.argv) < 2:
        current = load_version()
        print(f"Versão atual: {current.get('formatted', 'v1.0.0')}")
        print("Modo de uso: python scripts/bump_version.py [patch|minor|major|set <version>]")
        return

    action = sys.argv[1].lower().strip()
    current = load_version()
    major = current.get('major', 1)
    minor = current.get('minor', 0)
    patch = current.get('patch', 0)

    if action == 'patch':
        # Fix de bug -> incrementa terceiro número (PATCH)
        patch += 1
    elif action == 'minor':
        # Nova feature -> incrementa segundo número (MINOR) e zera o terceiro (PATCH)
        minor += 1
        patch = 0
    elif action == 'major':
        # Mudança grande -> incrementa primeiro número (MAJOR) e zera minor e patch
        major += 1
        minor = 0
        patch = 0
    elif action == 'set' and len(sys.argv) >= 3:
        target = sys.argv[2].lstrip('v').strip()
        parts = target.split('.')
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            print("Formato inválido para 'set'. Use o formato '1.2.3'.")
            return
    else:
        print("Ação desconhecida. Use patch, minor, major ou set <version>.")
        return

    save_version(major, minor, patch)

if __name__ == '__main__':
    main()
