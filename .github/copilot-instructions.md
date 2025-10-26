# Copilot Instructions for AI Coding Agents

## Project snapshot
- Django 5 backend (settings module: `webclerk3_api.settings`). Apps live in `apps/`; shared utilities in `common/`.
- Celery configured in `celery_app.py`; tasks are colocated with their app code (`app/tasks.py`).
- Domain docs: `readmes/` (start with `dev-setup.md`, `reset.md`, `architecture-actions-documents.md`).

## Local workflows
- Use the venv shims: `./bin/python manage.py ...`, `./bin/pip ...`.
- Run API locally: `./run.sh` (applies migrations then `runserver 0.0.0.0:8000`).
- OpenAPI schema: `./schema.sh` (drf-spectacular → `openapi.yaml` then syncs `openapi.json`).
- Common manage tasks: `makemigrations <app>`, `migrate`, `loaddata`, custom commands under `common/management/commands/`.

## Data reset & seeding (canonical)
- Entrypoint: `apps/core/fixtures/seed.seed_all`.
- CLI: `./bin/python manage.py reseed --full [--per-model 5] [--superusers N | --email you@x.com ...]`.
- Programmatic: `from apps.core.fixtures.seed import seed_all; seed_all(flush=True, migrate=True)`.
- Flow: ensures superusers → runs registered seeders (`@register_seeder("app.Model")`) → generic auto-seed to reach `per_model` rows. Optional hooks: `apps/core/fixtures/relationships.seed_relationships`, `apps/core/fixtures/connections.seed_default_connections`.
- Safety: can target remote DBs when `DEBUG=True` — double‑check host before running.

## WCAPI (centralized CRUD/query)
- URLs centralized in `apps/core/wcapi/urls.py`.
  - Patterns: `/wcapi/<model>/_query`, `/wcapi/<model>/_query/save`, `/wcapi/<model>/_sets[/<ident>]`, catch‑alls `/wcapi/<model>[/<extra>]`.
- Lint/compliance: `./bin/python manage.py wcapi_lint [--json]`. Exemptions must include owner+reason comments above path (see `apps/core/wcapi/README.md`).
- Optional guards (middleware):
  - `common.middleware.WCAPISearchGuardMiddleware` (enforce staff‑only `?q=` when `WCAPI_Q_GUARD_ENABLED=True`).
  - `common.middleware.WriteGateMiddleware` (allowlist writes; bypassed in pytest).

## Schema generation
- drf‑spectacular with whitelist filters:
  - `common/schema.py` (`WhitelistAutoSchema`) and `common/schema_hooks.py` (`whitelist_preprocessor`) honor regex patterns in `common/schema_whitelist.py`.
  - Only endpoints matching the whitelist appear in `openapi.(yaml|json)`.

## Testing
- Pytest config in `pytest.ini` (DJANGO_SETTINGS_MODULE=`webclerk3_api.settings`, testpaths: `apps/` and `tests/`).
- Run: `./bin/python -m pytest`. Markers used in repo include `smoke`, `fast` (see `tests/test_smoke_core.py`).

## Conventions & gotchas
- Canonical model_name: singular snake_case (e.g., `sales_order_line`). Inputs may be plural, kebab, or CamelCase; the registry normalizes to canonical (see `apps/core/constants/model_registry.py`).
- All first‑class tables inherit `common.BaseModel`, which provides JSON envelopes: `.metadata`, `.refs`, `.prefs` (plus `.comments`, `.actions`), versioning, and atomic JSON helpers.
- Share cross‑app code in `common/` (mixins: `link_mixins.py`, `search_mixins.py`, `stats_mixin.py`, etc.) to avoid cycles.
- Keep docs/registries in sync when changing schema: update `docs_index.json` and any `readmes/model-registry.*` files.
- Celery workers should use the same settings as Django. If tasks fail to load settings, ensure `DJANGO_SETTINGS_MODULE=webclerk3_api.settings` for workers (adjust `celery_app.py`/env accordingly).

## Quick diagnostics
- List registered seeders: `./bin/python manage.py shell -c "import django; django.setup(); from apps.core.fixtures import get_seeders; print(list(get_seeders().keys()))"`.
- Count sanity (example): `from apps.products.models import Item; print(Item.objects.count())`.
- WCAPI URL resolve (no deps): `./bin/python manage.py shell -c 'from django.urls import resolve; print(resolve("/wcapi/contact/_query/save"))'`.