# Celery & Redis — Background Task Processing

> **Reading order**: [← 08-transaction-save](08-transaction-save.md) | **End of sequence**

---

## Overview

webClerk3 uses **Celery 5.5** with a **Redis** broker to run background tasks.
The most important task is the **pending inventory processor**, which drains
`Pending` records created whenever transaction lines (orders, purchases,
invoices, workorders, proposals) are saved, and applies the quantity deltas
to `Item.data.quantity` buckets (`on_so`, `on_po`, `on_wo`, etc.).

## Architecture

```
┌──────────────┐         ┌───────────┐         ┌──────────────────┐
│  Django View │──push──▶│   Redis   │──pull──▶│  Celery Worker   │
│ (save_view / │  task   │ (broker)  │  task   │  (solo pool)     │
│  txn_save)   │         └───────────┘         │                  │
└──────────────┘                                │ process_pending  │
                                                │ _inventory_      │
        ┌───────────┐                           │ adaptive_task    │
        │  Celery   │──kicks every 30 s────────▶│                  │
        │  Beat     │                           └──────────────────┘
        └───────────┘                                   │
                                                        ▼
                                                ┌──────────────────┐
                                                │  PostgreSQL      │
                                                │  Pending → Item  │
                                                └──────────────────┘
```

**Two paths trigger pending processing:**

1. **On-save dispatch** — After lines are saved, the view calls
   `dispatch_pending_processing()`. In `transaction_save.py` (the
   collect-then-create path), this is a **single call** after all Pending
   records have been created from the collected deltas array. In
   `save_view.py`, it fires after the per-line processing loop. The helper
   checks for a live Celery worker (via `inspector.ping()` with a 60 s
   cache). If a worker is alive, it dispatches via `apply_async()`;
   otherwise it processes inline synchronously — guaranteeing records are
   always drained regardless of Celery's state.

2. **Beat schedule** — Celery Beat kicks the same task every **30 seconds** as
   a safety net. The task does **not** self-reschedule; Beat is the sole
   cycle driver.

---

## File Map

| File | Role |
|------|------|
| `webclerk3_api/celery.py` | Creates the `Celery` app, autodiscovers tasks |
| `webclerk3_api/__init__.py` | Exports `celery_app` so `@shared_task` binds correctly |
| `webclerk3_api/settings.py` (bottom) | `CELERY_*` settings, `CELERY_BEAT_SCHEDULE` |
| `apps/products/tasks.py` | `process_pending_inventory_adaptive_task` — the main inventory task |
| `apps/support/scheduler/tasks.py` | Maintenance tasks (keywords, stats, defaults, backup, docs) |
| `apps/core/models/pending.py` | `Pending` model — ephemeral queue records |
| `apps/transactions/services/pending_inventory_processor.py` | `process_line_item_pending()` — reads Pending, groups by item, applies deltas |
| `apps/transactions/services/line_item_service.py` | Creates Pending records when lines are added/changed/deleted |
| `apps/products/dispatch_pending.py` | Centralized dispatch helper — checks worker liveness, chooses Celery vs inline |
| `apps/core/views/save_view.py` | Generic `/wcapi/save/` endpoint — calls `dispatch_pending_processing()` after lines saved |
| `apps/transactions/services/transaction_save.py` | Transaction-specific save service — calls `dispatch_pending_processing()` after lines saved |
| `start_celery.sh` | Convenience script to start/stop worker and beat |
| `runserver.sh` | Dev server startup — auto-starts Celery worker+beat in background |

---

## Quick Start

### Prerequisites

```bash
# Redis must be running
brew services start redis   # macOS
redis-cli ping              # → PONG

# Python packages (already in venv)
pip install celery redis
```

### Start the Worker

```bash
# From the webClerk3 project root:

# Combined worker + beat (development)
./start_celery.sh combined

# Or separately:
./start_celery.sh worker   # in one terminal
./start_celery.sh beat     # in another

# Stop everything:
./start_celery.sh stop
```

