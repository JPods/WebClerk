#!/bin/bash
# WebClerk3 entrypoint — first-run detection, migration, seed, start.
# Used by both install-webclerk.sh (native) and Docker (container entrypoint).
set -e

WC3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WC3_DIR"

# Find Python
PY="${WC3_DIR}/venv/bin/python"
[ -x "$PY" ] || PY="$(which python3)"

echo "[webclerk] Checking database..."

# ── First-run detection ─────────────────────────────────────────
# If the contacts table doesn't exist, this is a fresh database.
NEEDS_MIGRATE=$("$PY" -c "
import sys, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
import django; django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='contacts')\")
exists = cursor.fetchone()[0]
print('no' if exists else 'yes')
" 2>/dev/null || echo "yes")

if [ "$NEEDS_MIGRATE" = "yes" ]; then
    echo "[webclerk] Fresh database detected — running migrations..."
    "$PY" manage.py migrate --no-input

    echo "[webclerk] Seeding system data (Settings, GL accounts, terms, RBAC)..."
    "$PY" manage.py seed_freshstart

    # Load demo data if requested
    LOAD_DEMO="${LOAD_DEMO_DATA:-0}"
    if [ "$LOAD_DEMO" = "1" ] || [ "$LOAD_DEMO" = "true" ]; then
        if [ -f "$WC3_DIR/demo-bundle.json" ]; then
            echo "[webclerk] Loading demo data from bundle..."
            "$PY" manage.py load_demo_data --data-only
        else
            echo "[webclerk] Seeding demo data..."
            "$PY" manage.py seed_demo
            "$PY" manage.py seed_demo_transactions
        fi
        echo "[webclerk] Demo data loaded."
    fi

    echo "[webclerk] First-run setup complete."
else
    # Not first run — just apply any pending migrations
    echo "[webclerk] Applying pending migrations..."
    "$PY" manage.py migrate --no-input 2>/dev/null || true
fi

# ── Generate secret key if missing ──────────────────────────────
if [ -f "$WC3_DIR/.env" ] && grep -q "change-me" "$WC3_DIR/.env" 2>/dev/null; then
    NEW_KEY=$("$PY" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/change-me-generate-a-real-key/$NEW_KEY/" "$WC3_DIR/.env"
    else
        sed -i "s/change-me-generate-a-real-key/$NEW_KEY/" "$WC3_DIR/.env"
    fi
    echo "[webclerk] Generated secret key."
fi

# ── Start ───────────────────────────────────────────────────────
# If an argument was passed, run it (Docker CMD). Otherwise start runserver.
if [ $# -gt 0 ]; then
    exec "$@"
else
    echo "[webclerk] Starting server at http://localhost:8000"
    exec "$PY" manage.py runserver 0.0.0.0:8000
fi
