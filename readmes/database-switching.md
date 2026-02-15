# Switching Between Local and Remote Databases

webClerk3 supports two database modes that can be toggled at any time during development:

| Mode | Host | Purpose |
|------|------|---------|
| **remote** | Shared server (configured in `.env`) | Team collaboration — everyone reads/writes the same data |
| **local** | `localhost` | Isolated debugging — safe to break things without affecting teammates |

The **remote** mode is always the default. Every time `./runserver.sh` starts, it force-resets the mode to `remote` as a safety measure.

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
# ── Switching modes (config only, no data transfer) ──

# Check current mode
./tools/switch-dataset.sh status

# Switch to local (skips data sync)
SKIP_LOCAL_SYNC=1 ./tools/switch-dataset.sh local

# Switch back to remote
./tools/switch-dataset.sh remote

# ── Data sync (independent of which mode is active) ──

# Download: copy remote database into local
cd tools/ && python sync_remote_to_local.py --status-file .sync_status.json

# Upload: copy local database into remote (manual, intentional)
cd tools/ && python sync_local_to_remote.py

# ── Combined: switch to local AND sync in one step ──

# Switch to local with automatic remote→local sync (default behavior)
./tools/switch-dataset.sh local

# Force re-sync while already in local mode
FORCE_LOCAL_SYNC=1 ./tools/switch-dataset.sh local
```