### Verify

```bash
# Check registered tasks
celery -A webclerk3_api inspect registered

# Check active workers
celery -A webclerk3_api inspect active

# Monitor in real time (optional)
pip install flower
celery -A webclerk3_api flower --port=5555
# → http://localhost:5555
```

---

## The Pending Model

```
Pending (apps.core.models)
├── model_name    CharField     e.g. "order_line"
├── record_id     CharField     the line PK
├── purpose       CharField     "inventory_line_add", "inventory_qty_change", "inventory_line_delete"
├── data          JSONField     { "item_id": 243, "on_so": 7, ... }
├── dt_processed  BigIntegerField   0 = unprocessed, else epoch-ms when processed
└── dt_created    (from CoreModel)
```

When a transaction line is created, changed, or deleted, a `Pending` record
is written with the appropriate purpose and delta values in `data`.

**Two creation paths:**
- `/wcapi/transaction/save/` → `_create_pending_from_deltas()` in `transaction_save.py` (collect-then-create, backend-authoritative)
- `/wcapi/save/` → `LineItemService._create_pending_for_new_line()` (per-line)

Both paths set `_pending_created = True` on line instances to prevent the
signal safety net from duplicating.

---

## Pending Inventory Processing Flow

1. `process_line_item_pending(limit=200)` queries `Pending` where
   `purpose IN ('inventory_line_add', 'inventory_qty_change', 'inventory_line_delete')`
   and `dt_processed = 0`.

2. Groups records by `data.item_id`.

3. For each item, aggregates all deltas (`on_so`, `on_po`, `on_wo`, `on_in`,
   `on_r`, `on_p`).

4. Locks the `Item` row with `select_for_update()` and applies the deltas to
   `item.data.quantity`.

5. Marks each `Pending` record as processed (`dt_processed = now`).

**If the item row is locked**, the record is skipped and retried on the next
cycle. If it remains unprocessed for more than 5 minutes (configurable via
`INVENTORY_CLEAR_STALE_TIMEOUT`), an admin alert is sent.

---

## Scheduling

Celery Beat fires `process_pending_inventory_adaptive_task` every **30 seconds**.
The task itself **does not self-reschedule** — Beat is the sole driver. This
avoids duplicate chains and broken loops when the worker restarts.

The adaptive delay settings below are used internally by the processor but
no longer control rescheduling:

| Condition | Behavior |
|-----------|----------|
| Records processed | Delay resets to `BASE_DELAY` (5 s) |
| No records, < IDLE_CYCLES | Stays at current delay |
| No records, idle cycles exhausted | Increases by `DELAY_INCREMENT` (5 s), max `MAX_DELAY` (120 s) |

Settings (overridable in Django settings or env):

| Setting | Default | Description |
|---------|---------|-------------|
| `INVENTORY_CLEAR_BASE_DELAY` | 5 | Seconds between runs when active |
| `INVENTORY_CLEAR_MAX_DELAY` | 120 | Maximum backoff delay |
| `INVENTORY_CLEAR_DELAY_INCREMENT` | 5 | Seconds added per backoff step |
| `INVENTORY_CLEAR_IDLE_CYCLES` | 5 | Idle iterations before increasing delay |
| `INVENTORY_CLEAR_STALE_TIMEOUT` | 300 | Seconds before a record is considered stale |

---

## Beat Schedule

All periodic tasks defined in `settings.CELERY_BEAT_SCHEDULE`:

| Name | Task | Schedule |
|------|------|----------|
| `inventory-pending-drain` | `process_pending_inventory_adaptive_task` | Every 30 s |
| `refresh-keywords-every-15-min` | `task_refresh_keywords` | Every 15 min |
| `recompute-relationship-counts-hourly` | `task_recompute_relationship_counts` | Hourly at :00 |
| `ensure-model-defaults-daily` | `task_ensure_model_defaults` | Daily 2:00 AM |
| `export-data-backup-daily` | `task_export_data` | Daily 3:00 AM |
| `refresh-model-registry-docs-daily` | `task_refresh_model_registry_docs` | Daily 5:00 AM |
| `recompute-basic-stats-weekly` | `task_recompute_basic_stats` | Sunday 4:00 AM |

