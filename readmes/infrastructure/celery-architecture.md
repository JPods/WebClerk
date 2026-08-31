# Celery Architecture — WC3 Background Task System

**Created:** 2026-08-09
**Owner:** Alice (library, data quality, health, schema, commerce analytics)

---

## What It Does

Celery is the background engine for everything that doesn't need to happen in the request cycle. Inventory drains, layout saves, search indexing, data quality, file library management, health scoring, backups — all run through Celery with Redis as the broker.

Alice owns the majority of the task load. She runs data quality nightly, commerce analytics weekly, and library management continuously. System tasks (keywords, defaults, backups) run independently.

Flowchart: `readmes/flowcharts/wc3-celery-pipeline.dot`
```bash
dot -Tpdf readmes/flowcharts/wc3-celery-pipeline.dot -o readmes/flowcharts/wc3-celery-pipeline.pdf
```

---

## Infrastructure

| Component | Config | Location |
|-----------|--------|----------|
| Broker | Redis `localhost:6379/0` | `CELERY_BROKER_URL` in settings.py |
| Backend | Redis `localhost:6379/0` | `CELERY_RESULT_BACKEND` in settings.py |
| Celery app | `webclerk3_api` | `webclerk3_api/celery.py` |
| Beat schedule | `CELERY_BEAT_SCHEDULE` | `webclerk3_api/settings.py:913` |
| Scheduler models | `ScheduledTask`, `TaskRun`, `TaskConfig` | `apps/scheduler/` |
| Task time limit | 30 min hard, 25 min soft | `CELERY_TASK_TIME_LIMIT` |
| Serialization | JSON only | `CELERY_TASK_SERIALIZER` |
| Timezone | UTC | Axiom 14 — all datetimes UTC |

### Central Registry

Maintenance and scheduler metadata are centralized in `apps/support/scheduler/registry.py`, which is the source of truth for:

- `MAINTENANCE_FUNCTIONS`: task name → Python callable
- `SCHEDULED_TASK_DEFINITIONS`: task metadata used to bootstrap ScheduledTask rows
- `build_celery_beat_schedule()`: periodic Celery schedule entries

Consumers:
- `apps/support/scheduler/tasks.py` uses `run_maintenance_function(...)` and sets `CELERY_BEAT_SCHEDULE` from `build_celery_beat_schedule()`.
- `apps/support/scheduler/services.py` uses `SCHEDULED_TASK_DEFINITIONS` in `get_or_create_scheduled_tasks()`.

---

## Installation & Setup

### Dependencies

```bash
pip install celery redis
```

Add to `requirements.txt`:
```
celery>=5.3.0
redis>=5.0.0
```

### Redis

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

**Verify:** `redis-cli ping` → `PONG`

### Django Configuration

