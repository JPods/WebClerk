# Celery & Redis — Background Task Processing

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

1. **On-save dispatch** — After lines are saved in `save_view.py` or
   `transaction_save.py`, the view calls
   `process_pending_inventory_adaptive_task.apply_async(countdown=2)`.
   If Celery is unreachable, it falls back to inline synchronous processing.

2. **Beat schedule** — Celery Beat kicks the same task every 30 seconds as a
   safety net. The task self-reschedules with an adaptive delay that backs off
   when idle.

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
| `apps/core/views/save_view.py` | Generic `/wcapi/save/` endpoint — dispatches Celery task after lines saved |
| `apps/transactions/services/transaction_save.py` | Transaction-specific save service — dispatches Celery task after lines saved |
| `start_celery.sh` | Convenience script to start/stop worker and beat |

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

When a transaction line is created, changed, or deleted, `LineItemService`
writes a `Pending` record with the appropriate purpose and delta values in
`data`.

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

## Adaptive Delay

The `process_pending_inventory_adaptive_task` self-reschedules with an
adaptive countdown:

| Condition | Delay Behavior |
|-----------|---------------|
| Records processed | Reset to `BASE_DELAY` (5 s) |
| No records, < IDLE_CYCLES | Stay at current delay |
| No records, idle cycles exhausted | Increase by `DELAY_INCREMENT` (5 s), max `MAX_DELAY` (120 s) |

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

Both `transaction_save.py` and `save_view.py` use the same pattern after
lines are saved:

```python
if lines_saved > 0:
    try:
        from apps.products.tasks import process_pending_inventory_adaptive_task
        process_pending_inventory_adaptive_task.apply_async(
            kwargs={'limit': 200},
            countdown=2,   # 2 s delay so the DB transaction commits first
        )
    except Exception:
        # Celery unavailable — fall back to inline processing
        from apps.transactions.services.pending_inventory_processor import process_line_item_pending
        process_line_item_pending(limit=200)
```

The 2-second countdown ensures the database transaction has committed before
the worker tries to read the new `Pending` rows.

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