---

## Django Settings (Celery section)

```python
# webclerk3_api/settings.py

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 1800        # 30 min hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 1500   # 25 min soft limit
```

Both `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` can be overridden via
environment variables or `.env` file.

---

## On-Save Dispatch Pattern

Both `transaction_save.py` and `save_view.py` call a single centralized
helper after lines are saved:

```python
if lines_saved > 0:
    from apps.products.dispatch_pending import dispatch_pending_processing
    dispatch_pending_processing(limit=200, caller='save_view')
```

### How `dispatch_pending_processing()` works

1. **Worker-alive check** — calls `_is_worker_alive()` which probes
   `inspector.ping(timeout=1.0)` and caches the result in Redis for 60 s.
   The task itself calls `mark_worker_alive()` on every execution to refresh
   the cache, so subsequent checks within 60 s skip the probe.

2. **Celery path** — if a worker is alive, dispatches via `apply_async()`
   with a 2 s countdown (so the DB transaction commits first).

3. **Inline fallback** — if no worker is detected (or `apply_async` fails),
   calls `process_line_item_pending(limit)` directly in the request thread.
   This guarantees pending records are always drained, even without Celery.

### Why the old pattern was broken

The original `try: apply_async() / except: inline` pattern failed silently
because `apply_async()` always succeeds as long as Redis is running — it
just pushes a message to the queue. If no worker is consuming the queue,
tasks sit there indefinitely and the `except` inline fallback never fires.
The new approach explicitly checks for a live worker first.

---

## `runserver.sh` Auto-Start

`runserver.sh` now automatically starts a Celery worker+beat process in the
background when the Django dev server launches:

```bash
# From runserver.sh:
start_celery()   # kills old celery, starts worker+beat, logs to logs/celery.log
trap stop_celery EXIT   # stops celery when the dev server exits
```

This means `start_celery.sh` is still available for standalone use, but in
normal development you get Celery automatically.

---

## Troubleshooting

### Worker won't start
```bash
# Verify Redis
redis-cli ping   # expect PONG

# Check for port conflicts
lsof -i :6379

# Start worker with debug logging
celery -A webclerk3_api worker -l debug --concurrency=1 -P solo
```

### Tasks queued but not consumed
```bash
# Check queue length
redis-cli llen celery

# Kill stuck workers and restart
./start_celery.sh stop
./start_celery.sh worker
```

### Pending records accumulating
```bash
# Check unprocessed count
cd /path/to/webClerk3
source bin/activate
DB_MODE=remote python manage.py shell -c "
from apps.core.models import Pending
print(Pending.objects.filter(dt_processed=0, purpose__startswith='inventory_').count())
"

# Force-process manually
DB_MODE=remote python manage.py process_pending_inventory --skip-stacks --limit=500
```

### Inspect task results
```python
# Django shell
from apps.products.tasks import process_pending_inventory_adaptive_task
result = process_pending_inventory_adaptive_task.apply_async(kwargs={'limit': 5})
print(result.get(timeout=15))
```

---

## Management Command (fallback)

If Celery is not running, pending records can be drained manually:

```bash
DB_MODE=remote python manage.py process_pending_inventory --skip-stacks --limit=500
```

The `--skip-stacks` flag is required because the stack adjustment processor
references a field (`dt_created`) that does not exist on the
`PendingInventoryAdjustment` model — a known issue to fix separately.

---

## Related Documentation

- [08-transaction-save.md](08-transaction-save.md) — How pending records are created during transaction saves
- [03-wcapi-gateway.md](03-wcapi-gateway.md) — WCAPI gateway overview
- [04-wcapi-usage.md](04-wcapi-usage.md) — API usage examples