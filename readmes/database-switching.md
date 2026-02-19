# Switching Between Local and Remote Databases

webClerk3 supports three database modes that can be toggled at any time during development:

| Mode | Reads from | Writes to | Purpose |
|------|-----------|-----------|---------|
| **remote** | Remote server | Remote server | Team collaboration — everyone reads/writes the same data |
| **local** | localhost | localhost | Isolated debugging — safe to break things without affecting teammates |
| **write-through** | localhost | Remote server (then syncs back to local) | Fast local reads + saves always reach remote. Best of both worlds. |

The **remote** mode is always the default. Every time `./runserver.sh` starts, it force-resets the mode to `remote` as a safety measure.

---

## Write-Through Mode (Recommended for Daily Development)

Write-through is the recommended mode for everyday development. It gives you
the speed of a local database for all reads (page loads, searches, list views)
while ensuring every save goes to the shared remote database so teammates and
production always have the latest data.

### How it works

```
Browser ──GET /wcapi/items/──▶ Django ──▶ Local Postgres (fast)
Browser ──POST /wcapi/save/──▶ Django ──▶ Remote Postgres (authoritative)
                                              │
                                         save succeeds,
                                         returns id, uuid,
                                         version, dt_modified
                                              │
                                              ▼
                                         Django stores the
                                         remote's response
                                         back into Local Postgres
                                              │
                                              ▼
                                         Response to browser
```

**Key points:**
- **Reads** are instant — they hit `localhost`, no network latency.
- **Saves** go to the remote server so the shared database is always authoritative.
- After a successful remote save, the record is **written back to local** so both databases stay in sync without a separate sync step.
- If the remote is unreachable, the save returns a `502` error — nothing is written locally either. This keeps both databases consistent.

### Setup (one time)

```bash
# 1. Create the local database (if it doesn't exist)
createdb -U williamjames commerce_expert

# 2. Seed it from remote (requires pg_dump matching the remote Postgres version)
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert

# 3. Set write-through mode in .env
#    DB_MODE=write-through

# 4. Restart the server
python manage.py runserver
```

The boot log will confirm:
```
DATABASE  ▸  WRITE-THROUGH  read=LOCAL@localhost  write=REMOTE@76.13.185.210
```

### Switching to write-through

Edit `.env`:
```
DB_MODE=write-through
```

Or use the switcher:
```bash
./tools/switch-dataset.sh write-through
```

### Re-seeding local (if it drifts)

If a teammate made changes directly on remote and your local copy is stale:

```bash
# Drop and recreate
dropdb -U williamjames commerce_expert
createdb -U williamjames commerce_expert

# Re-seed from remote
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert
```

### Configuration

All settings are in `.env` — no code changes needed:

| Variable | Purpose | Default |
|----------|---------|---------|
| `DB_MODE` | `remote` / `local` / `write-through` | `remote` |
| `WRITE_THROUGH_TIMEOUT` | Seconds before a remote save times out | `30` |
| `REMOTE_DATABASE_HOST` | Remote Postgres host | `76.13.185.210` |
| `LOCAL_DATABASE_HOST` | Local Postgres host | `localhost` |

### Error behavior

| What happens | Result |
|-------------|--------|
| Remote is down | Save returns HTTP 502 — nothing written anywhere |
| Remote save succeeds but local sync fails | Save returns HTTP 200 (data is safe on remote), warning logged. Local will be slightly stale until next re-seed. |
| Remote rejects the save (validation error) | Normal error response, same as remote mode |

---

## How It Works

Two files are kept in sync to track the active mode:

| File | Read by | Role |
|------|---------|------|
| `.env` → `DB_MODE=remote\|local` | Django (`python-decouple`) | Runtime database selection in `settings.py` |
| `tools/dev-config.json` → `"db_mode"` | Shell scripts, React DevTools UI, API endpoints | UI display and script coordination |

When Django starts, `settings.py` reads `DB_MODE` and selects the matching credential block:

```python
# webclerk3_api/settings.py
_db_mode = config('DB_MODE', default='remote').lower()

if _db_mode == 'local':
    DATABASES = { 'default': {
        'HOST': config('LOCAL_DATABASE_HOST', default='localhost'),
        'NAME': config('LOCAL_DATABASE_NAME', default='commerce_expert'),
        'USER': config('LOCAL_DATABASE_USER', default='williamjames'),
        # ...
    }}
else:
    DATABASES = { 'default': {
        'HOST': config('REMOTE_DATABASE_HOST', ...),
        'NAME': config('REMOTE_DATABASE_NAME', ...),
        'USER': config('REMOTE_DATABASE_USER', ...),
        # ...
    }}
```

A third file, `tools/.sync_status.json`, tracks the progress of data synchronization when switching to local mode. It is written by the sync scripts and read by the `/wcapi/dev/sync-status/` API endpoint.

---

## Switching Modes

Switching modes changes which database Django connects to. This is a **config-only** operation — it updates the `DB_MODE` value and restarts the server. It does **not** copy any data between databases.

### 1. CLI — `switch-dataset.sh` (recommended)

```bash
cd tools/
./switch-dataset.sh local     # switch to local
./switch-dataset.sh remote    # switch to remote
./switch-dataset.sh status    # show current mode
```

What the script does:
1. Updates `DB_MODE` in `.env`
2. Updates `db_mode` in `tools/dev-config.json`
3. Prompts to restart Django and Vite (or auto-restarts if `./runserver.sh` is running)