**Celery app** (`webclerk3_api/celery.py`):
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
app = Celery('webclerk3_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**Project `__init__.py`** (`webclerk3_api/__init__.py`):
```python
from .celery import app as celery_app
__all__ = ('celery_app',)
```

**Settings** (`webclerk3_api/settings.py`):
```python
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_RESULT_EXPIRES = 60 * 60 * 24
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_CONCURRENCY = 4
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Redis results backend |

---

## Running

### Development

```bash
# Combined worker + beat
celery -A webclerk3_api worker -l info -B

# Or use the helper script
cd /Users/williamjames/Documents/CommerceExpert/webClerk3
./start_celery.sh combined
```

### Production (separate services)

```bash
celery -A webclerk3_api worker -l info --concurrency=4
celery -A webclerk3_api beat -l info
```

**Systemd Service for Worker** (`/etc/systemd/system/celery-worker.service`):
```ini
[Unit]
Description=Celery Worker for WebClerk3
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=webclerk
Group=webclerk
WorkingDirectory=/opt/webclerk3
Environment="PATH=/opt/webclerk3/bin"
ExecStart=/opt/webclerk3/bin/celery -A webclerk3_api worker \
    --loglevel=info --concurrency=4 \
    --pidfile=/var/run/celery/worker.pid \
    --logfile=/var/log/celery/worker.log --detach
ExecStop=/bin/kill -TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

**Systemd Service for Beat** (`/etc/systemd/system/celery-beat.service`):
```ini
[Unit]
Description=Celery Beat for WebClerk3
After=network.target redis.service

[Service]
Type=simple
User=webclerk
Group=webclerk
WorkingDirectory=/opt/webclerk3
Environment="PATH=/opt/webclerk3/bin"
ExecStart=/opt/webclerk3/bin/celery -A webclerk3_api beat \
    --loglevel=info --pidfile=/var/run/celery/beat.pid \
    --logfile=/var/log/celery/beat.log
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

---

## Complete Task Registry

### High Frequency (seconds)

| Task | Schedule | Owner | What it does |
|------|----------|-------|-------------|
| `process_pending_inventory_adaptive_task` | Every 30s | System | Drain inventory pending queue; adaptive delay based on workload |
| `apply_pending_layouts_task` | Every 10s | Alice | Apply DataBrowser layout saves to Settings |

### Alice Library Pipeline (seconds/minutes)

| Task | Schedule | Owner | What it does |
|------|----------|-------|-------------|
| `alice_library_scan` | Every 1 min | Alice | Virus scan new uploads; status → scanned or virus_detected |
| `alice_library_thumbnails` | Every 1 min | Alice | Generate 200x200 thumbnails for images/videos |
| `alice_library_transfer` | Async | Alice | Upload verified files to secure cloud library |
| `alice_library_verify` | Every 2 min | Alice | Checksum verify: local == remote; trigger cleanup on match |
| `alice_library_cleanup` | Async | Alice | Delete local copy after verified transfer; status → archived |
| `alice_library_monitor` | Every 5 min | Alice | Find stuck transfers (> 2 hours); retry or write FAULT |
| `alice_library_dedup` | Every 5 min | Alice | Catch duplicates that slipped past upload-time check |

### Periodic (minutes/hours)

| Task | Schedule | Owner | What it does |
|------|----------|-------|-------------|
| `task_refresh_keywords` | Every 15 min | System | Update search keywords (FTS); limit=500, batch=200 |
| `task_recompute_relationship_counts` | Hourly | System | Sync relationship count denorm fields; limit=5000 |
| `task_athena_verify` | Every 4 hours | Athena | Integrity verification — sign and verify protected files |

### Nightly (1:30 AM - 5:00 AM UTC)

| Task | Time | Owner | What it does |
|------|------|-------|-------------|
| `task_aggregate_user_daily_logs` | 1:30 AM | System | Aggregate user activity into daily summary records |
| `task_ensure_model_defaults` | 2:00 AM | System | Fill missing JSONB envelope defaults across all models |
| `alice_schema_watch_task` | 2:20 AM | Alice | Detect schema changes; flag to WC_HQ for quarterly review |
| `health_scoring_task` | 2:30 AM | Alice | Score record health across all models |
| `task_reconcile_aging` | 2:40 AM | System | Reconcile AR/AP aging buckets; batch=500 |
| `task_export_data` | 3:00 AM | System | Backup data to JSON export files |
| `data_cleanup_task` | 3:10 AM | Alice | Clean stale data, orphaned records |
| `task_cleanup_metadata_temp` | 3:20 AM | System | Remove temporary metadata entries; limit=1000/model |
| `json_optimize_task` | 3:30 AM | Alice | Optimize JSONB field storage; remove nulls, compact |
| `task_audit_refs_fk` | 3:40 AM | System | Audit refs-FK mismatches; batch=500 |
| `relationship_scan_task` | 4:00 AM | Alice | Discover and strengthen model relationships |
| `task_refresh_model_registry_docs` | 5:00 AM | System | Regenerate model registry documentation |

Each task is staggered by 10-20 minutes to avoid resource contention. The window is 1:30 AM - 5:00 AM UTC — 3.5 hours for all nightly work. Tasks that run longer than expected hit the 25-minute soft limit (graceful shutdown) or 30-minute hard limit (kill).

### Weekly

| Task | Schedule | Owner | What it does |
|------|----------|-------|-------------|
| `task_recompute_basic_stats` | Sun 4:00 AM | System | Normalize stats containers; limit=50000 |
| `schema_drift_task` | Mon 4:30 AM | Alice | Detect schema drift between installations |
| `margin_tracking_task` | Mon 5:00 AM | Alice | Track margin trends per item/category |
| `velocity_task` | Mon 5:30 AM | Alice | Inventory velocity analysis (margin x turns / carry cost) |
| `layout_drift_task` | Mon 6:00 AM | Alice | Detect layout divergence across users |

---

## Nightly Timeline

```
1:30 AM --- User daily logs
2:00 AM --- Model defaults
2:20 AM --- Alice: Schema watch
2:30 AM --- Alice: Health scoring
2:40 AM --- Aging reconciliation
3:00 AM --- Data backup
3:10 AM --- Alice: Data cleanup
3:20 AM --- Metadata temp cleanup
3:30 AM --- Alice: JSON optimize
3:40 AM --- Refs-FK audit
4:00 AM --- Alice: Relationship scan
5:00 AM --- Registry docs refresh
```

---

## Alice's Domain — Complete Ownership

Alice owns **19 of 29 tasks** (65% of the Celery workload). Her responsibilities span five categories:

### 1. Library Management (7 tasks)
Upload → scan → thumbnail → transfer → verify → cleanup → monitor. Full flow at `readmes/68-document-library.md`.

### 2. Data Quality (4 tasks)
Health scoring, data cleanup, JSON optimization, relationship scanning. Three-tier processing: algorithms → Alice LLM → general LLM. Full spec at `readmes/topics/ai/alice-data-quality.md`.

### 3. Schema Governance (2 tasks)
Schema watch (nightly — detect changes) and schema drift (weekly — compare installations). Changes flagged to WC_HQ for quarterly admin review.

### 4. Commerce Analytics (3 tasks)
Margin tracking, velocity analysis, layout drift. Weekly cadence. Results feed Alice's coaching tips and dashboard reports.

### 5. UI Operations (3 tasks)
Pending layout application (10s), layout drift detection (weekly), apply pending layouts. Keeps DataBrowser responsive.

---

## Maintenance Commands

These commands can be run manually or are wrapped as Celery tasks:

| Command | Purpose |
|---------|---------|
| `ensure_model_defaults [--dry-run] [--app=X] [--model=X]` | Fill missing JSONB envelope defaults |
| `export_data` | Backup all model data to JSON files |
| `denormalize_links` | Rebuild denormalized relationship data |
| `fill_dt_fields` | Populate missing datetime fields |
| `update_attention` | Recalculate attention flags on records |
| `populate_cache` | Pre-warm frequently accessed data |
| `align_action_contacts` | Sync action contact references |
| `contact_communications_maintenance --limit 200` | Contact communication repair + refs sync |
| `org_financial_maintenance --mode daily --activity-hours 24` | Daily org financial scrub + pending drain + Alice health_check log |

### Task Functions (common/tasks.py)

| Function | Purpose | Default Params |
|----------|---------|----------------|
| `refresh_keywords_task` | Refresh pending keyword index rows | limit=500, batch_size=200 |
| `recompute_relationship_counts` | Update denormalized relationship counts | limit=5000, batch_size=500 |
| `recompute_basic_stats` | Normalize StatsMixin container structure | limit=5000, batch_size=500 |
| `refresh_model_registry_docs` | Regenerate model registry documentation | — |

---

## Task Architecture

### How Tasks Are Built

All tasks follow the same pattern:

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_name(self, limit=1000):
    config = _get_task_config('task_name')
    limit = config.get('limit', limit)
    run = _create_task_run('task_name', self.request.id or '', {'limit': limit})
    try:
        # ... task logic ...
        result = {'processed': N, 'updated': M}
        if run: run.complete(result)
        return result
    except Exception as exc:
        if run: run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)
```

### Task Configuration

Each task can be configured through `TaskConfig` records in the admin:
- `limit` — max records per run
- `batch_size` — DB batch size
- `app_filter` / `model_filter` — restrict scope
- `dry_run` — preview mode

Admin: `/admin/scheduler/scheduledtask/`

### Task History

Every run creates a `TaskRun` record:
- `started_at`, `completed_at`, `duration`
- `status` — pending, running, complete, error
- `result` — JSON summary
- `error_message`, `traceback` — on failure

Admin: `/admin/scheduler/taskrun/`

### Design Philosophy

1. **Non-blocking**: Maintenance tasks should not block user operations
2. **Idempotent**: Tasks can safely run multiple times without side effects
3. **Batched**: Process records in chunks to avoid memory issues and long locks
4. **Observable**: Return metrics (processed, updated, duration) for monitoring
5. **Configurable**: Task parameters adjustable via admin without code changes

---

## Adding a New Task

1. **Write the task** in the appropriate `tasks.py`:
   - Alice tasks → `apps/ai_assistant/tasks.py`
   - System tasks → `apps/support/scheduler/tasks.py`
   - Library tasks → `apps/docs/tasks.py`
   - Inventory tasks → `apps/products/tasks.py`

2. **Register callable** in `MAINTENANCE_FUNCTIONS` in `apps/support/scheduler/registry.py`

3. **Add metadata** to `SCHEDULED_TASK_DEFINITIONS` in `apps/support/scheduler/registry.py`

4. **Add beat entry** in `build_celery_beat_schedule()` when periodic execution is required

5. **Add/adjust wrapper task** in `apps/support/scheduler/tasks.py` if it needs a dedicated task entry

6. **Seed the task:**
   ```bash
   python manage.py shell -c "from apps.scheduler.services import get_or_create_scheduled_tasks; print(get_or_create_scheduled_tasks())"
   ```

7. **Add tests** or dry-run validation path

---

## Monitoring

```bash
# Verify tasks registered
celery -A webclerk3_api inspect registered

# Check active tasks
celery -A webclerk3_api inspect active

# Flower web UI (optional)
pip install flower
celery -A webclerk3_api flower --port=5555
# → http://localhost:5555
```

### What to Watch

| Signal | What it means |
|--------|-------------|
| Task stuck > 25 min | Soft limit hit — check for DB locks or large datasets |
| Redis memory growing | Results not expiring — check `CELERY_RESULT_EXPIRES` (24h default) |
| `TaskRun` errors clustering | Something systemic — check DB connection, disk space |
| Library monitor writing FAULTs | Cloud transfer failing — check network, credentials, storage |

---

## Troubleshooting

| Problem | Check |
|---------|-------|
| Tasks not running | `redis-cli ping` → `celery inspect ping` → beat logs |
| Task timing out | Reduce `limit` in TaskConfig; check for DB locks |
| High memory | Reduce `batch_size`; use `.iterator()` and `.only()` |
| Redis connection | `redis-cli info` → `redis-cli client list` |
| Worker not picking up | `celery -A webclerk3_api purge` (dev only!) then restart |
| Records not updating | Run with `--dry-run` to see what would change; check model's `get_field_default()` method |

---

## Operational Notes

- Some environments may not have scheduler tables migrated. In that case, scheduler bootstrap should degrade safely and report the missing tables.
- Keyword aggregation fallback now includes scalar text fields + refs.tags, while refs.links labels/values are excluded.
- Keyword stop-word filtering is centralized in `common/ignore_fields.py` (`IGNORE_WORDS`). Add low-value labels and abusive/profane tokens there when tuning keyword quality.

---

## Files

| File | What it is |
|------|-----------|
| `webclerk3_api/celery.py` | Celery app definition |
| `webclerk3_api/settings.py:897-1054` | Full beat schedule + config |
| `apps/support/scheduler/registry.py` | Central maintenance registry (source of truth) |
| `apps/support/scheduler/tasks.py` | System tasks |
| `apps/ai_assistant/tasks.py` | Alice tasks (data quality, schema, analytics, layouts) |
| `apps/docs/tasks.py` | Library management tasks |
| `apps/products/tasks.py` | Inventory pending drain |
| `apps/scheduler/models.py` | ScheduledTask, TaskRun, TaskConfig models |
| `readmes/flowcharts/wc3-celery-pipeline.dot` | Visual pipeline diagram |
| `readmes/68-document-library.md` | Library management detail |
