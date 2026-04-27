import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        return None

    url = _normalize_database_url(url)
    return psycopg2.connect(url, sslmode=os.getenv("PGSSLMODE", "require"))


def json_store_table_name() -> str:
    return "app_json_store"


def ensure_json_store_table(conn) -> None:
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                create table if not exists {json_store_table_name()} (
                    namespace text primary key,
                    payload jsonb not null,
                    updated_at timestamptz not null default now()
                )
                """
            )


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _candidate_paths(relative_path: str):
    root = _repo_root()
    yield root / relative_path
    yield root / "data" / relative_path


def load_json_data(namespace: str, default):
    """Carrega dados JSON do banco ou do arquivo local como fallback."""
    
    # Primeiro tenta carregar do Postgres
    conn = get_conn()
    if conn is not None:
        try:
            ensure_json_store_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"select payload from {json_store_table_name()} where namespace = %s",
                    (namespace,),
                )
                row = cur.fetchone()
                if row:
                    conn.close()
                    return row[0]
        except Exception as e:
            print(f"[DB] Error loading from Postgres: {e}")
        finally:
            if conn:
                conn.close()
    
    # Se não achou no Postgres (ou não tem conexão), tenta arquivo local
    for candidate in _candidate_paths(f"{namespace}.json"):
        if candidate.exists():
            try:
                with candidate.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Se tem conexão Postgres e carregou do arquivo, salva no banco
                conn = get_conn()
                if conn is not None:
                    try:
                        save_json_data(namespace, data)
                    except Exception as e:
                        print(f"[DB] Error saving to Postgres: {e}")
                    finally:
                        conn.close()
                return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"[DB] Error loading {namespace}.json: {e}")
                break
    
    # Nenhuma fonte disponível
    return default


def save_json_data(namespace: str, payload) -> None:
    conn = get_conn()
    if conn is None:
        return

    ensure_json_store_table(conn)
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                insert into {json_store_table_name()} (namespace, payload, updated_at)
                values (%s, %s, now())
                on conflict (namespace)
                do update set payload = excluded.payload, updated_at = now()
                """,
                (namespace, Json(payload)),
            )
    conn.close()


def get_database_count() -> int:
    """Retorna o número de namespaces armazenados no banco."""
    conn = get_conn()
    if conn is None:
        return 0
    
    try:
        ensure_json_store_table(conn)
        with conn.cursor() as cur:
            cur.execute(f"select count(*) from {json_store_table_name()}")
            row = cur.fetchone()
            return row[0] if row else 0
    finally:
        conn.close()


def auto_seed_on_init() -> None:
    """
    Popula o banco de dados com dados locais se não houver jogadores.
    Chamado na inicialização da aplicação.
    """
    # Verifica se existem jogadores no banco
    jogadores_data = load_json_data("jogadores", [])
    
    if jogadores_data and len(jogadores_data) > 0:
        # Já tem jogadores, não faz nada
        print(f"[DB] Found {len(jogadores_data)} players, skipping auto-seed")
        return
    
    print("[DB] No players found, cleaning and reseeding database...")
    
    # Limpa tudo no banco
    conn = get_conn()
    if conn is not None:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {json_store_table_name()}")
                    print("[DB] Cleared old data")
        except Exception as e:
            print(f"[DB] Error clearing database: {e}")
        finally:
            conn.close()
    
    # Faz reseed completo
    root = _repo_root()
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
    
    seeded_count = 0
    for namespace in namespaces:
        for candidate in _candidate_paths(f"{namespace}.json"):
            if candidate.exists():
                try:
                    with candidate.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    save_json_data(namespace, data)
                    record_count = len(data) if isinstance(data, list) else "dict"
                    print(f"[DB] ✓ Seeded {namespace}: {record_count} records")
                    seeded_count += 1
                except Exception as e:
                    print(f"[DB] ✗ Error seeding {namespace}: {e}")
                break
    
    print(f"[DB] Reseed complete: {seeded_count}/{len(namespaces)} namespaces")