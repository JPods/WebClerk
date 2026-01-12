# Schema Whitelist Guide

This project uses a strict whitelist to control which API endpoints appear in the generated OpenAPI spec (and, by convention, which ones are considered stable for frontend use).

- File: `common/schema_whitelist.py`
- Setting: `SPECTACULAR_SETTINGS['PREPROCESSING_HOOKS']` includes the whitelist preprocessor
- Canonical spec: `openapi.yaml` (sync to `openapi.json` via `tools/openapi_sync.py`)

## Principles

- Be explicit: only endpoints listed in the whitelist appear in the spec.
- Keep it tight: add endpoints one at a time when they’re truly ready.
- Consistency over backwards-compat: prefer canonical parameter names (`model_name`, `app_name`, `field_name`).

## How to add an endpoint

1. Identify the path and method.
2. Add an anchored regex pattern to `WHITELIST` in `common/schema_whitelist.py`.
   - Example patterns (commented in the file):
     - GET  /api/ping/            → `r'^/api/ping/$'`
     - POST /api/items/           → `r'^/api/items/$'`
     - GET  /api/items/42/        → `r'^/api/items/\\d+/$'`
3. Regenerate the schema and sync JSON.

### Regenerate and sync

Fast path (preferred):

```bash
./schema.sh
```

Manual path:

```bash
# optional: activate venv
source bin/activate
python manage.py spectacular --file openapi.yaml
python tools/openapi_sync.py
```

You should see `Wrote openapi.yaml and openapi.json` followed by a confirmation message.

## Current whitelisted endpoints (annotated)

- POST /api/auth/login/
- GET  /wcapi/get/
- POST /wcapi/save/
- GET  /wcapi/models/
- GET  /api/model-fields/
- GET  /wcapi/model_name/list/
- GET  /wcapi/model_name/detail/

These map one-to-one with the entries and comments in `common/schema_whitelist.py`.

## Tips

- Prefer canonical param names everywhere (`model_name`, `app_name`, `field_name`, `related_model_names`).
- When adding a new endpoint, also annotate it with `@extend_schema` for clear request/response examples.
- If an endpoint should not be publicly discoverable yet, keep it out of the whitelist (and optionally comment it out in `apps/core/urls.py`).
