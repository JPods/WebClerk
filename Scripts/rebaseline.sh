#!/usr/bin/env bash
set -euo pipefail

# Rebaseline local dev DB: optional drop/create, migrate, and seed admin.
# Intended for rapid schema iteration with single-0001 migrations per app.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

# Defaults (override via env or flags)
DB_NAME="${DATABASE_NAME:-commerce_expert}"
DB_USER="${DATABASE_USER:-postgres}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
PY_BIN="${PY_BIN:-}"
SEED="1"
DROPDB="1"
CLEAN_REDIS="1"

usage() {
  cat <<EOF
Usage: Scripts/rebaseline.sh [options]

Options:
  --no-drop          Do not drop/recreate the Postgres database (migrate only)
  --no-seed          Do not create an admin user after migrate
  --no-redis         Do not touch local dump.rdb (Redis snapshot)
  --db-name NAME     Database name (default: $DB_NAME)
  --db-user USER     Database user (default: $DB_USER)
  --db-host HOST     Database host (default: $DB_HOST)
  --db-port PORT     Database port (default: $DB_PORT)
  -h, --help         Show this help

Environment overrides:
  DATABASE_NAME, DATABASE_USER, DATABASE_HOST, DATABASE_PORT
  PY_BIN (path to python; defaults to repo venv bin/python if present, else python3)
EOF
}

while [[ ${1:-} ]]; do
  case "$1" in
    --no-drop) DROPDB="0" ; shift ;;
    --no-seed) SEED="0" ; shift ;;
    --no-redis) CLEAN_REDIS="0" ; shift ;;
    --db-name) DB_NAME="$2" ; shift 2 ;;
    --db-user) DB_USER="$2" ; shift 2 ;;
    --db-host) DB_HOST="$2" ; shift 2 ;;
    --db-port) DB_PORT="$2" ; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

# Resolve python
if [[ -z "$PY_BIN" ]]; then
  if [[ -x "$ROOT_DIR/bin/python" ]]; then
    PY_BIN="$ROOT_DIR/bin/python"
  else
    PY_BIN="python3"
  fi
fi

echo "[rebaseline] Using python: $($PY_BIN -V 2>&1 || echo python3)"

# Optional: Clean Redis snapshot (harmless if absent)
if [[ "$CLEAN_REDIS" == "1" ]]; then
  if [[ -f "$ROOT_DIR/dump.rdb" ]]; then
    echo "[rebaseline] Removing Redis dump: dump.rdb"
    rm -f "$ROOT_DIR/dump.rdb"
  fi
fi

# Drop/recreate database (Postgres)
if [[ "$DROPDB" == "1" ]]; then
  echo "[rebaseline] Dropping database $DB_NAME (if exists)"
  PGPASSWORD="${DATABASE_PASS:-${PGPASSWORD:-}}" dropdb --if-exists -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" || {
    echo "[rebaseline] dropdb not available or failed; trying psql..."
    PGPASSWORD="${DATABASE_PASS:-${PGPASSWORD:-}}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" || true
    PGPASSWORD="${DATABASE_PASS:-${PGPASSWORD:-}}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" || true
  }
  echo "[rebaseline] Creating database $DB_NAME"
  PGPASSWORD="${DATABASE_PASS:-${PGPASSWORD:-}}" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" || \
  PGPASSWORD="${DATABASE_PASS:-${PGPASSWORD:-}}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";"
fi

echo "[rebaseline] Running migrations"
$PY_BIN manage.py migrate --noinput

if [[ "$SEED" == "1" ]]; then
  echo "[rebaseline] Creating/upserting admin user"
  $PY_BIN create_superuser.py --email "admin@webclerk.com" --password "admin123" --name-first "Web" --name-last "Admin" || true
fi

echo "[rebaseline] Done. You can run the server with: $PY_BIN manage.py runserver"
