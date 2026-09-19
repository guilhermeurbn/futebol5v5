#!/usr/bin/env python3
"""
Script de Migração Idempotente de Namespaces Legados do Clube 001.

Copia as chaves legadas não prefixadas ('partidas', 'jogadores', 'historico', etc.)
para o formato padronizado 'clube_001_{namespace}'.

Segurança:
- Não deleta nenhuma chave legada (mantém como backup de segurança).
- Não sobrescreve se a chave de destino 'clube_001_{namespace}' já existir.
- Suporta flag --dry-run para simulação segura sem alterar nada.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.db import get_conn, json_store_table_name, _repo_root

CHAVES_MIGRACAO = [
    "partidas",
    "jogadores",
    "historico",
    "temporadas",
    "sorteios_stack",
    "juiz_partida_atual",
    "confiabilidade_votos",
    "votacoes_partidas",
]


def migrar_postgres(dry_run: bool = False):
    conn = get_conn()
    if conn is None:
        print("[AVISO] DATABASE_URL não configurada ou erro ao conectar no Postgres.")
        return False

    tabela = json_store_table_name()
    print(f"[INFO] Conectado ao Postgres. Verificando tabela '{tabela}'...")

    try:
        with conn.cursor() as cur:
            for chave in CHAVES_MIGRACAO:
                nova_chave = f"clube_001_{chave}"

                # 1. Verifica se a nova chave já existe
                cur.execute(f"select 1 from {tabela} where namespace = %s", (nova_chave,))
                if cur.fetchone():
                    print(f"  [OK] '{nova_chave}' já existe no banco. Ignorando.")
                    continue

                # 2. Busca dado legado
                cur.execute(f"select payload from {tabela} where namespace = %s", (chave,))
                row = cur.fetchone()
                if not row:
                    print(f"  [INFO] Chave legada '{chave}' não encontrada no banco. Pulando.")
                    continue

                payload = row[0]
                print(f"  [MIGRAR] Copiando '{chave}' -> '{nova_chave}'...")

                if not dry_run:
                    from psycopg2.extras import Json
                    cur.execute(
                        f"""
                        insert into {tabela} (namespace, payload, updated_at)
                        values (%s, %s, now())
                        on conflict (namespace) do nothing
                        """,
                        (nova_chave, Json(payload)),
                    )
                    conn.commit()
                    print(f"  [SUCESSO] '{nova_chave}' criada com sucesso no Postgres.")
                else:
                    print(f"  [DRY-RUN] Simulação: '{nova_chave}' seria criada.")

        return True
    except Exception as e:
        print(f"[ERRO] Falha durante migração no Postgres: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrar_arquivos_locais(dry_run: bool = False):
    data_dir = _repo_root() / "data"
    print(f"[INFO] Verificando arquivos locais em '{data_dir}'...")

    for chave in CHAVES_MIGRACAO:
        legado_path = data_dir / f"{chave}.json"
        novo_path = data_dir / f"clube_001_{chave}.json"

        if novo_path.exists():
            print(f"  [OK] '{novo_path.name}' já existe. Ignorando.")
            continue

        if not legado_path.exists():
            continue

        try:
            with legado_path.open("r", encoding="utf-8") as f:
                dados = json.load(f)

            print(f"  [MIGRAR] Copiando '{legado_path.name}' -> '{novo_path.name}'...")
            if not dry_run:
                with novo_path.open("w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
                print(f"  [SUCESSO] '{novo_path.name}' criado com sucesso.")
            else:
                print(f"  [DRY-RUN] Simulação: '{novo_path.name}' seria criado.")
        except Exception as e:
            print(f"  [ERRO] Falha ao migrar '{legado_path.name}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Migração segura de namespaces legados para clube_001_")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simula a migração sem escrever nada")
    args = parser.parse_args()

    print("=== INICIANDO MIGRAÇÃO DE NAMESPACES PARA CLUBE 001 ===")
    if args.dry_run:
        print("[MODO DRY-RUN ATIVADO] Nenhuma alteração real será feita.")

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print("[ORIGEM] DATABASE_URL detectada. Executando no PostgreSQL...")
        migrar_postgres(dry_run=args.dry_run)
    else:
        print("[ORIGEM] Executando em ambiente local (arquivos JSON)...")
        migrar_arquivos_locais(dry_run=args.dry_run)

    print("=== MIGRAÇÃO CONCLUÍDA COM SUCESSO ===")


if __name__ == "__main__":
    main()
