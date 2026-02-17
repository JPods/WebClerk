# sync_model — Copy Model Data Between Local & Remote


<!-- TOC START -->

## Table of Contents

- [sync\_model — Copy Model Data Between Local \& Remote](#sync_model--copy-model-data-between-local--remote)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Quick Start](#quick-start)
  - [How It Works](#how-it-works)
  - [Arguments \& Flags](#arguments--flags)
  - [Environment Variables](#environment-variables)
  - [Examples](#examples)
    - [Pull remote contacts into local](#pull-remote-contacts-into-local)
    - [Push local settings to remote](#push-local-settings-to-remote)
    - [Dry-run to preview without changes](#dry-run-to-preview-without-changes)
    - [List all available models](#list-all-available-models)
    - [Use app.Model format instead of blessed key](#use-appmodel-format-instead-of-blessed-key)
    - [Skip confirmation prompt (scripts / CI)](#skip-confirmation-prompt-scripts--ci)
  - [FK Constraints](#fk-constraints)
  - [Sequence Reset](#sequence-reset)
  - [Audit Log](#audit-log)
  - [Typical Workflows](#typical-workflows)
    - [Refresh local dev data from remote](#refresh-local-dev-data-from-remote)
    - [Seed a single table after schema change](#seed-a-single-table-after-schema-change)
  - [Caveats](#caveats)
  - [Related Documentation](#related-documentation)

## FK Conflict Handling & Update-on-Match

Starting February 2026, sync_model detects and logs foreign key conflicts during insert. If a row fails to insert due to FK constraint:

- If a row with the same PK (id or uuid) already exists in the target, and the UUID matches, the existing row is updated with new data (all fields except PK/UUID).
- If PK/UUID do not match, the row is logged as a true conflict for manual review.
- If --conflict new is used and PK matches but UUID does not, a new record is created at the destination (with a new PK).
- The audit log records both the number of updated rows and any FK conflicts as a JSON blob in the error field.

### Example Audit Log (with updates and conflicts)

```
[2026-02-15 21:42:07 UTC] user=williamjames@MacBookPro model=core.Contact table=core_contact direction=REMOTE→LOCAL src=REMOTE@76.13.185.210(15) tgt=LOCAL@localhost(15) rows_synced=12 elapsed=1.2s dry_run=False status=OK cmd="manage.py sync_model contact --direction to-local --no-confirm --conflict new" error="{'fk_conflicts': [...], 'updated': 3, 'inserted': 9}"
```

- `updated`: Number of rows updated due to PK/UUID match.
- `inserted`: Number of new rows created (including --conflict new cases).
- `fk_conflicts`: List of rows that could not be inserted or updated, including PK, field values, and error reason.

This ensures that data is updated when possible, new records are created for conflicts (if requested), and only true conflicts are flagged for manual review.

<!-- TOC END -->

Date: 2026-02-15
Status: Implemented
Owner: Bill


## Overview

`sync_model` is a Django management command that copies all rows for a
single model from one PostgreSQL database to another. It connects to
**both** the local and remote databases simultaneously (regardless of
`DB_MODE`) and transfers data via Django's serialization framework.

**Location:** `apps/core/management/commands/sync_model.py`

The command is intentionally simple and single-model — it updates or inserts rows in the target table, preserving existing records. For full-database restores, use `restore_data_smart` instead.

Every invocation is logged to `logs/sync_model.log` with timestamp,
user, hostname, model, direction, row counts, and the full command.


## Quick Start

```bash
# Activate the virtual environment
cd webClerk3 && source bin/activate

# Pull all contacts from remote → local
python manage.py sync_model contact --direction to-local

# Push local settings → remote
python manage.py sync_model setting --direction to-remote

# Preview what would happen (no data touched)
python manage.py sync_model item --direction to-local --dry-run

# See all available model names
python manage.py sync_model --list
```


## How It Works

```
  Source DB                              Target DB
  ─────────                              ─────────
  ┌──────────┐   1. serialize (JSON)     ┌──────────┐
  │  table    │ ──────────────────────►   │  table   │
  │  N rows   │                          │  M rows  │
  └──────────┘                           └──────────┘
                 2. update/insert rows
                 3. disable FK triggers
                 4. reset PK sequence    ┌──────────┐
                                         │  table   │
                                         │  N+M rows│
                                         └──────────┘
```

1. **Serialize** — Read all rows from the source via Django ORM
   (`model.objects.using(src).all()`) and serialize to JSON.
2. **Update/Insert** — For each row, update existing records if PK/UUID match, insert new records otherwise. If --conflict new is used, create new records for PK matches with UUID mismatch.
3. **Disable triggers** — `ALTER TABLE ... DISABLE TRIGGER ALL` on the
target so FK constraints don't block inserts when referenced tables
are out of sync.
4. **Reset sequence** — Calls `setval(pg_get_serial_sequence(...))` to
   set the auto-increment to `MAX(id) + 1`. Skipped silently for UUID
   primary keys.


## Arguments & Flags

| Argument | Required | Description |
|---|---|---|
| `model_name` | Yes (unless `--list`) | WCAPI blessed key (`contact`, `item`, `order`) or `app.Model` format (`core.Contact`, `products.Item`) |
| `--direction` | Yes | `to-local` (remote → local) or `to-remote` (local → remote) |
| `--dry-run` | No | Show row counts and plan without modifying any data |
| `--list` | No | Print all available model names with their tables and exit |
| `--no-confirm` | No | Skip the interactive "Type 'yes' to proceed" prompt |
| `--conflict` | No | Conflict resolution: `record` (default, update existing), `new` (create new record for PK matches with UUID mismatch) |


## Environment Variables

The command reads connection parameters from the `.env` file via
`decouple.config()`. It always connects to **both** databases
regardless of the current `DB_MODE` setting.

| Variable | Default | Used for |
|---|---|---|
| `LOCAL_DATABASE_NAME` | `commerce_expert` | Local DB name |
| `LOCAL_DATABASE_USER` | `williamjames` | Local DB user |
| `LOCAL_DATABASE_PASS` | *(empty)* | Local DB password |
| `LOCAL_DATABASE_HOST` | `localhost` | Local DB host |
| `LOCAL_DATABASE_PORT` | `5432` | Local DB port |
| `REMOTE_DATABASE_NAME` | `commerce_expert` | Remote DB name |
| `REMOTE_DATABASE_USER` | `postgres` | Remote DB user |
| `REMOTE_DATABASE_PASS` | *(from .env)* | Remote DB password |
| `REMOTE_DATABASE_HOST` | `localhost` | Remote DB host |
| `REMOTE_DATABASE_PORT` | `5432` | Remote DB port |

The command registers temporary Django database aliases (`_sync_local`
and `_sync_remote`) during execution and cleans them up on exit.


## Examples

### Pull remote contacts into local

```bash
python manage.py sync_model contact --direction to-local
```

Output:
```
  sync_model: core.Contact
  Table:       contacts
  Source:      REMOTE @ 76.13.185.210  (15 rows)
  Target:      LOCAL @ localhost  (2 rows)
  Direction:   REMOTE → LOCAL

  This will update existing rows in LOCAL.contacts and insert new rows from REMOTE.

  Type 'yes' to proceed: yes
  [1/4] Reading 15 rows from REMOTE... 15 serialized
  [2/4] Syncing 15 rows into LOCAL... done
  [3/4] Resetting PK sequence... done

  ✓ core.Contact: 15 rows synced REMOTE → LOCAL in 24.4s
```

### Push local settings to remote

```bash
python manage.py sync_model setting --direction to-remote
```

### Push with conflict resolution (create new records for PK matches with UUID mismatch)

```bash
python manage.py sync_model action --direction to-remote --conflict new
```

### Dry-run to preview without changes

```bash
python manage.py sync_model item --direction to-local --dry-run
```

Output:
```
  sync_model: products.Item
  Table:       products_item
  Source:      REMOTE @ 76.13.185.210  (1,247 rows)
  Target:      LOCAL @ localhost  (0 rows)
  Direction:   REMOTE → LOCAL

  Dry run — no changes made.
```

### List all available models

```bash
python manage.py sync_model --list
```

Shows all 64+ models from `WCAPI_BLESSED_MODELS` with their
`app.Model` path and database table name.

### Use app.Model format instead of blessed key

```bash
python manage.py sync_model core.Action --direction to-local
```

### Skip confirmation prompt (scripts / CI)

```bash
python manage.py sync_model contact --direction to-local --no-confirm
```


## FK Constraints

The command **disables all triggers** on the target table during
insertion. This is necessary because:

- Tables are synced one at a time, not in FK dependency order.
- The target may not yet have the referenced rows in related tables
  (e.g., syncing `contacts` before `orgs_orgbase`).

Triggers are always re-enabled in a `finally` block after the insert
completes or fails. This means FK constraints are **not validated**
during the sync — the data is trusted to be referentially consistent
on the source.

**If you need referential integrity on the target**, sync the
referenced (parent) tables first:

```bash
# Sync parent tables first
python manage.py sync_model org --direction to-local --no-confirm
python manage.py sync_model contact --direction to-local --no-confirm
python manage.py sync_model item --direction to-local --no-confirm

# Then sync child tables
python manage.py sync_model order --direction to-local --no-confirm
python manage.py sync_model invoice --direction to-local --no-confirm
```


## Sequence Reset

After inserting rows, the command resets the PostgreSQL auto-increment
sequence to `MAX(pk) + 1`. This prevents "duplicate key" errors when
creating new records on the target after the sync.

For models with UUID primary keys (no serial sequence), the reset is
skipped silently.


## Audit Log

Every invocation is appended to **`logs/sync_model.log`** as a
single-line structured record. The log file is created automatically
on first use.

### Log Fields

| Field | Example | Description |
|---|---|---|
| `timestamp` | `2026-02-15 21:38:38 UTC` | When the command ran (UTC) |
| `user` | `williamjames@MacBookPro` | OS username + hostname |
| `model` | `core.Contact` | Resolved `app_label.Model` |
| `table` | `core_contact` | Database table name |
| `direction` | `REMOTE→LOCAL` | Data flow direction |
| `src` | `REMOTE@76.13.185.210(15)` | Source alias, host, row count |
| `tgt` | `LOCAL@localhost(15)` | Target alias, host, row count |
| `rows_synced` | `15` | Rows actually inserted |
| `elapsed` | `1.4s` | Wall-clock time |
| `dry_run` | `True` / `False` | Whether `--dry-run` was active |
| `status` | `OK` / `ABORTED` / `ERROR` | Outcome |
| `cmd` | `manage.py sync_model ...` | Full command as executed |

### Sample Log Entry

```
[2026-02-15 21:42:07 UTC] user=williamjames@MacBookPro model=core.Setting table=core_setting direction=REMOTE→LOCAL src=REMOTE@76.13.185.210(47) tgt=LOCAL@localhost(47) rows_synced=47 elapsed=0.8s dry_run=False status=OK cmd="manage.py sync_model setting --direction to-local --no-confirm"
```

The log captures successful syncs, dry-runs, user aborts, and errors.
Use `tail -f logs/sync_model.log` to monitor during batch operations.


## Typical Workflows

### Refresh local dev data from remote

When your local database is empty or stale and you want to work with
production-like data:

```bash
# Core reference data
python manage.py sync_model org --direction to-local --no-confirm
python manage.py sync_model contact --direction to-local --no-confirm
python manage.py sync_model setting --direction to-local --no-confirm

# Products
python manage.py sync_model item --direction to-local --no-confirm
python manage.py sync_model warehouse --direction to-local --no-confirm

# Transactions
python manage.py sync_model order --direction to-local --no-confirm
python manage.py sync_model invoice --direction to-local --no-confirm
```

### Seed a single table after schema change

After running a migration that adds a new table, pull its data from
remote:

```bash
python manage.py sync_model specification --direction to-local
```


## Caveats

| Concern | Detail |
|---|---|
| **Non-destructive** | Existing records in the target table are preserved and updated or new records are inserted. No rows are deleted. |
| **Single table** | Does not follow FK relationships automatically. Sync parent tables before children if you need referential integrity. |
| **Performance** | Uses Django ORM `save()` per-row (batched in 500s). Large tables (100k+ rows) will be slow over the network. For bulk loads, consider `pg_dump`/`pg_restore`. |
| **No incremental sync** | Always does a full update/insert. Not suitable for ongoing replication. |
| **Trigger side effects** | Triggers are disabled during insert, so any `post_save` signals or DB-level triggers will **not** fire for the synced rows. |
| **CASCADE risk** | Triggers are disabled, but no TRUNCATE is performed. |

## Related Documentation

- [Dev DB Strategy](dev-db-strategy.md) — SQLite vs Postgres dual-lane
  approach
- [Data Set Identification](../../data-set-identification.md) — how
  `DB_MODE`, `DATA_SET_ID`, and `SystemInfoView` work together
- [Settings](settings.md) — `LOCAL_DATABASE_*` and `REMOTE_DATABASE_*`
  env vars
- [Connections](connections.md) — database connection architecture
