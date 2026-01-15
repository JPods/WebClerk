# Celery + Redis Setup

This document covers the complete Celery setup for WebClerk3, including installation, configuration, and operation.

## Overview

WebClerk3 uses Celery with Redis for:
- **Background tasks**: Database maintenance, data exports, keyword indexing
- **Scheduled tasks**: Daily/weekly maintenance via Celery Beat
- **Task tracking**: Execution history stored in `apps.scheduler` models

---

## Installation

### 1. Install Dependencies

```bash
pip install celery redis
```

Add to `requirements.txt`:
```
celery>=5.3.0
redis>=5.0.0
```

### 2. Install Redis

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

**Verify Redis:**
```bash
redis-cli ping
# Should return: PONG
```

---

## Django Configuration

### 3. Create Celery App

Create `webclerk3_api/celery.py`:

```python
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

app = Celery('webclerk3_api')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

### 4. Update Project __init__.py

Edit `webclerk3_api/__init__.py`:

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 5. Django Settings

Add to `webclerk3_api/settings.py`:

```python
# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

# Broker (Redis)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Timezone
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task tracking
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # Soft limit for graceful shutdown

# Result expiration
CELERY_RESULT_EXPIRES = 60 * 60 * 24  # 24 hours

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Fair task distribution
CELERY_WORKER_CONCURRENCY = 4  # Adjust based on server

# Beat schedule (from scheduler app)
from apps.scheduler.tasks import CELERY_BEAT_SCHEDULE
```

---

## Running Celery

### Development

**Start Redis:**
```bash
redis-server
# Or if using Homebrew:
brew services start redis
```

**Start Celery Worker:**
```bash
cd /path/to/webClerk3
source bin/activate
celery -A webclerk3_api worker -l info
```

**Start Celery Beat (scheduler):**
```bash
celery -A webclerk3_api beat -l info
```

**Combined (worker + beat):**
```bash
celery -A webclerk3_api worker -l info -B
```

### Production

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
    --loglevel=info \
    --concurrency=4 \
    --pidfile=/var/run/celery/worker.pid \
    --logfile=/var/log/celery/worker.log \
    --detach
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
    --loglevel=info \
    --pidfile=/var/run/celery/beat.pid \
    --logfile=/var/log/celery/beat.log
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

---

## Task Management

### Scheduler App (`apps.scheduler`)

All scheduled tasks are managed through Django models:

| Model | Purpose |
|-------|---------|
| `ScheduledTask` | Task definition, frequency, status |
| `TaskRun` | Execution history, results, errors |
| `TaskConfig` | Configurable parameters (limits, filters) |

**Admin URL:** `/admin/scheduler/`

### Defined Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| `task_refresh_keywords` | Every 15 min | Update search keywords |
| `task_recompute_relationship_counts` | Hourly | Sync relationship counts |
| `task_ensure_model_defaults` | Daily 2 AM | Fill missing JSONB defaults |
| `task_export_data` | Daily 3 AM | Backup to JSON files |
| `task_refresh_model_registry_docs` | Daily 5 AM | Regenerate docs |
| `task_recompute_basic_stats` | Weekly Sun 4 AM | Normalize stats containers |

### Manual Task Execution

**Via Django Shell:**
```python
from apps.scheduler.tasks import task_ensure_model_defaults

# Async (queued to Celery)
result = task_ensure_model_defaults.delay()
print(result.get(timeout=300))

# With arguments
result = task_ensure_model_defaults.delay(app='orgs')
```

**Via Services (synchronous):**
```python
from apps.scheduler.services import run_task_now

result = run_task_now('ensure_model_defaults', limit=100)
```

**Via Management Command:**
```bash
python manage.py ensure_model_defaults --dry-run
```

### Task Configuration via Admin

1. Navigate to `/admin/scheduler/scheduledtask/`
2. Click on a task
3. Adjust **TaskConfig** inline:
   - `limit`: Max records per run
   - `batch_size`: DB batch size
   - `app_filter`: Restrict to app
   - `model_filter`: Restrict to model
   - `dry_run`: Preview mode

---

## Monitoring

### Verify Tasks Registered

```bash
celery -A webclerk3_api inspect registered
```

### Check Active Tasks

```bash
celery -A webclerk3_api inspect active
```

### View Task History

**Django Admin:** `/admin/scheduler/taskrun/`

**Django Shell:**
```python
from apps.scheduler.models import TaskRun

# Recent runs
TaskRun.objects.order_by('-started_at')[:10]

# Failed runs
TaskRun.objects.filter(status='error')
```

### Flower Web UI (Optional)

```bash
pip install flower
celery -A webclerk3_api flower --port=5555
```

Visit: `http://localhost:5555`

### Logging

Configure in `settings.py`:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/webclerk3/celery.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'celery': {
            'handlers': ['celery_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.scheduler': {
            'handlers': ['celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## Troubleshooting

### Task Not Running

1. **Check Redis:** `redis-cli ping`
2. **Check Worker:** `celery -A webclerk3_api inspect ping`
3. **Check Beat:** Look for beat log output
4. **Verify registration:** `celery -A webclerk3_api inspect registered`

### Task Timing Out

1. Reduce `limit` in TaskConfig
2. Increase `CELERY_TASK_TIME_LIMIT`
3. Check for database locks: `SELECT * FROM pg_locks`

### High Memory Usage

1. Reduce `batch_size` in TaskConfig
2. Ensure tasks use `.iterator()` for large querysets
3. Use `.only()` to limit loaded fields

### Redis Connection Issues

```bash
# Check Redis status
redis-cli info

# Check connections
redis-cli client list

# Clear Redis (development only!)
redis-cli FLUSHALL
```

### Worker Not Picking Up Tasks

```bash
# Purge pending tasks (careful!)
celery -A webclerk3_api purge

# Restart worker
sudo systemctl restart celery-worker
```

---

## Adding New Tasks

1. **Create task function** in `apps/scheduler/tasks.py`:

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_my_new_task(self, limit=1000):
    task_name = 'my_new_task'
    config = _get_task_config(task_name)
    limit = config.get('limit', limit)
    
    run = _create_task_run(task_name, self.request.id or '', {'limit': limit})
    
    try:
        logger.info(f"Starting my_new_task (limit={limit})")
        # ... task logic ...
        result = {'processed': 100, 'updated': 10}
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"my_new_task failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)
```

2. **Add to CELERY_BEAT_SCHEDULE** in `apps/scheduler/tasks.py`:

```python
'my-new-task-daily': {
    'task': 'apps.scheduler.tasks.task_my_new_task',
    'schedule': crontab(hour=6, minute=0),
    'kwargs': {'limit': 1000},
},
```

3. **Register in services.py** (for admin seeding):

```python
# In get_or_create_scheduled_tasks()
'my_new_task': {
    'task_path': 'apps.scheduler.tasks.task_my_new_task',
    'description': 'Description of what it does',
    'frequency': ScheduledTask.Frequency.DAILY,
    'run_at_hour': 6,
},
```

4. **Seed the task:**

```bash
python manage.py shell -c "from apps.scheduler.services import get_or_create_scheduled_tasks; print(get_or_create_scheduled_tasks())"
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Redis results backend |

**Production example:**
```bash
export CELERY_BROKER_URL=redis://redis.internal:6379/1
export CELERY_RESULT_BACKEND=redis://redis.internal:6379/1
```

---

## Related Documentation

- [Background Maintenance](background-maintenance.md) - Task-specific details
- [Cache Service](cache-service.md) - In-memory caching strategy
