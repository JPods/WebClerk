#!/bin/bash
set -e

WC3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESTART_REQUEST_FILE="$WC3_DIR/tools/.restart_django"
ENV_FILE="$WC3_DIR/.env"
DEV_CONFIG_FILE="$WC3_DIR/tools/dev-config.json"

cd "$WC3_DIR"

PY_BIN="$WC3_DIR/bin/python"
if [ ! -x "$PY_BIN" ]; then
  PY_BIN="python"
fi

echo "Starting Django with same-terminal auto-restart loop"
echo "Use this command for dev: ./runserver.sh [local]"

# Accept optional argument: ./runserver.sh local
INITIAL_DB_MODE="${1:-remote}"
if [[ "$INITIAL_DB_MODE" != "local" && "$INITIAL_DB_MODE" != "remote" ]]; then
  echo "Usage: ./runserver.sh [local|remote]  (default: remote)"
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

# Ensure log directory exists
mkdir -p "$WC3_DIR/logs"
start_celery

# Stop celery on script exit
trap stop_celery EXIT

while true; do
  free_port_8000
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
