# Copilot Instructions for AI Coding Agents

## Project Snapshot
- **webClerk3** is a Django 5 backend (`webclerk3_api/settings.py`) with domain-specific apps under `apps/` and shared utilities in `common/` and `core/`.
- Service workers live in `celery_app.py`; Celery tasks are declared inside their owning app modules.
- Extensive design docs and runbooks are in `readmes/`; start with `readmes/architecture-actions-documents.md` and `readmes/dev-setup.md`.

## Local Environment
- Always invoke Django via the project venv: `./bin/python manage.py ...` (guards in reset scripts assume this path).
- Default entry points: `./run.sh` boots the API + Celery, `scripts/` holds ad-hoc helpers, and `schema.sh` rebuilds the OpenAPI schema.

## Database Reset & Seeding
- The authoritative seeding API is `apps/core/fixtures/seed.seed_all(per_model=..., superuser_emails=...)`.
- `get_seeders()` / `register_seeder()` in `apps/core/fixtures/__init__.py` expose app-specific seeders; pass context with `{"superusers": [...]}` when invoking.
- Legacy reseed helpers (`apps/core/fixtures/reseed.py`, `common/rebuild/*`, scattered `seed_*` commands) are being collapsed into a single call chain around `seed.seed_all`. Treat them as deprecated and route new code through `seed_all`.
- Dev reset workflows described in `readmes/reset.md`; align new automation with that document (e.g., patterned superusers, connection bootstrap).

## Testing & QA
- Pytest is configured via `pytest.ini`; run `./bin/python -m pytest`.
- API smoke/bulk tests live in `api_tests/` (Postman collections) and `frontend-endpoint-explorer/` for manual exercises.

## Conventions
- Apps follow Django app boundaries listed in `project_structure.txt`; keep shared mixins/utilities inside `common/` to avoid circular imports.
- Docs and fixtures often use CSV/JSON registries (`readmes/model-registry.*`, `apps/*/fixtures/`); update those alongside code changes.
- Keep management commands under `common/management/commands/` for cross-app utilities; app-specific commands stay in each app’s `management/commands/`.

## References
- Architecture and workflow primers: `readmes/dev-db-strategy.md`, `readmes/debug.md`, `readmes/reset.md`.
- Data contracts: `openapi.yaml`/`openapi.json` plus `docs_index.json` for doc search.
- When unsure about domain rules, check the matching `readmes/*.md` file; many flows (transactions, exchanges, verifications) have dedicated guides.