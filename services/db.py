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

_db_disabled_until: float = 0.0


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_conn():
    global _db_disabled_until
    url = os.getenv("DATABASE_URL")
    if not url:
        return None

    now = time.time()
    if now < _db_disabled_until:
        return None

    url = _normalize_database_url(url)
    if psycopg2 is None:
        return None
    try:
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "2"))
        return psycopg2.connect(
            url,
            sslmode=os.getenv("PGSSLMODE", "require"),
            connect_timeout=connect_timeout,
        )
    except Exception as e:
        _db_disabled_until = now + 30.0
        print(f"[DB] Error connecting to Postgres: {e}. Circuit breaker active for 30s.")
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


def _get_cached(namespace: str):
    if namespace not in _cache:
        return None

    data, timestamp = _cache[namespace]
    ttl = 5 if namespace == "users" else _cache_ttl_seconds
    if time.time() - timestamp < ttl:
        return data

    del _cache[namespace]
    return None


def _set_cached(namespace: str, data) -> None:
    _cache[namespace] = (data, time.time())


def clear_db_cache(namespace: str = None) -> None:
    """Limpa o cache em memória do banco/arquivos JSON em db.py."""
    if namespace:
        _cache.pop(namespace, None)
    else:
        _cache.clear()


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
                return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"[DB] Error loading {namespace}.json ({candidate}): {e}")
                continue
    
    # Nenhuma fonte disponível
    return default


def save_json_data(namespace: str, payload) -> None:
    _set_cached(namespace, payload)

    target_path = _repo_root() / "data" / f"{namespace}.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

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
        except Exception as e:
            print(f"[DB] Error saving to Postgres: {e}")
        finally:
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


def executar_migracao_link_usuarios_jogadores() -> None:
    """
    Realiza a vinculação de usuários e jogadores pelo nome e
    limpa aqueles que não possuem correspondência (paridade).
    """
    status = load_json_data("migration_user_player_link_done", None)
    if status and isinstance(status, dict) and status.get("done"):
        print("[MIGRATION] User-Player link migration already executed.")
        return

    print("[MIGRATION] Running User-Player link and cleanup migration...")
    usuarios = load_json_data("users", [])
    jogadores = load_json_data("jogadores", [])

    # Indexar jogadores por nome limpo e lowercase
    jogadores_por_nome = {}
    for j in jogadores:
        if isinstance(j, dict):
            nome = (j.get("nome") or "").strip().lower()
            if nome:
                jogadores_por_nome[nome] = j

    # Indexar usuários por nome limpo e lowercase
    usuarios_por_nome = {}
    for u in usuarios:
        if isinstance(u, dict):
            nome = (u.get("nome") or "").strip().lower()
            if nome:
                usuarios_por_nome[nome] = u

    # Encontrar as paridades
    matched_user_ids = set()
    matched_player_ids = set()

    for nome, u in usuarios_por_nome.items():
        if nome in jogadores_por_nome:
            j = jogadores_por_nome[nome]
            j["owner_user_id"] = u["id"]
            matched_user_ids.add(u["id"])
            matched_player_ids.add(j["id"])

    # Filtrar usuários e jogadores sem paridade
    # Manter usuários admin/juiz por segurança
    novos_usuarios = []
    for u in usuarios:
        if not isinstance(u, dict):
            continue
        if u.get("id") in matched_user_ids or u.get("role") in ["admin", "juiz"]:
            novos_usuarios.append(u)

    novos_jogadores = []
    for j in jogadores:
        if not isinstance(j, dict):
            continue
        if j.get("id") in matched_player_ids:
            novos_jogadores.append(j)

    save_json_data("users", novos_usuarios)
    save_json_data("jogadores", novos_jogadores)
    save_json_data("migration_user_player_link_done", {"done": True})
    print(f"[MIGRATION] Finished: kept {len(novos_usuarios)} users and {len(novos_jogadores)} players.")


def clear_db_cache() -> None:
    """Limpa o cache em memória do banco."""
    global _cache
    _cache.clear()


def salvar_image_asset(asset_data: dict) -> dict:
    """Salva os metadados de uma imagem (Cloudinary) no namespace image_assets."""
    if not isinstance(asset_data, dict):
        return {}

    assets = load_json_data("image_assets", [])
    if not isinstance(assets, list):
        assets = []

    public_id = asset_data.get("public_id")
    asset_id = asset_data.get("asset_id")

    # Verificar se já existe registro com mesmo public_id ou asset_id (idempotência)
    indice_existente = -1
    for idx, item in enumerate(assets):
        if isinstance(item, dict):
            if (public_id and item.get("public_id") == public_id) or (asset_id and item.get("asset_id") == asset_id):
                indice_existente = idx
                break

    record = {
        "asset_id": asset_id or f"local_{int(time.time())}",
        "public_id": public_id or "",
        "resource_type": asset_data.get("resource_type", "image"),
        "format": asset_data.get("format", "jpg"),
        "width": asset_data.get("width", 0),
        "height": asset_data.get("height", 0),
        "bytes": asset_data.get("bytes", 0),
        "secure_url": asset_data.get("secure_url") or asset_data.get("url") or "",
        "url": asset_data.get("url") or asset_data.get("secure_url") or "",
        "created_at": asset_data.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "entity_type": asset_data.get("entity_type", "unknown"),
        "entity_id": str(asset_data.get("entity_id", "")),
    }

    if indice_existente >= 0:
        assets[indice_existente].update(record)
    else:
        assets.append(record)

    save_json_data("image_assets", assets)
    return record


def obter_image_asset(public_id_ou_asset_id: str) -> dict:
    """Busca os metadados de uma imagem pelo public_id ou asset_id."""
    if not public_id_ou_asset_id:
        return {}
    assets = load_json_data("image_assets", [])
    if not isinstance(assets, list):
        return {}
    for item in assets:
        if isinstance(item, dict):
            if item.get("public_id") == public_id_ou_asset_id or item.get("asset_id") == public_id_ou_asset_id:
                return item
    return {}



