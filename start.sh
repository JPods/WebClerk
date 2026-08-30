#!/bin/bash
# WebClerk launcher — starts backend (Django + Celery) and frontend (Vite)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"
LOG_DIR="$DATA_DIR/logs"
mkdir -p "$LOG_DIR"

# Track child PIDs for cleanup
PIDS=()

cleanup() {
  echo ""
  echo "Shutting down WebClerk..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # Clean up Celery processes
  pkill -f "celery -A webclerk3_api" 2>/dev/null || true
  wait 2>/dev/null
  echo "Stopped."
}

trap cleanup EXIT INT TERM

echo "========================================"
echo "  WebClerk"
echo "========================================"

# ── Preflight checks ─────────────────────────────────────────────

if [ ! -d "$BACKEND_DIR/venv" ]; then
  echo "ERROR: Backend not installed. Run ./install.sh first."
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "ERROR: Frontend not installed. Run ./install.sh first."
  exit 1
fi

# ── Free port 8000 if occupied ────────────────────────────────────

OLD_PIDS=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
  echo "Port 8000 in use — stopping existing process"
  echo "$OLD_PIDS" | xargs kill -TERM 2>/dev/null || true
  sleep 1
fi

# ── Start Ollama (if installed) ───────────────────────────────────

if command -v ollama &>/dev/null; then
  if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama:    running"
  else
    ollama serve >> "$LOG_DIR/ollama.log" 2>&1 &
    PIDS+=($!)
    echo "Ollama:    started (log: data/logs/ollama.log)"
  fi
else
  echo "Ollama:    not installed (AI features disabled)"
fi

# ── Start Celery ──────────────────────────────────────────────────

pkill -f "celery -A webclerk3_api" 2>/dev/null || true
sleep 1

cd "$BACKEND_DIR"
venv/bin/python -m celery -A webclerk3_api worker \
  -l info \
  --concurrency=2 \
  -P solo \
  --without-heartbeat \
  -B \
  -s /tmp/celerybeat-webclerk3-schedule \
  >> "$LOG_DIR/celery.log" 2>&1 &
PIDS+=($!)
echo "Celery:    started (log: data/logs/celery.log)"

# ── Start Django ──────────────────────────────────────────────────

cd "$BACKEND_DIR"
venv/bin/python manage.py runserver 2>&1 &
PIDS+=($!)
echo "Django:    http://localhost:8000"

# ── Start Vite ────────────────────────────────────────────────────

cd "$FRONTEND_DIR"
npm run dev 2>&1 &
PIDS+=($!)
echo "Vite:      http://localhost:5173"

echo ""
echo "  Press Ctrl+C to stop all services"
echo "========================================"

# Wait for any child to exit
wait
