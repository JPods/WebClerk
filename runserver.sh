#!/bin/bash
set -e

WC3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESTART_REQUEST_FILE="$WC3_DIR/tools/.restart_django"
ENV_FILE="$WC3_DIR/.env"
DEV_CONFIG_FILE="$WC3_DIR/tools/dev-config.json"

cd "$WC3_DIR"

PY_BIN="$WC3_DIR/venv/bin/python"
if [ ! -x "$PY_BIN" ]; then
  PY_BIN="$WC3_DIR/bin/python"  # legacy fallback
fi
if [ ! -x "$PY_BIN" ]; then
  echo "ERROR: No Python found. Run: /opt/homebrew/bin/python3 -m venv venv"
  exit 1
fi

echo "Starting Django with same-terminal auto-restart loop"
echo "Use this command for dev: ./runserver.sh [local|remote]"

# Accept optional argument: ./runserver.sh local|remote  (default: local)
INITIAL_DB_MODE="${1:-local}"
if [[ "$INITIAL_DB_MODE" != "local" && "$INITIAL_DB_MODE" != "remote" ]]; then
  echo "Usage: ./runserver.sh [local|remote]  (default: local)"
  exit 1
fi

ensure_default_mode() {
  local mode="$INITIAL_DB_MODE"
  if [ -f "$ENV_FILE" ]; then
    if grep -q '^DB_MODE=' "$ENV_FILE"; then
      sed -i '' "s/^DB_MODE=.*/DB_MODE=$mode/" "$ENV_FILE"
    else
      echo "DB_MODE=$mode" >> "$ENV_FILE"
    fi
  fi

  if [ -f "$DEV_CONFIG_FILE" ]; then
    python3 << EOF
import json
from pathlib import Path
path = Path("$DEV_CONFIG_FILE")
config = json.loads(path.read_text())
config["db_mode"] = "$mode"
path.write_text(json.dumps(config, indent=2))
EOF
  fi

  echo "DB mode set to: $mode"
}

free_port_8000() {
  local pids
  pids=$(lsof -ti:8000 2>/dev/null || true)
  if [ -z "$pids" ]; then
    return
  fi

  echo "Port 8000 is in use. Stopping existing process(es): $pids"
  echo "$pids" | xargs kill -TERM 2>/dev/null || true
  sleep 1

  local remaining
  remaining=$(lsof -ti:8000 2>/dev/null || true)
  if [ -n "$remaining" ]; then
    echo "$remaining" | xargs kill -KILL 2>/dev/null || true
  fi
}

ensure_default_mode
free_port_8000

# ── Start Celery worker+beat in the background ──────────────────
start_celery() {
  # Kill any existing celery processes for this project
  pkill -f "celery -A webclerk3_api" 2>/dev/null || true
  sleep 1

  echo "Starting Celery worker+beat in background..."
  "$PY_BIN" -m celery -A webclerk3_api worker \
    -l info \
    --concurrency=2 \
    -P solo \
    --without-heartbeat \
    -B \
    -s /tmp/celerybeat-webclerk3-schedule \
    >> "$WC3_DIR/logs/celery.log" 2>&1 &
  CELERY_PID=$!
  echo "Celery PID: $CELERY_PID (log: logs/celery.log)"
}

stop_celery() {
  pkill -f "celery -A webclerk3_api" 2>/dev/null || true
}

print_prime_startup_info() {
  echo "[startup] Prime setting + org snapshot"
  "$PY_BIN" manage.py shell <<'PY' || true
from apps.core.models import Setting
from apps.orgs.models import OrgBase

rows = list(Setting.objects.filter(purpose='db_defaults', name='primary_organization', is_active=True).order_by('-id')[:1])
if not rows:
    print('[startup] primary_organization setting: MISSING')
    raise SystemExit(0)

s = rows[0]
d = s.data or {}
model_name = d.get('model_name') or d.get('org_type') or 'customer'
org_id = d.get('id') or d.get('org_id')
print(f"[startup] setting_id={s.id} model_name={model_name} id={org_id} company={d.get('company')}")

if not org_id:
    print('[startup] prime org: MISSING id in setting.data (id/org_id)')
    raise SystemExit(0)

try:
    oid = int(org_id)
except Exception:
    print(f"[startup] prime org: INVALID id value: {org_id}")
    raise SystemExit(0)

org = OrgBase.objects.filter(pk=oid).first()
if not org:
    print(f"[startup] prime org: NOT FOUND id={oid}")
    raise SystemExit(0)

print(
    f"[startup] prime org id={org.id} org_type={org.org_type} "
    f"company={org.company} phone={org.phone} email={org.email} "
    f"attention={getattr(org, 'attention', None)} address_full={getattr(org, 'address_full', None)}"
)
PY
}

# ── Ensure Ollama is running for LLM features ───────────────────
ensure_ollama() {
  # Check if ollama is installed
  if ! command -v ollama &>/dev/null; then
    echo "Warning: Ollama not installed - LLM features will not work"
    echo "Install with: brew install ollama"
    return 1
  fi

  if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama is already running"
    return 0
  fi

  echo "Starting Ollama in background..."
  ollama serve >> "$WC3_DIR/logs/ollama.log" 2>&1 &
  OLLAMA_PID=$!
  
  # Wait for Ollama to be ready (up to 10 seconds)
  for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
      echo "Ollama started (PID: $OLLAMA_PID, log: logs/ollama.log)"
      return 0
    fi
    sleep 1
  done
  
  echo "Warning: Ollama failed to start - LLM features may not work"
  return 1
}

# Ensure log directory exists
mkdir -p "$WC3_DIR/logs"
start_celery
ensure_ollama

# Stop celery on script exit
trap stop_celery EXIT

while true; do
  free_port_8000
  print_prime_startup_info
  set +e
  "$PY_BIN" manage.py runserver
  EXIT_CODE=$?
  set -e

  if [ -f "$RESTART_REQUEST_FILE" ]; then
    rm -f "$RESTART_REQUEST_FILE"
    echo "Restart requested by DB switch. Relaunching runserver..."
    sleep 1
    continue
  fi

  if [ "$EXIT_CODE" = "130" ] || [ "$EXIT_CODE" = "0" ]; then
    echo "Runserver stopped. Exiting loop."
    exit 0
  fi

  echo "Runserver exited with code $EXIT_CODE. Not auto-restarting."
  exit "$EXIT_CODE"
done
