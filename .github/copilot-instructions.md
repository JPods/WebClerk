# Copilot Instructions for AI Coding Agents

## Project Snapshot
- Django 5 backend (settings: `webclerk3_api/`), apps under `apps/`, shared tooling in `common/`.
- Celery app at `celery_app.py`; tasks live alongside their app code.
- Domain docs live in `readmes/` (start with `dev-setup.md`, `reset.md`, `architecture-actions-documents.md`).

## Local Environment
- Use the venv shims: `./bin/python manage.py ...` and `./bin/pip ...`.
- Run API/Celery via `./run.sh`. Rebuild OpenAPI schema via `./schema.sh`.

## Database Reset & Seeding (canonical)
- Single entry point: `apps/core/fixtures/seed.seed_all`.
- Management command:
  - Full destructive reseed (flush + migrate): `./bin/python manage.py reseed --full`
  - Tune volume: `--per-model 5` (default 5)
  - Superusers: 3 patterned by default (`1@1.com`, `2@2.com`, `3@3.com`); override with `--superusers N` or repeated `--email`.
- Programmatic:
  - `from apps.core.fixtures.seed import seed_all; seed_all(flush=True, migrate=True)`
- How it works:
  - Ensures superusers, runs any registered seeders (`@register_seeder("app.Model")`), then auto-seeds remaining models generically to reach `per_model` rows.
  - Optional hooks called if present: `apps/core/fixtures/relationships.seed_relationships`, `apps/core/fixtures/connections.seed_default_connections`.
- Files:
  - Seeding engine: `apps/core/fixtures/seed.py`
  - Command: `common/management/commands/reseed.py`
  - Seeder registry: `apps/core/fixtures/__init__.py`
  - Docs: `readmes/reset.md`
- Safety:
  - Reseed can target remote DBs (e.g., host `85.31.234.194`) when `DEBUG=True`. Be deliberate when running against non-local hosts.

## Adding/Adjusting Seed Data
- Prefer explicit seeders for models with strict FKs or domain rules:
  - Example:
    - `@register_seeder("products.Item")`
    - Return a list of created IDs; receive `per` and a context dict with `{"superusers": [...]}`.
- Otherwise the generic auto-seeder creates simple, deterministic values for Char/JSON/Date/UUID/etc., and best-effort M2M attachments.

## Testing & QA
- Pytest configured by `pytest.ini`: `./bin/python -m pytest`
- Smoke example: `tests/test_smoke_core.py` (creates a `products.Item` and asserts defaults).

## Conventions
- Cross-app commands go in `common/management/commands/`; app-specific go under each app’s `management/commands/`.
- Keep shared mixins/utilities in `common/` to avoid circular imports.
- Update related docs/registries (`readmes/model-registry.*`, `docs_index.json`) when changing schema.

## Quick Diagnostics
- Show discovered seeders: `./bin/python manage.py shell -c "import django; django.setup(); from apps.core.fixtures import get_seeders; print(list(get_seeders().keys()))"`
- Sanity check counts, e.g.: `from apps.products.models import Item; print(Item.objects.count())`