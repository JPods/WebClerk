# Management & Operations

## Common Commands

```bash
python manage.py migrate
python manage.py createsuperuser  # or python create_superuser.py
python manage.py shell
python manage.py showmigrations
```

## Squashed Migrations

Historical migrations for `orgs` and `products` were squashed into their `0001_initial` files (2025-09-03). Intermediate product migrations were replaced with no-op stubs to avoid duplicate DDL.

If your local DB predates the squash:

```bash
psql -c 'DROP DATABASE IF EXISTS commerce_expert;' -d postgres
psql -c 'CREATE DATABASE commerce_expert;' -d postgres
python manage.py migrate
```

## Adding New Migrations

```bash
python manage.py makemigrations <app>
python manage.py migrate
```

Commit each generated migration; do not hand-edit unless applying a deliberate squash.

## Data Scripts

`local/demo_data.py` contains optional seed helpers (review before use). Run inside Django shell if needed.

## Health Checks

- Run tests: `pytest -q`
- Lint / style can be integrated later (currently minimal).
