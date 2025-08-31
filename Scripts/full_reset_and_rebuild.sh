#!/usr/bin/env bash
# Full destructive reset: drop DB schema, remove ALL app migrations, recreate, migrate, rebuild demo data.
# Intended for LOCAL DEVELOPMENT only. Do NOT run on shared/staging/prod.
# Adds to earlier reset_dev.sh but covers all domain apps and triggers rebuild_demo_data.
#
# Safety:
#  - Requires interactive confirmation unless -y provided.
#  - If DEBUG env var is not '1' (or True) then requires FORCE_FULL_RESET=1.
#  - Refuses to run if DJANGO_SETTINGS_MODULE looks like a production settings module (contains 'prod').
#
# Usage:
#   ./scripts/full_reset_and_rebuild.sh          # interactive confirm
#   ./scripts/full_reset_and_rebuild.sh -y       # auto-confirm
#   FORCE_FULL_RESET=1 DEBUG=0 ./scripts/full_reset_and_rebuild.sh -y   # explicit override outside DEBUG

set -euo pipefail

AUTO_CONFIRM=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      AUTO_CONFIRM=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2; exit 2
      ;;
  esac
done

DB_NAME=${DATABASE_NAME:-commerce_expert}
DB_USER=${DATABASE_USER:-$USER}
DB_HOST=${DATABASE_HOST:-localhost}
DB_PORT=${DATABASE_PORT:-5432}

# All apps containing models (add/remove as needed)
APPS=(core communications accounts docs orgs transactions products support sync)

confirm() {
  if [[ "$AUTO_CONFIRM" == true ]]; then
    echo "Auto-confirm enabled (-y)."; return 0
  fi
  read -p "This will ERASE ALL DATA for database '$DB_NAME' on $DB_HOST and reset migrations for: ${APPS[*]}. Continue? (y/N) " yn || true
  if [[ ${yn:-N} != "y" ]]; then
    echo "Aborted"; exit 1
  fi
}

safety_guard() {
  local ds_mod=${DJANGO_SETTINGS_MODULE:-}
  if [[ "$ds_mod" == *prod* ]]; then
    echo "Refusing to run: DJANGO_SETTINGS_MODULE suggests production ('$ds_mod')." >&2
    exit 3
  fi
  local debug=${DEBUG:-1}
  if [[ "$debug" != "1" && "$debug" != "true" && -z "${FORCE_FULL_RESET:-}" ]]; then
    echo "DEBUG is not enabled (DEBUG=$debug). Set FORCE_FULL_RESET=1 to proceed." >&2
    exit 4
  fi
  if [[ -n "${CI:-}" ]]; then
    echo "Running under CI environment: forcing non-interactive confirmation.";
    AUTO_CONFIRM=true
  fi
}

terminate_connections() {
  echo "Terminating active connections..."
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid<>pg_backend_pid();" || true
}

drop_and_create_db() {
  echo "Dropping and creating database $DB_NAME..."
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"${DB_NAME}\";" || true
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"${DB_NAME}\";"
}

clean_migrations() {
  echo "Removing migration files..."
  for app in "${APPS[@]}"; do
    MIG_DIR="apps/${app}/migrations"
    if [[ -d "$MIG_DIR" ]]; then
      find "$MIG_DIR" -maxdepth 1 -type f -name "[0-9]*_*.py" -delete
      rm -f "$MIG_DIR"/*.pyc || true
    fi
  done
}

make_migrations() {
  echo "Generating fresh migrations..."
  ./bin/python manage.py makemigrations
}

apply_migrations() {
  echo "Applying migrations..."
  ./bin/python manage.py migrate
}

create_superuser() {
  echo "Creating superuser (skip if exists)..."
  ./bin/python manage.py createsuperuser || true
}

rebuild_demo() {
  echo "Rebuilding demo data..."
  ./bin/python manage.py rebuild_demo_data --export-after || true
}

main() {
  safety_guard
  confirm
  terminate_connections
  drop_and_create_db
  clean_migrations
  make_migrations
  apply_migrations
  create_superuser
  ./bin/python manage.py load_default_company || true
  ./bin/python manage.py load_default_access || true
  rebuild_demo
  echo "Full reset complete."
}

main "$@"