> **Note:** By default, switching to local also triggers a data sync (see [Data Sync](#data-sync) below). To switch without syncing, use `SKIP_LOCAL_SYNC=1`.

**Environment flags:**

| Flag | Effect |
|------|--------|
| `SKIP_RESTART=1` | Don't restart servers after switching |
| `SKIP_LOCAL_SYNC=1` | Switch to local without syncing data |
| `SWITCH_HEADLESS=1` | Non-interactive mode (used by API) |
| `REQUEST_CONSOLE_RESTART=1` | Signal `runserver.sh` loop to auto-restart |

### 2. API Endpoints (from React DevTools or curl)

Four dev-only endpoints are available when `DEBUG=True` and `DATA_SET_ID` is `DEV` or `LOCAL`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wcapi/dev/config/` | GET | Current mode and available modes |
| `/wcapi/dev/sync-status/` | GET | Sync progress (reads `tools/.sync_status.json`) |
| `/wcapi/dev/switch/` | POST | Switch mode (config only, no data sync) |
| `/wcapi/dev/sync/` | POST | Trigger data sync (download or upload) |
| `/wcapi/dev/restart/` | POST | Trigger server restart |

**Example — switch to local via curl:**

```bash
curl -X POST http://localhost:8000/wcapi/dev/switch/ \
  -H "Content-Type: application/json" \
  -d '{"mode": "local"}'
```

**Example — download remote data to local:**

```bash
curl -X POST http://localhost:8000/wcapi/dev/sync/ \
  -H "Content-Type: application/json" \
  -d '{"direction": "download"}'
```

**Example — upload local data to remote:**

```bash
curl -X POST http://localhost:8000/wcapi/dev/sync/ \
  -H "Content-Type: application/json" \
  -d '{"direction": "upload"}'
```

The API runs `switch-dataset.sh` in headless mode with `SKIP_RESTART=1` and `REQUEST_CONSOLE_RESTART=1`, so it updates config and signals the running `./runserver.sh` loop without spawning detached servers.

### 3. Edit `.env` Manually

Change `DB_MODE` in `.env` directly and restart Django:

```
DB_MODE=local    # or remote
```

This is the lowest-level approach — it only changes the config. No data sync, no server restart.

---

## Data Sync

Data sync copies rows between the remote and local Postgres databases. It is **independent** of switching modes — you can sync data at any time, regardless of which mode is active.

### Download: Remote → Local

`tools/sync_remote_to_local.py` copies all data from the remote database into the local database:

```bash
cd tools/
python sync_remote_to_local.py --status-file .sync_status.json
```

What it does:
- Connects to both local and remote Postgres instances using credentials from `.env`
- Truncates all local public tables (except `django_migrations`)
- Copies all rows from remote → local in 1,000-row batches
- Resets sequences
- Writes progress to `tools/.sync_status.json` (polled by the `/wcapi/dev/sync-status/` API)

> **Automatic sync on switch:** By default, `switch-dataset.sh local` calls this script before completing the switch. If the sync fails, the mode switch is reverted. To skip the automatic sync, use `SKIP_LOCAL_SYNC=1`. To force a re-sync while already in local mode, use `FORCE_LOCAL_SYNC=1`.

### Upload: Local → Remote

`tools/sync_local_to_remote.py` copies all data from the local database into the remote database:

```bash
cd tools/
python sync_local_to_remote.py
```

This is **never called automatically**. Pushing local changes to the shared remote database is an intentional, deliberate action — it will overwrite what teammates see.

---

## Startup Behavior

`runserver.sh` accepts an optional mode argument:

```bash
./runserver.sh          # starts in remote mode (default)
./runserver.sh local    # starts in local mode
./runserver.sh remote   # starts in remote mode (explicit)
```

On every launch it:

1. **Sets `DB_MODE`** to the requested mode (default: `remote`) in both `.env` and `dev-config.json`
2. Frees port 8000 if occupied
3. Runs Django in a restart loop — if a `.restart_django` sentinel file appears (written by `switch-dataset.sh`), Django automatically relaunches

Remote mode remains the default to protect you from accidentally writing to the shared database when you intend to be local, and vice versa.

---

## File Reference

| File | Purpose |
|------|---------|
| `.env` | Runtime config — `DB_MODE`, database credentials |
| `tools/dev-config.json` | Mode + available modes for scripts and UI |
| `tools/.sync_status.json` | Sync progress state |
| `tools/switch-dataset.sh` | CLI database switcher |
| `tools/sync_remote_to_local.py` | Force-copy remote → local |
| `tools/sync_local_to_remote.py` | Force-copy local → remote (manual) |
| `tools/.restart_django` | Sentinel file for auto-restart |
| `tools/.pids/` | PID tracking for Django and Vite processes |
| `webclerk3_api/settings.py` | `DB_MODE` → `DATABASES` selection logic |
| `apps/core/views/dev_tools.py` | API endpoints for switching |
| `runserver.sh` | Server loop with remote-default enforcement |

---

## Quick Reference

```bash
# ── Check current mode ──
./tools/switch-dataset.sh status

# ── Switch modes (config only, no data transfer) ──

# Remote (default) — all reads and writes go to shared server
DB_MODE=remote                    # in .env

# Local — fully isolated, no network
DB_MODE=local                     # in .env

# Write-through — reads local, saves to remote, syncs back
DB_MODE=write-through             # in .env

# ── First-time local database setup ──

createdb -U williamjames commerce_expert
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert

# ── Re-seed local from remote (if stale) ──

dropdb -U williamjames commerce_expert
createdb -U williamjames commerce_expert
PGPASSWORD=wc_psql_server \
  /opt/homebrew/Cellar/postgresql@16/16.11_1/bin/pg_dump \
  -h 76.13.185.210 -U postgres -d commerce_expert \
  | psql -U williamjames -d commerce_expert

# ── Data sync (alternative to pg_dump) ──

# Download: copy remote database into local
cd tools/ && python sync_remote_to_local.py --status-file .sync_status.json

# Upload: copy local database into remote (manual, intentional)
cd tools/ && python sync_local_to_remote.py
```
