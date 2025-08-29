#!/usr/bin/env bash
# source bin/activate
# bash reset_dev.sh
# Destructive dev reset: drops DB, removes local app migrations, recreates schema.
# USE ONLY IN DEV. All data will be lost.

set -euo pipefail

DB_NAME="commerce_expert"
# Adjust to one valid local role
DB_USER="williamjames"

APPS=(core communications accounts docs)

read -p "This will DROP database '$DB_NAME' and delete migrations in ${APPS[*]}. Continue? (y/N) " yn
if [[ ${yn:-N} != "y" ]]; then
  echo "Aborted"; exit 1
fi

echo "Dropping database (if exists)..."
psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid<>pg_backend_pid();" || true
psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
psql -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"

for app in "${APPS[@]}"; do
  MIG_DIR="apps/${app}/migrations"
  if [[ -d "$MIG_DIR" ]]; then
    echo "Cleaning migrations in $MIG_DIR"
    find "$MIG_DIR" -maxdepth 1 -type f -name "[0-9]*_*.py" -delete
    rm -f "$MIG_DIR"/*.pyc || true
  fi
done

echo "Making fresh migrations..."
python manage.py makemigrations

echo "Applying migrations..."
python manage.py migrate

echo "Creating superuser (you may be prompted)..."
python manage.py createsuperuser || true

echo "Seeding settings (view/edit permissions)..."
python manage.py view_edit_to_settings || true

echo "Done. You can now run: python manage.py runserver"
