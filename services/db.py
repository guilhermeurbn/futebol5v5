import json
import os
import time
from pathlib import Path
from typing import Dict, Tuple, Any

try:
    import psycopg2
    from psycopg2.extras import Json
except Exception:
    psycopg2 = None
    Json = None

# Cache em memória com TTL (5 minutos)
_cache: Dict[str, Tuple[Any, float]] = {}
_cache_ttl_seconds = 300  # 5 minutos

# SQL injection whitelist
ALLOWED_TABLES = {"app_json_store"}


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        return None

    url = _normalize_database_url(url)
    if psycopg2 is None:
        return None
    try:
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))
        return psycopg2.connect(
            url,
            sslmode=os.getenv("PGSSLMODE", "require"),
            connect_timeout=connect_timeout,
        )
    except Exception as e:
        print(f"[DB] Error connecting to Postgres: {e}")
        return None


def json_store_table_name() -> str:
    table = "app_json_store"
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' not in whitelist")
    return table


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
    yield root / "data" / "seeds" / relative_path


def _get_cached(namespace: str):
    if namespace not in _cache:
        return None

    data, timestamp = _cache[namespace]
    if time.time() - timestamp < _cache_ttl_seconds:
        return data

    del _cache[namespace]
    return None


def _set_cached(namespace: str, data) -> None:
    _cache[namespace] = (data, time.time())


def load_json_data(namespace: str, default):
    """Carrega dados JSON do cache, banco ou arquivo local como fallback."""
    cached = _get_cached(namespace)
    if cached is not None:
        return cached

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
                    data = row[0]
                    _set_cached(namespace, data)
                    return data
        except Exception as e:
            print(f"[DB] Error loading from Postgres: {e}")
        finally:
            conn.close()

    for candidate in _candidate_paths(f"{namespace}.json"):
        if candidate.exists():
            try:
                with candidate.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                _set_cached(namespace, data)

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
    _set_cached(namespace, payload)

    conn = get_conn()
    if conn is not None:
        try:
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
            return
        except Exception as e:
            print(f"[DB] Error saving to Postgres: {e}")
        finally:
            conn.close()

    target_path = None
    for candidate in _candidate_paths(f"{namespace}.json"):
        if candidate.exists():
            target_path = candidate
            break

    if target_path is None:
        target_path = _repo_root() / "data" / f"{namespace}.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


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
        # Já tem jogadores, verifica integridade
        usuarios_data = load_json_data("users", [])
        print(f"[DB] Found {len(jogadores_data)} players and {len(usuarios_data)} users, skipping auto-seed")
        print(f"[DB] Checking player-user relationships...")
        
        # Debug: verifica se há mismatches
        user_ids = {u.get("id") for u in usuarios_data if isinstance(u, dict)}
        orphan_count = 0
        for jogador in jogadores_data:
            if isinstance(jogador, dict):
                owner = jogador.get("owner_user_id")
                if owner and owner not in user_ids:
                    orphan_count += 1
        
        if orphan_count > 0:
            print(f"[DB] ⚠️  WARNING: {orphan_count} players have non-existent user owners!")
        else:
            print(f"[DB] ✓ All players have valid user relationships")
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
    
    # Validação pós-seed
    print("[DB] Validating...")
    jogadores_data = load_json_data("jogadores", [])
    usuarios_data = load_json_data("users", [])
    if jogadores_data and usuarios_data:
        print(f"[DB] ✓ POST-SEED: {len(jogadores_data)} players, {len(usuarios_data)} users loaded successfully")
    else:
        print(f"[DB] ✗ POST-SEED validation failed: players={len(jogadores_data)}, users={len(usuarios_data)}")
