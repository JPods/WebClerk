# Development & Debug Configuration Overview

Purpose: Central reference for the temporary / development-only switches, shortcuts, and architectural choices currently active in this codebase so they are visible, intentional, and easy to revert.

---

## 1. Core Environment Flags

| Flag | Current Intent | Effect | How to Disable |
|------|----------------|--------|----------------|
| `VIEW_EDIT_DEV_BYPASS=1` | ENABLED during active UI/API build | Field-level access control bypassed; all model concrete fields exposed; edit filtering relaxed | Unset or set to `0` then restart server |
| `WCAPI_OPEN_READ=1` | ENABLED for frictionless GET tests | Allows unauthenticated GET to `/wcapi/get` & related read endpoints (role treated as PUBLIC) | Unset or set to `0` (then only authenticated users can read) |
| `WCAPI_JWT_ONLY=0` | DISABLED (default) | Session auth OR JWT accepted (plus open read if enabled) | Set to `1` to *require* Bearer tokens (even if session cookie exists) |

Notes:

- If both `WCAPI_OPEN_READ=1` and `WCAPI_JWT_ONLY=1`, the JWT requirement wins for authenticated contexts; unauthenticated read still allowed only if `WCAPI_OPEN_READ=1` AND `WCAPI_JWT_ONLY=0`.
- Bypass is evaluated dynamically each request; you can toggle the env var and restart to switch behavior.

---

## 2. Field Access & Bypass Mechanics

Module: `apps/core/services/view_edit_access.py`

Behavior:

- Normal mode: For each `(table, role, access_type)` we look up an active `Setting` with `purpose="view_edit"` and filter fields to those listed.
- Dev bypass mode: `get_view_edit_fields` returns `['*']` (wildcard). `filter_record_for_role` expands `*` to full concrete model fields (excluding M2M) and merges any existing dict keys.
- Fail-open safety: If allowed list is empty or missing, we still return full record in development to avoid silent `{}` responses.
- Logging: Missing Setting messages were converted from `print` spam to a one-time `DEBUG` log keyed by `(table, role, access_type)`.

Rationale: Speed up UI prototyping before curating per-role matrices.

To restore strict mode: unset `VIEW_EDIT_DEV_BYPASS`, create the required `Setting` rows, and (optionally) raise log level to surface missing configs.

---

## 3. Authentication Endpoints

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `POST /wcapi/login/` | JWT login (alias of `/api/auth/login/`) | Returns access/refresh & user claims |
| `POST /wcapi/signup/` | User registration + tokens | Development convenience |
| `POST /api/token/refresh/` | Refresh JWT | Standard SimpleJWT |
| `GET /login/` | Session (HTML form) | Uses Django sessions |

Decision: Provide `/wcapi/login/` alias to match legacy / expected client path.

---

## 4. Serialization Sanitization

File: `apps/core/views/get_view.py`

- Added `_sanitize()` method to coerce non-JSON-safe values (e.g., `Decimal`, `datetime`, model instances) to primitives.
- Prevents 500 errors like `TypeError: Object of type Permission is not JSON serializable` when contacts include related permission objects indirectly.

---

## 5. Data Seeding Strategy (Simplified)

Remaining canonical command: `reseed_all_models`.

Removed (deleted) legacy/demo commands:

- `seed_orgs`, `seed_transactions`, `seed_projects`, `seed_project_links`, `seed_documents`, `rebuild_demo_data`, `seed_minimal_if_empty`.

Why: Single mental model for resetting development data; generate consistent small dataset quickly.

Usage:

```bash
python manage.py reseed_all_models --per-model 3
```

Options: `--no-flush`, `--apps`, `--m2m-max`, `--org-relations`, `--no-relate`.

Relationship pass creates:

- Random M2M links (bounded)
- OrgBase `relations` parents/children/linked_ids population

---

## 6. Stats & Periodic Tasks

Defined in `settings.py` (`CELERY_BEAT_SCHEDULE`):

