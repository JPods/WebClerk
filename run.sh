#!/bin/zsh
# Unified developer helper: optional full reset (drop DB), migrate, seed, create 3 superusers, run server.
# Usage examples:
#   ./run.sh                       # just migrate + runserver (prompts about reset)
#   ./run.sh --full                # full destructive reset + seed + superusers, then runserver
#   ./run.sh --full --no-server    # full reset & seed only
#   ./run.sh --full --python "-OO" # pass extra python flags (example) – not typical
#   ./run.sh --full --addr 0.0.0.0:9000  # run on custom host:port
#   ./run.sh --full --no-seed      # reset without seed commands

set -euo pipefail

# ---------------- Configuration (env overridable) ----------------
DB_NAME=${DATABASE_NAME:-commerce_expert}
DB_USER=${DATABASE_USER:-$(whoami)}
DB_HOST=${DATABASE_HOST:-localhost}
DB_PORT=${DATABASE_PORT:-5432}
ADDR="127.0.0.1:8000"
PYTHON_FLAGS=""
RUN_SERVER=1
DO_FULL=0
SEED=1
QUIET_PROMPT=0

SEED_COMMANDS=(
  load_default_company
  load_default_access
  seed_orgs
  seed_documents
  seed_projects
  seed_transactions
)

# ---------------- Helpers ----------------
log() { printf "\033[1;34m[run]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[err]\033[0m %s\n" "$*" >&2; }

run() {
  local msg=$1; shift
  log "$msg"
  if ! "$@"; then
    err "FAILED: $msg"
    return 1
  fi
}

create_three_superusers() {
  log "Creating 3 superusers (pattern first_i / last_i / i@i.com)..."
  for i in 1 2 3; do
    python ${PYTHON_FLAGS} create_superuser.py \
      --email "${i}@${i}.com" \
      --password 1111pass \
      --first-name "first_${i}" \
      --last-name "last_${i}" || warn "superuser $i creation issue (continuing)"
  done
}

seed_data() {
  [[ $SEED -eq 1 ]] || { warn "Seeding skipped (--no-seed)"; return 0; }
  for cmd in "${SEED_COMMANDS[@]}"; do
    log "Seeding via: $cmd"
    python ${PYTHON_FLAGS} manage.py "$cmd" || warn "Seed command $cmd failed (non-fatal)"
  done
  # Light synthetic fill for any remaining models
  python ${PYTHON_FLAGS} manage.py reseed_all_models --no-flush --per-model 2 || warn "reseed_all_models partial/failed"
}

full_reset() {
  log "Starting FULL RESET of database $DB_NAME"
  if ! command -v psql >/dev/null 2>&1; then
    err "psql not found in PATH"; return 1
  fi
  # Terminate sessions, drop, create
  run "Terminate active connections" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();"
  run "Drop database" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
  run "Create database" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"
  # Apply migrations (assuming already committed baseline migrations)
  run "Apply migrations" python ${PYTHON_FLAGS} manage.py migrate --noinput
  seed_data
  create_three_superusers
  log "FULL RESET complete"
}

activate_venv() {
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    log "Virtualenv already active: $VIRTUAL_ENV"
  elif [[ -f ./bin/activate ]]; then
    # shellcheck disable=SC1091
    source ./bin/activate
    log "Virtualenv activated"
  else
    warn "./bin/activate not found; proceeding with current python"
  fi
}

# ---------------- Arg Parsing ----------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full|-F) DO_FULL=1; QUIET_PROMPT=1; shift ;;
    --addr) ADDR=$2; shift 2 ;;
    --python) PYTHON_FLAGS=$2; shift 2 ;;
    --no-server) RUN_SERVER=0; shift ;;
    --no-seed) SEED=0; shift ;;
    --yes|-y) QUIET_PROMPT=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: ./run.sh [--full] [--no-server] [--no-seed] [--addr host:port] [--python "flags"] [--yes]
  --full / -F   Drop & recreate DB, migrate, seed, create 3 superusers
  --no-server   Do not start Django dev server afterward
  --no-seed     Skip seed commands (still creates superusers if --full)
  --addr        Host:port for runserver (default 127.0.0.1:8000)
  --python      Extra python flags (e.g. "-X faulthandler")
  --yes         Auto-confirm destructive reset prompt
EOF
      exit 0 ;;
    *) warn "Unknown arg $1 (ignored)"; shift ;;
  esac
done

# ---------------- Preconditions ----------------
[[ -f manage.py ]] || { err "manage.py not found (run from project root)"; exit 1; }
activate_venv

if [[ $DO_FULL -eq 1 && $QUIET_PROMPT -eq 0 ]]; then
  read -r "REPLY?This will DROP database '$DB_NAME'. Continue? (y/N) "
  [[ $REPLY == 'y' || $REPLY == 'Y' ]] || { err "Aborted"; exit 1; }
fi

if [[ $DO_FULL -eq 1 ]]; then
  full_reset
else
  log "Standard path: migrate only"
  run "Apply migrations" python ${PYTHON_FLAGS} manage.py migrate --noinput
fi

if [[ $RUN_SERVER -eq 1 ]]; then
  log "Starting dev server at $ADDR"
  exec python ${PYTHON_FLAGS} manage.py runserver "$ADDR"
else
  log "Done (server suppressed)"
fi
