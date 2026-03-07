# Data Synchronization — Consolidated Reference

Date: 2026-03-06
Status: Authoritative (consolidates 6 prior docs)
Owner: Bill

---

## Table of Contents

- [Purpose](#purpose)
- [Decision Matrix — Which Tool When](#decision-matrix--which-tool-when)
- [Database Modes](#database-modes)
  - [Remote (default)](#remote-default)
  - [Local](#local)
  - [Write-Through (recommended for daily dev)](#write-through-recommended-for-daily-dev)
  - [Local-Sync (async push to remote)](#local-sync-async-push-to-remote)
- [Switching Modes](#switching-modes)
  - [CLI — switch-dataset.sh](#cli--switch-datasetsh)
  - [API Endpoints (DevTools)](#api-endpoints-devtools)
  - [Manual .env Edit](#manual-env-edit)
  - [Environment Flags](#environment-flags)
- [Write-Through Proxy](#write-through-proxy)
  - [Architecture](#architecture)
  - [Configuration](#write-through-configuration)
  - [Save View Wiring](#save-view-wiring)
  - [Core Module — common/write_through.py](#core-module--commonwrite_throughpy)
  - [Error Handling](#write-through-error-handling)
- [sync_model Management Command](#sync_model-management-command)
  - [Overview](#sync_model-overview)
  - [Quick Start](#sync_model-quick-start)
  - [How It Works](#sync_model-how-it-works)
  - [Arguments & Flags](#arguments--flags)
  - [Environment Variables](#sync_model-environment-variables)
  - [Examples](#sync_model-examples)
  - [FK Constraint Handling](#fk-constraint-handling)
  - [Update-on-Match & Conflict Resolution](#update-on-match--conflict-resolution)
  - [Sequence Reset](#sequence-reset)
  - [Audit Log](#audit-log)
  - [Bundle Logging](#bundle-logging)
- [Raw SQL Sync Scripts (tools/)](#raw-sql-sync-scripts-tools)
  - [sync_remote_to_local.py](#sync_remote_to_localpy)
  - [sync_local_to_remote.py](#sync_local_to_remotepy)
- [Data Export / Import / Restore](#data-export--import--restore)
  - [export_data](#export_data)
  - [restore_data / restore_data_smart](#restore_data--restore_data_smart)
  - [data_load_json](#data_load_json)
- [Readme / Documentation Sync](#readme--documentation-sync)
- [Destructive Reset (reseed)](#destructive-reset-reseed)
- [Identity Model — id + uuid + ida](#identity-model--id--uuid--ida)
  - [IDA — Born-On Identity](#ida--born-on-identity)
  - [The Matching Rule](#the-matching-rule)
  - [Change Detection Fields](#change-detection-fields)
- [§25 Sync Topologies](#25-sync-topologies)
  - [Scenario 1 — Hub & Spoke (Outage / Merge)](#scenario-1--hub--spoke-outage--merge)
  - [Scenario 2 — Peer Transfer (Catalog Exchange)](#scenario-2--peer-transfer-catalog-exchange)
  - [Identity Rules by Scenario](#identity-rules-by-scenario)
  - [Id Block-Allocation (Future)](#id-block-allocation-future)
- [Pre-Flight Migration Check](#pre-flight-migration-check)
- [FK Dependency Order](#fk-dependency-order)
- [Incremental Sync Design (Future Phases)](#incremental-sync-design-future-phases)
  - [Phase 1 — Timestamp-Based Delta Pull](#phase-1--timestamp-based-delta-pull)
  - [Phase 2 — Bidirectional Merge](#phase-2--bidirectional-merge)
  - [Phase 3 — Event-Driven Notification](#phase-3--event-driven-notification)
- [Local-Sync Bundle Strategy (§25.1)](#local-sync-bundle-strategy-251)
  - [How Bundling Works](#how-bundling-works)
  - [FK Dependency Collection](#fk-dependency-collection)
  - [FK Resolution via uuid_map](#fk-resolution-via-uuid_map)
  - [Celery Retry Configuration](#celery-retry-configuration)
  - [Signal Suppression](#signal-suppression)
  - [Worker Health Integration](#worker-health-integration)
  - [Response Enrichment](#response-enrichment)
- [Data Set Identification](#data-set-identification)
- [Remote Database Audit & Cleanup Tools](#remote-database-audit--cleanup-tools)
- [File Reference](#file-reference)
- [Safety & Guardrails](#safety--guardrails)
- [Quick Reference Cheatsheet](#quick-reference-cheatsheet)
- [Changelog](#changelog)

---

## Purpose

This is the **single authoritative reference** for all data synchronization between remote and local PostgreSQL databases, database mode switching, documentation sync, and related tooling.

It consolidates six prior documents:
- `database-sync-strategy.md` — sync strategy + write-through design
- `sync-model.md` — sync_model command reference
- `write-through.md` — write-through proxy
- `database-switching.md` — switching between remote/local/write-through
- `data-set-identification.md` — environment identification
- `docs-sync.md` — readme documentation sync pipeline

---

## Decision Matrix — Which Tool When

| Scenario | Tool | Command |
|----------|------|---------|
| **Daily development** | Write-through proxy | `DB_MODE=write-through` in `.env` |\n| **Daily dev (slow remote)** | Local-sync | `DB_MODE=local-sync` in `.env` (needs Celery worker) |
| **Initial local DB setup** | pg_dump / pg_restore | See [Switching Modes](#switching-modes) |
| **Pull one model from remote** | sync_model | `python manage.py sync_model contact --direction to-local` |
| **Pull all models from remote** | sync_model all | `python manage.py sync_model all --direction to-local` |
| **Push one model to remote** | sync_model | `python manage.py sync_model setting --direction to-remote` |
| **Full database copy (fast)** | Raw SQL scripts | `python tools/sync_remote_to_local.py` |
| **Re-seed after local DB loss** | pg_dump or sync_model all | See [Quick Reference](#quick-reference-cheatsheet) |
| **Export data as JSON backup** | export_data | `python manage.py export_data` |
| **Restore from JSON backup** | restore_data_smart | `python manage.py restore_data_smart` |
| **Clean slate + synthetic data** | reseed | `python manage.py reseed --full` |
| **Sync readmes to Document table** | sync_readmes | `python manage.py sync_readmes` |
| **Switch database mode** | switch-dataset.sh | `./tools/switch-dataset.sh write-through` |
| **Check current mode** | switch-dataset.sh | `./tools/switch-dataset.sh status` |
| **Preview without changes** | sync_model --dry-run | `python manage.py sync_model item --direction to-local --dry-run` |
| **Audit remote data quality** | SQL/Python scripts | See [Audit Tools](#remote-database-audit--cleanup-tools) |

---

## Database Modes

Three modes control which PostgreSQL instance Django reads from and writes to:

| Mode | Reads | Writes | Use Case |
|------|-------|--------|----------|
| **remote** | Remote server | Remote server | Team collaboration — shared data |
| **local** | localhost | localhost | Isolated debugging — safe to break |
| **write-through** | localhost | Remote → syncs back to local | Fast reads + authoritative remote writes |
| **local-sync** | localhost | localhost + Celery → remote async | Fast saves, async merge to shared DB |

**Remote is always the default.** `./runserver.sh` force-resets to remote on every boot as a safety measure.

### Remote (default)

All reads and writes go to the shared remote server. Everyone sees the same data.

### Local

Fully isolated. No network dependency. Safe for destructive experiments.

Requires a local PostgreSQL database seeded from remote (see [Switching Modes](#switching-modes)).

### Write-Through (recommended for daily dev)

The best of both worlds:
- **Reads** hit localhost — instant, no network latency
- **Writes** go to the remote server — shared data stays authoritative
- After a successful remote save, the record is written back to local — both databases stay in sync without a separate sync step

If the remote is unreachable, the save returns HTTP 502 — nothing is written locally either, keeping both databases consistent.

### Local-Sync (async push to remote)

Saves go to local database immediately (fast), then a **Celery task** pushes the record + its entire FK dependency tree to remote in the background.

**Advantages over write-through:**
- Saves return instantly — no waiting for slow remote DB
- If remote is temporarily down, saves still succeed locally; Celery retries automatically
- Pending inventory processing happens immediately on local

**Trade-offs:**
- Other users on remote won't see changes until the Celery task completes (typically 2-5 seconds)
- If Celery worker is down, syncs queue in Redis and process when worker restarts

**Scope:** Applies to **all saves** — both `/wcapi/save/` (generic models) and `/wcapi/transaction/save/` (transaction headers + lines). Any model saved in local-sync mode is queued for async push to remote.

**Sync tracking:** After Celery pushes to remote, it stamps `metadata.history.synced.dt` on the local record. The frontend can show a sync badge using this timestamp.

```env
DB_MODE=local-sync
```

**Implementation:** `common/sync_tasks.py` — `sync_record_to_remote()` (universal), `dispatch_sync_to_remote()`

---

## Switching Modes

### CLI — switch-dataset.sh

```bash
cd tools/
./switch-dataset.sh remote        # switch to remote
./switch-dataset.sh local         # switch to local (triggers sync by default)
./switch-dataset.sh write-through # switch to write-through
./switch-dataset.sh local-sync    # switch to local-sync (async push to remote)
./switch-dataset.sh status        # show current mode
```

The script updates `DB_MODE` in `.env` and `db_mode` in `tools/dev-config.json`, then optionally restarts Django and Vite.

### API Endpoints (DevTools)

Available when `DEBUG=True` and `DATA_SET_ID` is `DEV` or `LOCAL`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wcapi/dev/config/` | GET | Current mode and available modes |
| `/wcapi/dev/sync-status/` | GET | Sync progress (reads `tools/.sync_status.json`) |
| `/wcapi/dev/switch/` | POST | Switch mode (config only, no data sync) |
| `/wcapi/dev/sync/` | POST | Trigger data sync (download or upload) |
| `/wcapi/dev/restart/` | POST | Trigger server restart |

```bash
# Switch via API
curl -X POST http://localhost:8000/wcapi/dev/switch/ \
  -H "Content-Type: application/json" \
  -d '{"mode": "local"}'

# Download remote → local via API
curl -X POST http://localhost:8000/wcapi/dev/sync/ \
  -H "Content-Type: application/json" \
  -d '{"direction": "download"}'
```

### Manual .env Edit

Change `DB_MODE` in `.env` directly and restart Django:

```env
DB_MODE=write-through    # or: remote, local
```

### Environment Flags

| Flag | Effect |
|------|--------|
| `SKIP_RESTART=1` | Don't restart servers after switching |
| `SKIP_LOCAL_SYNC=1` | Switch to local without syncing data |
| `FORCE_LOCAL_SYNC=1` | Force re-sync while already in local |
| `SWITCH_HEADLESS=1` | Non-interactive mode (used by API) |
| `REQUEST_CONSOLE_RESTART=1` | Signal `runserver.sh` loop to auto-restart |

### First-Time Local Database Setup

```bash
# 1. Create the local database
createdb -U williamjames commerce_expert

# 2. Seed from remote via pg_dump
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert

# 3. Set mode in .env
DB_MODE=write-through

# 4. Start server
python manage.py runserver
```

### Re-Seeding Local (if stale)

```bash
dropdb -U williamjames commerce_expert
createdb -U williamjames commerce_expert
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert
```

---

## Write-Through Proxy

### Architecture

```
Browser ──GET──────────► Django ──► Local Postgres (fast read)
Browser ──POST/PUT──────► Django ──► Remote Postgres (authoritative)
                                        │
                                   save succeeds → returns id, uuid,
                                   version, dt_modified
                                        │
                                        ▼
                                   Django stores the remote's response
                                   back into Local Postgres
                                        │
                                        ▼
                                   Response to browser
```

Uses Django's multi-database ORM (`using=alias`) — direct Postgres-to-Postgres, **not** HTTP forwarding. No running remote Django server required.

### Write-Through Configuration

| Variable | Purpose | Default |
|---|---|---|
| `DB_MODE` | `remote` / `local` / `write-through` | `remote` |
| `WRITE_THROUGH_TIMEOUT` | Seconds before remote save fails | `30` |
| `REMOTE_DATABASE_HOST` | Remote Postgres host | `76.13.185.210` |
| `LOCAL_DATABASE_HOST` | Local Postgres host | `localhost` |

When `write-through` is active, `settings.py` configures:
- `DATABASES['default']` → local Postgres (reads)
- `DATABASES['_wt_remote']` → remote Postgres (writes)
- `WRITE_THROUGH_ENABLED = True`

### Save View Wiring

All save endpoints are gated by `is_write_through()` (write-through mode) and `is_local_sync()` (local-sync mode):

| View | File | Write-Through | Local-Sync | Handles |
|---|---|---|---|---|
| `SaveWcapiView` | `apps/core/views/save_view.py` | `forward_and_store()` | `dispatch_sync_to_remote()` | Generic model saves |
| `WCAPITransactionSaveView` | `apps/transactions/views/wcapi.py` | `forward_transaction_and_store()` | `dispatch_sync_to_remote()` | Transaction header + lines |
| `WCAPISaveView` | `apps/transactions/views/wcapi.py` | delegates to above | delegates to above | Simple delegate saves |

When `DB_MODE` is `remote` or `local`, views behave as default — direct save to the configured database with no secondary sync.

### Core Module — common/write_through.py

**Public API:**

```python
is_write_through() → bool
get_remote_alias() → str
forward_and_store(request, model_cls, payload) → (dict, status_code)
forward_transaction_and_store(request, model_key, record_data, lines_data, options) → (dict, status_code)
```

**Key design decisions:**
- Uses `models.Model.save()` (not `CoreModel.save()`) when storing bundles locally, so remote's exact `version`, `dt_modified`, `id` are preserved
- Sets `_sync_in_progress = True` to suppress post_save signals
- Matches by **uuid first**, falls back to PK for local storage
- Resets PostgreSQL auto-increment sequence after each store

### Write-Through Error Handling

| Scenario | Response |
|---|---|
| Remote DB unreachable | `502` with `write_through_error: True` |
| Record not found on remote (update) | `404` |
| Remote save raises exception | `502` with error detail |
| Remote save OK but local sync fails | `200` (data is safe on remote) + warning logged |

---

## sync_model Management Command

### sync_model Overview

`sync_model` copies rows for a single model (or all models) between local and remote PostgreSQL databases. It connects to **both** databases simultaneously (regardless of `DB_MODE`) via Django's serialization framework.

**Location:** `apps/core/management/commands/sync_model.py`

The command is non-destructive — it updates or inserts rows in the target table, preserving existing records. No rows are deleted.

### sync_model Quick Start

```bash
cd webClerk3 && source bin/activate

# Pull all contacts from remote → local
python manage.py sync_model contact --direction to-local

# Push local settings → remote
python manage.py sync_model setting --direction to-remote

# Sync ALL blessed models (remote → local)
python manage.py sync_model all --direction to-local

# Preview what would happen
python manage.py sync_model item --direction to-local --dry-run

# See all available model names
python manage.py sync_model --list
```

### sync_model How It Works

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

1. **Serialize** — Read all rows from source via Django ORM and serialize to JSON
2. **Update/Insert** — For each row, update existing records if PK/UUID match, insert new records otherwise
3. **Disable triggers** — `ALTER TABLE ... DISABLE TRIGGER ALL` on target so FK constraints don't block inserts
4. **Reset sequence** — `setval(pg_get_serial_sequence(...))` to `MAX(id) + 1`

### Arguments & Flags

| Argument | Required | Description |
|---|---|---|
| `model_name` | Yes (unless `--list`) | WCAPI blessed key (`contact`, `item`) or `app.Model` (`core.Contact`) |
| `--direction` | Yes | `to-local` (remote → local) or `to-remote` (local → remote) |
| `--dry-run` | No | Show row counts and plan without modifying data |
| `--list` | No | Print all available models with tables and exit |
| `--no-confirm` | No | Skip the interactive confirmation prompt |
| `--conflict` | No | `record` (default, update existing) or `new` (create new record for UUID mismatch) |

### sync_model Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `LOCAL_DATABASE_NAME` | `commerce_expert` | Local DB name |
| `LOCAL_DATABASE_USER` | `williamjames` | Local DB user |
| `LOCAL_DATABASE_PASS` | *(empty)* | Local DB password |
| `LOCAL_DATABASE_HOST` | `localhost` | Local DB host |
| `LOCAL_DATABASE_PORT` | `5432` | Local DB port |
| `REMOTE_DATABASE_NAME` | `commerce_expert` | Remote DB name |
| `REMOTE_DATABASE_USER` | `postgres` | Remote DB user |
| `REMOTE_DATABASE_PASS` | *(from .env)* | Remote DB password |
| `REMOTE_DATABASE_HOST` | *(from .env)* | Remote DB host |
| `REMOTE_DATABASE_PORT` | `5432` | Remote DB port |

### sync_model Examples

```bash
# Pull remote contacts into local
python manage.py sync_model contact --direction to-local

# Push local settings to remote
python manage.py sync_model setting --direction to-remote

# Sync all blessed models at once
python manage.py sync_model all --direction to-local --no-confirm

# Dry-run
python manage.py sync_model item --direction to-local --dry-run

# Use app.Model format
python manage.py sync_model core.Action --direction to-local

# Conflict resolution: create new records for UUID mismatches
python manage.py sync_model action --direction to-remote --conflict new

# Skip confirmation (for scripts/CI)
python manage.py sync_model contact --direction to-local --no-confirm
```

### FK Constraint Handling

Triggers are **disabled** on the target table during insertion because tables are synced one at a time and the target may not yet have referenced rows. Triggers are always re-enabled in a `finally` block.

For referential integrity, sync parent tables before children (see [FK Dependency Order](#fk-dependency-order)).

### Update-on-Match & Conflict Resolution

When a row fails to insert due to FK constraint:

- If PK + UUID match → existing row is **updated** with new field values
- If PK matches but UUID does not → logged as a conflict (`--conflict record`) or creates a new record (`--conflict new`)
- If no matching PK → logged as conflict or creates new record depending on mode

The audit log records both updated count and FK conflicts as JSON in the error field.

### Sequence Reset

After inserting rows, the command resets the PostgreSQL auto-increment sequence to `MAX(pk) + 1`. Silently skipped for UUID primary keys.

### Audit Log

Every invocation is appended to `logs/sync_model.log` as a single-line structured record.

| Field | Example | Description |
|---|---|---|
| `timestamp` | `2026-02-15 21:38:38 UTC` | When the command ran |
| `user` | `williamjames@MacBookPro` | OS username + hostname |
| `model` | `core.Contact` | Resolved app_label.Model |
| `table` | `core_contact` | Database table name |
| `direction` | `REMOTE→LOCAL` | Data flow direction |
| `src` | `REMOTE@76.13.185.210(15)` | Source alias, host, row count |
| `tgt` | `LOCAL@localhost(15)` | Target alias, host, row count |
| `rows_synced` | `15` | Rows inserted |
| `elapsed` | `1.4s` | Wall-clock time |
| `dry_run` | `True/False` | Whether dry-run was active |
| `status` | `OK/ABORTED/ERROR` | Outcome |
| `cmd` | `manage.py sync_model ...` | Full command |

### Bundle Logging

Every non-dry-run sync creates a lightweight `sync.Bundle` record in the database. This provides queryable sync history without storing full payloads.

**Connection:** A single `sync.Connection` record (name=`sync_model`, type=`internal`, purpose=`sync`) is auto-created on first use via `get_or_create`. No data migration required.

**Bundle fields populated:**

| Bundle Field | Value | Description |
|---|---|---|
| `connection` | FK → `sync_model` Connection | Always the internal sync connection |
| `direction` | `pull` or `push` | `pull` = to-local, `push` = to-remote |
| `config` | `{model, table, src, tgt, src_count, tgt_count, updated}` | Sync coordinates (small JSON) |
| `status` | `success` or `warning` | `warning` when FK conflicts occurred |
| `alert` | `none` or `warning` | Mirrors status for UI visibility |
| `duration` | elapsed milliseconds | Wall-clock time |
| `size` | rows synced count | Number of rows inserted |
| `conflicts` | conflict details or `null` | Only populated when integrity errors occur |
| `response` | `null` | Not used — kept lightweight |
| `payload` | `null` | Not used — kept lightweight |

**Query examples:**

```python
from apps.sync.models import Bundle

# All sync history
Bundle.objects.filter(connection__name='sync_model').order_by('-dt_created')

# Only syncs with conflicts
Bundle.objects.filter(connection__name='sync_model', conflicts__isnull=False)

# Last sync for a specific model
Bundle.objects.filter(
    connection__name='sync_model',
    config__model='core.Contact',
).latest('dt_created')
```

**Non-fatal:** Bundle creation is wrapped in a try/except. If it fails (e.g., database connectivity), the sync itself still succeeds — only a warning is logged.

---

## Raw SQL Sync Scripts (tools/)

For bulk full-database copies (faster than sync_model for large datasets), two raw psycopg2 scripts bypass Django entirely:

### sync_remote_to_local.py

```bash
cd tools/
python sync_remote_to_local.py --status-file .sync_status.json
```

Truncates all local public tables (except `django_migrations`), copies all rows from remote in 1,000-row batches, resets sequences. Writes progress to `.sync_status.json` for the DevTools API.

### sync_local_to_remote.py

```bash
cd tools/
python sync_local_to_remote.py
```

Mirror of the above but local → remote. **Never called automatically** — pushing to the shared remote is an intentional action.

> **When to use these vs sync_model:** Use the raw SQL scripts for complete database copies (fast, all tables at once). Use `sync_model` for targeted single-model syncs with PK/UUID-aware conflict handling.

---

## Data Export / Import / Restore

### export_data

Exports all model data to JSON files in `webclerk3_data/`:

```bash
python manage.py export_data
```

### restore_data / restore_data_smart

`restore_data_smart` is the recommended restore command — schema-tolerant, handles unknown fields gracefully:

```bash
python manage.py restore_data_smart                # restore all
python manage.py restore_data_smart --file contacts.json  # single file
python manage.py restore_data_smart --dry-run      # preview
python manage.py restore_data_smart --clear        # clear tables first
```

`restore_data` is the older variant using Django `loaddata` with a hardcoded FK-safe ordering.

### data_load_json

Load seed/demo data from a specific JSON file into a model:

```bash
python manage.py data_load_json mydata.json --model core.Contact
python manage.py data_load_json mydata.json --model core.Contact --drop  # clear first
```

---

## Readme / Documentation Sync

The `sync_readmes` management command ingests markdown files from `readmes/` into `Document` rows (`model_name = 'readme'`), exposed via API and exported as a JSON index for React.

```bash
# Standard sync (skip unchanged files)
python manage.py sync_readmes

# Dry run
python manage.py sync_readmes --dry-run

# Force refresh all
python manage.py sync_readmes --force

# Export search index
python manage.py sync_readmes --export-index

# Filter by glob pattern
python manage.py sync_readmes --pattern "readmes/api/*.md"

# Delete docs whose source files are gone
python manage.py sync_readmes --delete-missing

# Add additional scan root
python manage.py sync_readmes --root docs

# Handle large files
python manage.py sync_readmes --max-bytes 65536 --truncate
```

Key features: idempotent (SHA256 checksum comparison), collision-safe slugs, modification time gating, size management.

**API access:**
- `GET /api/docs/readmes/` — list of readme documents
- `GET /api/docs/readmes/<slug>/` — detail with full body

See `apps/core/management/commands/sync_readmes.py` for implementation.

---

## Destructive Reset (reseed)

For a clean-slate local rebuild with synthetic data:

```bash
# Full destructive reset + seed + 3 superusers
python manage.py reseed --full

# Quick reseed without dropping DB
python manage.py reseed_all_models

# Target a single model
python manage.py reseed_all_models --model apps.core.models.Contact --per-model 5
```

Creates patterned superusers: `1@1.com / 1111pass`, `2@2.com / 1111pass`, `3@3.com / 1111pass`.

**Use sparingly.** Only for clean-slate situations — migration history squash, schema drift, pristine baseline testing. See `readmes/reset.md` for the full guide.

---

## Identity Model — id + uuid + ida

Every record inherits from `CoreModel`:

| Field | Type | Purpose |
|---|---|---|
| `id` | BigAutoField | PK, auto-increment. **Source of truth** from the primary (remote) database. Overwrites local id on sync. |
| `uuid` | UUIDField | Unique **across all databases** — cross-database matching key |
| `ida` | CharField(40) | Born-on identifier with environment prefix. Created once; **never overwritten** by sync. |
| `dt_created` | BigInteger | Epoch ms, set once on insert |
| `dt_modified` | BigInteger | Epoch ms, updated on every save |
| `version` | PositiveInt | Bumped on every update |

### IDA — Born-On Identity

The `ida` field is a locally generated soft identifier that tells users *where* a record was created. It uses the format `{IDA_PREFIX}-{pk}` and is assigned once on first save via `CoreModel.save()`.

| Database | DATA_SET_ID | IDA_PREFIX | Example ida |
|---|---|---|---|
| Production | PRODUCTION | `ida` | `ida-1087` |
| Development | DEV | `DEV` | `DEV-42` |
| Local | LOCAL | `LOC` | `LOC-42` |
| Staging | STAGING | `STG` | `STG-99` |

**Configuration** (`.env`):

```env
DATA_SET_ID=DEV                 # environment type
IDA_PREFIX=DEV                  # explicit override (optional; auto-derived from DATA_SET_ID)
```

**Key rules:**
- ida is generated **once** on first save via `CoreModel.save()` + `common/ida.py`
- **uuid is the only truly immutable cross-database identity** — never overwritten
- ida **can** be overwritten during hub-spoke merge (primary is authoritative)
- ida is always **new** in the target during peer transfer (source ida ignored)
- `write_through.py` allows remote ida to flow to local (remote is primary)
- `sync_model.py` allows ida to flow from source like any other field
- The `fix_ida_values.py` tool only repairs **empty or malformed** idas — valid prefixed idas from other environments are preserved
- See **[§25 Sync Topologies](#25-sync-topologies)** for full rules per scenario

**Implementation:** `common/ida.py` — `get_ida_prefix()`, `generate_ida(pk)`, `is_local_ida(ida)`, `parse_ida(ida)`

### The Matching Rule

| id match? | uuid match? | Interpretation | Action |
|---|---|---|---|
| Yes | Yes | Same record, same entity | **Update** — take later `dt_modified` |
| Yes | No | PK collision, different entities | **Conflict** — reassign PK |
| No | Yes | Same entity, different PKs | **Update** — align to target's PK |
| No | No | Completely different records | **Insert** |

The **uuid is the authoritative cross-database identity**. The id is a database-local convenience.

### Change Detection Fields

| Field | Sync Use |
|---|---|
| `dt_modified` | Query `filter(dt_modified__gt=last_sync_ts)` for delta sync |
| `version` | Compare to detect conflicts (higher = newer) |
| `dt_created` | `dt_created > last_sync_ts` = new record since last sync |

---

## §25 Sync Topologies

Two distinct synchronization scenarios govern how `id`, `ida`, and `uuid` behave during data movement. Understanding which scenario applies is critical — the identity rules differ.

### Scenario 1 — Hub & Spoke (Outage / Merge)

**Use case:** Cloud primary ↔ local backup, field laptops, outage-recovery merge.

```
         ┌────────────────────┐
         │  Cloud Primary DB  │  ← authoritative for id + ida
         │  (PRODUCTION)      │
         └──────┬───────┬─────┘
                │       │
       sync     │       │   sync
       to-local │       │   to-local
                │       │
         ┌──────▼──┐ ┌──▼──────┐
         │ Local   │ │ Field   │  ← satellites
         │ Backup  │ │ Laptop  │
         └─────────┘ └─────────┘
```

**Identity behaviour:**

| Field | During sync | Rationale |
|-------|------------|-----------|
| `id` | Primary's id overwrites satellite | PK alignment for uniform FK graphs |
| `ida` | Primary's ida overwrites satellite | Primary generated the authoritative born-on identity |
| `uuid` | **NEVER changes** | Cross-database matching key — immutable |

**When satellites operate disconnected:**
- Satellites generate records with their own ida prefix (e.g. `LOC-42`)
- On reconnect, the primary's merge process matches by uuid
- New satellite-born records (no uuid match on primary) are imported with their satellite ida preserved
- Conflicting records resolve in favour of the primary

**Write-through mode** is the online version of this scenario — remote is the primary, local mirrors it in real-time. Remote's ida flows to local.

**Tooling:** `sync_model --direction to-local`, `write_through.py`

### Scenario 2 — Peer Transfer (Catalog Exchange)

**Use case:** Manufacturer → Company, Company A → Company B, vendor catalog import.

```
    ┌─────────────────┐         ┌─────────────────┐
    │  Manufacturer   │  ────►  │  Your Company   │
    │  DB (peer)      │ export  │  DB (target)    │
    └─────────────────┘         └─────────────────┘
```

**Identity behaviour:**

| Field | During transfer | Rationale |
|-------|-----------------|-----------|
| `id` | **Always new** in target | Target assigns its own PK |
| `ida` | **Always new** in target | Target generates its own born-on identity |
| `uuid` | Preserved as cross-dataset link | Permanent reference back to source record |

**Key differences from hub & spoke:**
- No merge — records are copied/imported as new entities
- Source `id` and `ida` are **not** authoritative in the target
- The uuid becomes a permanent cross-dataset reference (e.g. "item X in our DB was originally item Y from manufacturer Z")
- No FK cascade issues because all FKs use target-local ids

**Tooling:** Future `sync_model --mode peer-transfer` or dedicated import command

### Identity Rules by Scenario

| Field | Hub & Spoke (merge) | Peer Transfer (import) | Write-Through (online) |
|-------|--------------------|-----------------------|----------------------|
| `id` | Source overwrites target | New in target | Remote overwrites local |
| `ida` | Source overwrites target | New in target | Remote overwrites local |
| `uuid` | **Immutable** (matching key) | **Preserved** (cross-dataset link) | **Immutable** |
| Matching by | uuid | uuid | uuid → PK fallback |

**Summary:** uuid is the **only** field that is never overwritten in any scenario. Both `id` and `ida` are dataset-scoped values that can change during merge or be freshly generated during transfer.

### Id Block-Allocation (Future)

> **Status:** Design phase — not yet implemented.

To minimize PK collisions during hub-and-spoke disconnected operation, each satellite can pre-allocate a block of ids from the primary:

```
Primary reserves ranges:
  Satellite A: ids 10,000 – 19,999
  Satellite B: ids 20,000 – 29,999
  Primary:     ids 1 – 9,999 and 30,000+
```

This approach (used in WC2/4D) eliminates most merge conflicts:
- Each satellite auto-increments within its allocated range
- On merge, ids don't collide → no FK cascade problems
- When a satellite exhausts its range, it requests a new block

**Components needed:** allocation endpoint on primary, local sequence seed per satellite, range exhaustion + renewal handling.

---

## Pre-Flight Migration Check

Before any sync, `sync_model` runs an automatic migration parity check to detect schema drift between databases. This prevents data corruption from mismatched schemas.

### Usage

```bash
# Stand-alone migration check (no sync)
python manage.py sync_model --check-migrations

# Include column-level drift detection
python manage.py sync_model --check-migrations --check-columns

# Check for a specific model only
python manage.py sync_model contact --check-migrations

# Skip the pre-flight check (expert mode)
python manage.py sync_model contact --direction to-local --skip-migration-check
```

### Check Levels

| Level | What it checks | Default |
|---|---|---|
| **Migrations** | `django_migrations` table parity | Always |
| **Tables** | Tables present in one DB but not the other | Always |
| **Columns** | Column name/type differences per table | Opt-in (`--check-columns`) |

### Report Output

The checker produces a structured report with:
- **Errors** — migration or table mismatches that will cause sync failures
- **Warnings** — column-level differences (opt-in)
- **Remediation steps** — numbered actionable fix instructions

If mismatches are detected during a sync operation, the user is prompted to continue or abort (respects `--no-confirm`).

**Implementation:** `common/migration_check.py` — `check_migration_parity()`, `check_migration_parity_for_model()`, `format_remediation()`

---

## Local-Sync Bundle Strategy (§25.1)

When `DB_MODE=local-sync`, the `sync_record_to_remote` Celery task pushes records using a **bundle strategy** that preserves FK relationships in a single ordered batch — avoiding multiple slow remote round trips.

### How Bundling Works

```
  Local DB (fast reads)                    Remote DB
  ──────────────────────                   ─────────
  1. COLLECT — walk FK tree   ────►  (no remote queries)
     from saved record, build
     ordered dependency graph

  2. ORDER — topological sort
     leaf deps first, main record
     last, child lines after

  3. PUSH — iterate sorted bundle,   ────►  INSERT or UPDATE
     push each record to remote,             each record,
     building uuid→remote_pk map             FK values resolved
     as we go                                via uuid_map

  4. MARK — stamp local record        (local DB write)
     metadata.history.synced.dt
```

**Example bundle for an Order save:**
```
[OrgBase#87, OrgBase#69, Contact#40, Order#12, OrderLine#15, OrderLine#16]
```

> Leaf dependencies (orgs) appear before dependents (contacts) before the main record (order) before child lines — so FK targets exist on remote before records that reference them.

### FK Dependency Collection

`_collect_fk_deps()` walks the record's FK fields recursively:
- Adds FK targets to the bundle **before** the record that references them
- Depth-limited to `MAX_FK_DEPTH = 3` (prevents cycles)
- Cycle-safe via `OrderedDict` key check (`ModelName:pk`)
- All reads are against the local database (fast, no remote queries)

For transaction headers, child lines are also collected with their own FK deps (e.g. `item_fk` on each line).

### FK Resolution via `uuid_map`

When pushing a record that has FK fields, the task must translate local FK values to remote PKs. Resolution order (fastest first):

| Priority | Source | Cost | Description |
|---|---|---|---|
| 1 | `uuid_map` | Free | Populated by earlier records in the same bundle |
| 2 | Remote uuid query | 1 query | Falls back when FK target was synced in a prior task |
| 3 | Raw value | Free | When related record has no uuid — assumes same PK space |

### Celery Retry Configuration

| Setting | Value | Purpose |
|---|---|---|
| `autoretry_for` | `(Exception,)` | Retry on any failure |
| `retry_backoff` | `True` | Exponential: 1s, 2s, 4s, 8s, … |
| `retry_backoff_max` | `300` (5 min) | Cap backoff duration |
| `max_retries` | `10` | Give up after 10 attempts |
| `retry_jitter` | `True` | Randomize backoff to prevent thundering herd |
| `acks_late` | `True` | Acknowledge only after success (crash-safe) |
| `reject_on_worker_lost` | `True` | Re-queue if worker dies mid-task |
| `countdown` | `3` (on dispatch) | 3-second delay to let DB transaction commit |

### Signal Suppression

During remote push, each record has `_sync_in_progress = True` set before save. This flag suppresses `post_save` signals on the remote database — preventing duplicate side-effects (pending records, event logging, etc.).

### Worker Health Integration

The sync task calls `mark_worker_alive()` from `apps.products.dispatch_pending` on entry. This lets the pending worker health monitor detect that Celery is operational, even if no pending-specific tasks are running.

### Response Enrichment

Both save views add sync metadata to successful responses when local-sync is active:

```json
{
  "status": "success",
  "data": { ... },
  "sync_task_id": "abc-123-def",
  "sync_status": "queued"
}
```

The `sync_task_id` can be used by the frontend to poll task status if needed.

---

## FK Dependency Order

When syncing multiple tables, parent tables must be synced before children:

```
 1. core.Setting          (no FKs)
 2. orgs.OrgBase          (no FKs)
 3. core.Contact          (FK → OrgBase)
 4. products.Item         (FK → OrgBase via vendor)
 5. products.Warehouse    (no FKs)
 6. orders.Order          (FK → Contact, OrgBase)
 7. orders.OrderLine      (FK → Order, Item)
 8. invoices.Invoice      (FK → Contact, OrgBase, Order)
 9. invoices.InvoiceLine  (FK → Invoice, Item)
10. payments.Payment      (FK → Invoice, Contact)
```

Helper script pattern:

```bash
#!/bin/bash
DIRECTION=${1:-to-local}
MODELS=(setting org contact item warehouse order orderline invoice invoiceline payment)
for model in "${MODELS[@]}"; do
  echo "▸ Syncing $model ($DIRECTION)..."
  python manage.py sync_model "$model" --direction "$DIRECTION" --no-confirm
done
echo "✓ Done"
```

---

## Incremental Sync Design (Future Phases)

> **Status:** Not yet implemented. The current `sync_model` always does a full pass. These phases extend the existing infrastructure.

### Phase 1 — Timestamp-Based Delta Pull

```bash
python manage.py sync_model contact --direction to-local --since last
```

Queries source for `Model.objects.filter(dt_modified__gt=last_sync_ts)`, applies [Record Matching](#the-matching-rule), updates `SyncState` high-water mark.

### Phase 2 — Bidirectional Merge

```bash
python manage.py sync_model contact --direction merge
```

Collects changes from both sides since last sync. Partitions into remote-only, local-only, and conflict sets. Applies per-field merge or flags for manual review.

### Phase 3 — Event-Driven Notification

A `post_save` signal handler writes to a `SyncJournal` table on every mutation. The sync command reads the journal instead of scanning `dt_modified` across all records.

**Models planned:** `SyncJournal` (append-only mutation log) and `SyncState` (high-water mark per model per direction). See the [Incremental Sync Design](#incremental-sync-design-future-phases) and [Identity Model](#identity-model--id--uuid) sections above.

---

## Data Set Identification

Environment variables identify which data set is active:

```env
DATA_SET_ID=DEV                      # LOCAL, DEV, STAGING, PRODUCTION
DATA_SET_NAME=Development Server
```

**API:** `GET /wcapi/system-info/` returns environment info (no auth required).

**Frontend:** Color-coded badge in bottom-left — green = remote, blue = local. Click to expand the DevTools panel.

**Files:**
- `.env` → `DB_MODE`, database credentials
- `tools/dev-config.json` → mode + available modes for scripts and UI
- `tools/.sync_status.json` → sync progress state
- `apps/core/views/system_info.py` → API view

---

## Remote Database Audit & Cleanup Tools

| Tool | Location | Purpose |
|---|---|---|
| `remote_audit.sql` | `tools/` | Comprehensive audit: duplicate UUIDs, orphaned FKs, NULL values |
| `remote_fk_check.sql` | `tools/` | FK orphan check + UUID population |
| `populate_uuids.sql` | `tools/` | Populates NULL UUIDs with `gen_random_uuid()` |
| `populate_uuids_simple.sql` | `tools/` | Minimal version across 26 tables |
| `fix_orphan_actions.sql` | `tools/` | Remaps orphaned action.contact_id |
| `verify_cleanup.py` | `tools/` | Python verification: NULL UUIDs, orphaned FKs |
| `verify_cleanup.sql` | `tools/` | SQL verification post-cleanup |
| `audit_fk_values.py` | `tools/` | FK integrity audit |
| `check_sequences.py` | `tools/` | PostgreSQL sequence value checks |
| `check_renamed_models.sh` | `tools/` | Guard against legacy model name reintroduction |

---

## File Reference

### Core Sync Implementation

| File | Purpose |
|------|---------|
| `apps/core/management/commands/sync_model.py` | Django ORM sync command (primary sync tool) |
| `common/write_through.py` | Write-through proxy module |\n| `common/sync_tasks.py` | Celery async sync for local-sync mode |
| `common/ida.py` | IDA prefix utilities — born-on identity for cross-database sync |
| `common/migration_check.py` | Pre-flight migration parity checker |
| `tools/sync_remote_to_local.py` | Raw psycopg2: remote → local full copy |
| `tools/sync_local_to_remote.py` | Raw psycopg2: local → remote full copy |
| `tools/fix_ida_values.py` | Bulk-fix ida values to `{IDA_PREFIX}-{id}` format |
| `tools/switch-dataset.sh` | DB mode switcher shell script |

### Export / Import / Restore

| File | Purpose |
|------|---------|
| `apps/core/management/commands/export_data.py` | Export models to JSON |
| `apps/core/management/commands/restore_data.py` | Restore from JSON (loaddata) |
| `apps/core/management/commands/restore_data_smart.py` | Schema-tolerant restore |
| `apps/core/management/commands/data_load_json.py` | Load JSON into specific model |

### Readme Sync

| File | Purpose |
|------|---------|
| `apps/core/management/commands/sync_readmes.py` | Ingest markdown → Document rows |

### Reset / Seed

| File | Purpose |
|------|---------|
| `apps/core/management/commands/reseed.py` | Full destructive reset + seed |
| `apps/core/management/commands/reseed_all_models.py` | Synthetic row population |
| `apps/core/management/commands/reset_database.py` | Clear all tables |
| `apps/core/management/commands/populate_dummy_data.py` | Faker-generated data |

### Configuration

| File | Purpose |
|------|---------|
| `.env` | `DB_MODE`, database credentials |
| `tools/dev-config.json` | Mode + modes for scripts/UI |
| `tools/.sync_status.json` | Sync progress state |
| `webclerk3_api/settings.py` | DB mode → DATABASES selection |
| `apps/core/views/dev_tools.py` | API endpoints for switching |
| `runserver.sh` | Server loop with remote-default enforcement |

### Local-Sync (Async Remote Push)

| File | Purpose |
|------|---------|
| `common/sync_tasks.py` | Celery task: `sync_record_to_remote()` — universal bundle push |
| `common/sync_tasks.py` | `dispatch_sync_to_remote()` — view dispatch helper |
| `common/sync_tasks.py` | `_collect_fk_deps()`, `_push_one_to_remote()`, `_resolve_fk_via_map()` |

### Sync App (External Integrations)

| File | Purpose |
|------|---------|
| `apps/sync/models/connection.py` | External integration endpoint model |
| `apps/sync/models/bundle.py` | Exchange audit log model |
| `apps/sync/choices.py` | Connection types, statuses, purposes |
| `apps/sync/services/` | Google Calendar, email/phone/address verification |

---

## Safety & Guardrails

| Safeguard | Description |
|---|---|
| **Remote default** | `runserver.sh` force-resets to remote on every boot |
| **Dry-run** | `--dry-run` previews without touching data |
| **Audit log** | Every sync appended to `logs/sync_model.log` |
| **Non-destructive** | `sync_model` does insert/update only — no DELETE/TRUNCATE |
| **Confirmation prompt** | Interactive "Type 'yes'" unless `--no-confirm` |
| **Signal suppression** | `_sync_in_progress = True` prevents re-journaling |
| **FK trigger disable** | Disabled during sync, re-enabled in `finally` block |
| **Write-through fail-fast** | Remote unreachable → 502, nothing written locally |
| **Environment guards** | `reseed --full` checks interpreter, Django version, DEBUG |

---

## Quick Reference Cheatsheet

```bash
# ── Check current mode ──
./tools/switch-dataset.sh status

# ── Switch modes ──
./tools/switch-dataset.sh remote         # shared server (default)
./tools/switch-dataset.sh local          # isolated debugging
./tools/switch-dataset.sh write-through  # fast reads + authoritative writes\n./tools/switch-dataset.sh local-sync     # fast saves + async push to remote

# ── First-time local setup ──
createdb -U williamjames commerce_expert
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert

# ── Sync single model ──
python manage.py sync_model contact --direction to-local
python manage.py sync_model setting --direction to-remote

# ── Sync all models ──
python manage.py sync_model all --direction to-local --no-confirm

# ── Full database copy (raw SQL, fast) ──
cd tools/ && python sync_remote_to_local.py --status-file .sync_status.json

# ── Export / restore JSON backups ──
python manage.py export_data
python manage.py restore_data_smart

# ── Sync readmes to DB ──
python manage.py sync_readmes
python manage.py sync_readmes --export-index

# ── Clean slate reset ──
python manage.py reseed --full

# ── Re-seed local from remote (if stale) ──
dropdb -U williamjames commerce_expert && createdb -U williamjames commerce_expert
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert

# ── Audit remote data quality ──
psql -h 76.13.185.210 -U postgres -d commerce_expert -f tools/remote_audit.sql
```

---

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-03 | Consolidated 6 prior docs into this reference |
| 2026-03-06 | Updated local-sync scope: now covers all saves (generic + transaction), not just transactions. Renamed `sync_transaction_to_remote` → `sync_record_to_remote` (universal). Added §25.1 Bundle Strategy section with FK collection, uuid_map resolution, Celery retry config, signal suppression, response enrichment. Updated Save View Wiring table with local-sync columns. Added Local-Sync file reference section. |

*This document consolidates the former: database-sync-strategy.md, sync-model.md, write-through.md, database-switching.md, data-set-identification.md, and docs-sync.md (all removed 2026-03-03).*