- `recompute-basic-stats-hourly` – Normalize/repair `stats` blobs.
- `recompute-relationship-counts-2h` – Rebuild lightweight org relation counts.
- `refresh-keywords-30m` – Keywords refresh sweep.

All are low-cost; expiration options prevent backlog execution after downtime.

---

## 7. Removed / Deferred Concepts

| Concept | Status | Replacement / Reason |
|---------|--------|----------------------|
| Verb-style wcapi endpoints (`/wcapi/post`, `/wcapi/delete`) | Removed | Consolidated on `/wcapi/get`, `/wcapi/save`, `/wcapi/query` |
| Multi-command demo rebuild chain | Removed | `reseed_all_models` single entry point |
| Static JSONField defaults (mutable) warnings for `Item.cost`/`Item.price` | Addressed | Now use callable factories (`default_cost`, `default_price`) |

---

## 8. How to Switch to Secure Mode

1. Unset dev flags:

```bash
unset VIEW_EDIT_DEV_BYPASS
unset WCAPI_OPEN_READ
export WCAPI_JWT_ONLY=1
```

1. Restart application.
1. Create appropriate `Setting` rows for each table/role:

```python
# Example (Django shell)
from apps.core.models import Setting
Setting.objects.create(
  table_name='contacts', purpose='view_edit', is_active=True,
  data={'ADMIN': {'view':['id','email','name_first','name_last','role'], 'edit':['name_first','name_last','role']}, 'PUBLIC': {'view':['id','name_first'], 'edit':[]}}
)
```

1. Confirm filtered responses return only whitelisted fields.

---

## 9. Quick Debug Commands

| Goal | Command |
|------|---------|
| Reseed full dataset (flush) | `python manage.py reseed_all_models --per-model 3` |
| Inspect model counts | `python manage.py shell -c "from django.apps import apps;print({m._meta.label: m.objects.count() for m in apps.get_models() if m._meta.app_label in ['core','products','transactions']})"` |
| Test open read | `curl http://localhost:8000/wcapi/get/?table_name=contacts` |
| JWT login | `curl -X POST http://localhost:8000/wcapi/login/ -H 'Content-Type: application/json' -d '{"email":"...","password":"..."}'` |

---

## 10. Future Cleanup Targets

- Remove fail-open behavior once full `Setting` matrices populated.
- Swap `WCAPI_OPEN_READ` for a per-endpoint allowlist or temporary signed token approach.
- Introduce structured audit log for field-level exposure decisions (optional).
- Add a `/wcapi/debug/config` read-only endpoint exposing current effective flags (non-prod only).

---

## 11. Summary of Current Choices

| Area | Choice | Temporary? |
|------|--------|------------|
| Field ACL | Global bypass, wildcard all fields | YES |
| Auth | Mixed session/JWT, open read allowed | YES |
| Data seeding | Single generic reseed command | STAYS |
| Serialization | Sanitize non-JSON values on GET | STAYS |
| Logging | One-time debug for missing Setting | MAY CHANGE |
| Stats recompute | Lightweight Celery beat tasks | STAYS |

---

Maintainers: Keep this file updated whenever a debug flag or development shortcut is added or removed.

---

## Appendix: Fast Dev Reset Workflow

Typical full reset (drop DB + wipe migrations for core app set + reseed minimal data):

```bash
# 1. (Optional) Commit or stash any model code changes first

# 2. Drop DB & remove existing migrations (interactive confirm) - DESTRUCTIVE
bash reset_dev.sh

# 3. (Script already runs makemigrations + migrate + createsuperuser)

# 4. Populate synthetic sample data (if not already populated by other flows)
python manage.py reseed_all_models --per-model 3
```

Lightweight alternative (keep migrations, just nuke data + reseed):

```bash
python manage.py flush --no-input
python manage.py reseed_all_models --per-model 3
```

Notes:

- `reset_dev.sh` expects a local Postgres role (`DB_USER`) and database name; edit the script if your local credentials differ.
- Use `--no-flush` with `reseed_all_models` when you only want to top up sparse tables.
- After a structural model change that invalidates old migrations: prefer `reset_dev.sh` to avoid drift.
