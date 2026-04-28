#!/usr/bin/env bash
set -euo pipefail

# Usage:
# export DATABASE_URL='postgresql://user:pass@host:5432/dbname'
# ./scripts/backup_restore.sh backup    -> writes app_json_store_all.csv and jogadores_payload.json
# ./scripts/backup_restore.sh restore  -> reads jogadores_payload.json and upserts into app_json_store

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set. Export it first, e.g."
  echo "  export DATABASE_URL='postgresql://user:pass@host:5432/dbname'"
  exit 1
fi

COMMAND=${1:-backup}

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql not found. Install Postgres client or run this from a machine with psql."
  exit 1
fi

case "$COMMAND" in
  backup)
    echo "Backing up app_json_store to app_json_store_all.csv..."
    PGPASSFILE=${PGPASSFILE:-}
    psql "$DATABASE_URL" -c "\copy (SELECT namespace, payload FROM app_json_store) TO 'app_json_store_all.csv' WITH CSV"
    echo "Exporting jogadores payload to jogadores_payload.json..."
    psql "$DATABASE_URL" -t -A -c "SELECT payload FROM app_json_store WHERE namespace='jogadores'" > jogadores_payload.json
    echo "Done: app_json_store_all.csv and jogadores_payload.json created."
    ;;
  restore)
    if [ ! -f jogadores_payload.json ]; then
      echo "ERROR: jogadores_payload.json not found in current dir"
      exit 1
    fi
    echo "Restoring jogadores payload into app_json_store (upsert)..."
    psql "$DATABASE_URL" -c "INSERT INTO app_json_store (namespace, payload, updated_at) VALUES ('jogadores', '
$(sed -e "s/'/''/g" jogadores_payload.json)
'::jsonb, NOW()) ON CONFLICT (namespace) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW();"
    echo "Restore complete."
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo "Usage: $0 backup|restore"
    exit 2
    ;;
esac
