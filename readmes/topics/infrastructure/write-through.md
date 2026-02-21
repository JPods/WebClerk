# Write-Through Proxy

Date: 2026-02-18
Status: Implemented
Owner: Bill

---

## What It Does

When `DB_MODE=write-through`, the local PostgreSQL database serves all **reads**
while **saves** are forwarded to the remote PostgreSQL database via Django's
multi-database ORM. The remote's response (the "bundle") is stored back in the
local database so both copies stay current — no separate sync step required.

```
Browser ──POST /wcapi/save/──▶ Local Django
                                  │
                                  ├─ reads:  local Postgres (default)
                                  └─ saves:  remote Postgres (_wt_remote)
                                               │
                                               ▼
                                        CoreModel.save()
                                        assigns id, uuid,
                                        version, dt_modified
                                               │
                                               ▼
                                        Bundle returned
                                        stored in local DB
                                               │
                                               ▼
                                        Response to browser
```

## Why Not HTTP?

The original sketch forwarded saves over HTTP (`requests.post()`).
The actual implementation uses **Django ORM `using=alias`** instead:

| Concern | HTTP forwarding | ORM `using=` (implemented) |
|---|---|---|
| Remote Django must be running | Yes | No — talks to Postgres directly |
| Auth forwarding needed | Yes | No — same DB credentials |
| Latency | HTTP overhead | Direct Postgres wire protocol |
| Proven pattern | New | Same as `sync_model` command |

## Quick Start

### 1. Ensure local Postgres has the schema

```bash
# One-time: if local DB doesn't exist yet
createdb commerce_expert

# Run migrations against local
DB_MODE=local python manage.py migrate
```

### 2. Seed local from remote

```bash
# Download all tables (FK-safe order)
python manage.py sync_model setting  --direction to-local --no-confirm
python manage.py sync_model org      --direction to-local --no-confirm
python manage.py sync_model contact  --direction to-local --no-confirm
python manage.py sync_model item     --direction to-local --no-confirm
python manage.py sync_model warehouse --direction to-local --no-confirm
python manage.py sync_model order    --direction to-local --no-confirm
python manage.py sync_model orderline --direction to-local --no-confirm
python manage.py sync_model invoice  --direction to-local --no-confirm
python manage.py sync_model invoiceline --direction to-local --no-confirm
python manage.py sync_model payment  --direction to-local --no-confirm
```

Or use the helper script at the bottom of this doc.

### 3. Switch to write-through mode

```bash
# .env
DB_MODE=write-through
```

### 4. Start the server

```bash
python manage.py runserver
```

Boot log will show:

```
DATABASE  ▸  WRITE-THROUGH  read=LOCAL@localhost  write=REMOTE@76.13.185.210
```

## Configuration

All settings live in `.env`:

| Variable | Purpose | Default |
|---|---|---|
| `DB_MODE` | `remote` / `local` / `write-through` | `remote` |
| `WRITE_THROUGH_TIMEOUT` | Seconds before remote save fails | `30` |
| `REMOTE_DATABASE_HOST` | Remote Postgres host | `76.13.185.210` |
| `LOCAL_DATABASE_HOST` | Local Postgres host | `localhost` |

Derived settings in `settings.py`:

| Setting | Value when `write-through` |
|---|---|
| `WRITE_THROUGH_ENABLED` | `True` |
| `WRITE_THROUGH_REMOTE_ALIAS` | `'_wt_remote'` |
| `DATABASES['default']` | Local Postgres |
| `DATABASES['_wt_remote']` | Remote Postgres |

## How Save Views Are Wired

All three WCAPI save endpoints are gated by `is_write_through()`:

| View | File | Handles |
|---|---|---|
| `SaveWcapiView` | `apps/core/views/save_view.py` | Generic model saves (Contact, Item, Setting, etc.) |
| `WCAPITransactionSaveView` | `apps/transactions/views/wcapi.py` | Transaction header + lines (Order, Invoice, etc.) |
| `WCAPISaveView` | `apps/transactions/views/wcapi.py` | Simple delegate saves |

When `DB_MODE` is **not** `write-through`, all views behave exactly as before.

## Core Module: `common/write_through.py`

### Public API

```python
is_write_through() → bool
get_remote_alias() → str

forward_and_store(request, model_cls, payload) → (dict, status_code)
forward_transaction_and_store(request, model_key, record_data, lines_data, options) → (dict, status_code)
```

### Single-Record Save Flow (`forward_and_store`)

1. Determine create vs update from `payload['id']`
2. For **update**: `model_cls.objects.using('_wt_remote').get(id=X)` → apply fields → `.save(using='_wt_remote')`
3. For **create**: `model_cls()` → apply fields → `.save(using='_wt_remote')`
4. `refresh_from_db(using='_wt_remote')` to get authoritative `id`, `uuid`, `version`, `dt_modified`
5. `_store_bundle_locally()` mirrors the record in local DB
6. Returns `{'id': ..., 'record': ..., 'write_through': True}`

### Transaction Save Flow (`forward_transaction_and_store`)

1. Temporarily swaps `DATABASES['default']` → remote config
2. Calls `save_transaction_with_lines()` (operates on "default" → remote)
3. Restores original default connection
4. Syncs header + all lines back to local via `_store_bundle_locally()`

### Local Storage Details

- Matches by **uuid first**, falls back to **PK**
- Sets `_sync_in_progress = True` to suppress `post_save` signals
- Calls `models.Model.save()` (not `CoreModel.save()`) to preserve remote's version/timestamps
- Resets PostgreSQL auto-increment sequence after each store

## Error Handling

| Scenario | Response |
|---|---|
| Remote DB unreachable | `502` with `write_through_error: True` |
| Record not found on remote (update) | `404` |
| Remote save raises exception | `502` with error detail |
| Remote save OK but local sync fails | `200` (save succeeded) + warning logged |

## Testing

```bash
pytest tests/test_write_through.py -v
```

Tests use `@override_settings` to toggle `WRITE_THROUGH_ENABLED` and mock
the remote database alias. See the test file for full coverage.

## Switching Back

To return to normal remote-only mode:

```bash
# .env
DB_MODE=remote
```

No code changes needed — the `is_write_through()` gate returns `False`.

## Catch-Up After Offline Work

If you've been working offline (local-only saves) and need to push changes
to remote, or if the local DB has drifted:

```bash
# Re-seed local from remote (overwrites local with remote data)
python manage.py sync_model <model> --direction to-local --no-confirm

# Or sync ALL models:
./sync_all.sh to-local
```

## Helper Script: `sync_all.sh`

```bash
#!/bin/bash
# sync_all.sh — Sync all tables in FK dependency order
DIRECTION=${1:-to-local}

MODELS=(setting org contact item warehouse order orderline invoice invoiceline payment)

for model in "${MODELS[@]}"; do
  echo "▸ Syncing $model ($DIRECTION)..."
  python manage.py sync_model "$model" --direction "$DIRECTION" --no-confirm
done

echo "✓ Done"
```

## Related Documentation

- [database-sync-strategy.md](database-sync-strategy.md) — Full sync strategy and write-through architecture
- [sync-model.md](sync-model.md) — The `sync_model` management command
- [dev-db-strategy.md](dev-db-strategy.md) — SQLite vs Postgres dual-lane approach
- [settings.md](settings.md) — Django settings reference
