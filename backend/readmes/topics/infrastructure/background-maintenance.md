# Background Database Maintenance

This document covers background maintenance tasks that keep the database healthy, consistent, and up-to-date.

> **Celery Setup**: See [celery.md](celery.md) for installation, configuration, and running Celery workers.

## Architecture

All scheduled tasks are managed through the **`apps.scheduler`** Django app:

```
apps/scheduler/
    models.py      # ScheduledTask, TaskRun, TaskConfig
    tasks.py       # Celery shared_tasks + CELERY_BEAT_SCHEDULE
    admin.py       # Django admin for monitoring
    services.py    # Utility functions for manual runs
```

## Philosophy

1. **Non-blocking**: Maintenance tasks should not block user operations
2. **Idempotent**: Tasks can safely run multiple times without side effects
3. **Batched**: Process records in chunks to avoid memory issues and long locks
4. **Observable**: Return metrics (processed, updated, duration) for monitoring
5. **Configurable**: Task parameters adjustable via admin without code changes

---

## Management Commands

These commands can be run manually or wrapped as Celery tasks:

### ensure_model_defaults

Ensures all model records have proper default structures in their JSONB envelope fields.

```bash
# Dry run - see what would change
python manage.py ensure_model_defaults --dry-run

# Apply changes
python manage.py ensure_model_defaults

# Process specific app
python manage.py ensure_model_defaults --app=orgs

# Process specific model
python manage.py ensure_model_defaults --model=orgs.OrgBase
```

**What it does:**
- Scans all models with JSON envelope fields (metadata, refs, prefs, comments, actions, etc.)
- Deep-merges missing default keys without overwriting existing data
- Respects model-specific defaults defined in `get_field_default()` methods

**When to run:**
- After schema changes that add new envelope fields
- After migrations that introduce new default structures
- Weekly maintenance to catch any drift

### export_data

Exports all model data to JSON files for backup.

```bash
python manage.py export_data
```

**Output location:** `/Users/williamjames/Documents/CommerceExpert/webclerk3_data/`

**When to run:**
- Before major migrations
- Daily backup schedule
- Before running destructive maintenance

### Other Maintenance Commands

| Command | Purpose |
|---------|---------|
| `denormalize_links` | Rebuild denormalized relationship data |
| `fill_dt_fields` | Populate missing datetime fields |
| `update_attention` | Recalculate attention flags on records |
| `populate_cache` | Pre-warm frequently accessed data |
| `align_action_contacts` | Sync action contact references |
| `org_financial_maintenance --mode daily` | Daily org financial scrub + pending drain + Alice health_check log |

### org_financial_maintenance (daily)

```bash
python manage.py org_financial_maintenance --mode daily --activity-hours 24
```

This is the recommended daily financial-integrity command for org records. It performs:

- org financial scrub/reconciliation
- pending locked-org update processing
- recent transaction activity summary
- `alice_log` observation creation for unusual conditions

---

## Task Functions (common/tasks.py)

These functions are ready to be wrapped as Celery shared tasks:

### refresh_keywords_task

Refreshes search keywords for records with pending updates.

```python
from common.tasks import refresh_keywords_task

# Direct call
result = refresh_keywords_task(limit=500, batch_size=200)
# Returns: {'processed': 127, 'duration': 2.34}
```

**Parameters:**
- `limit`: Maximum records to process per invocation (default: 500)
- `batch_size`: Records per database batch (default: 200)

### recompute_relationship_counts

Updates denormalized relationship counts (parents, children, linked).

```python
from common.tasks import recompute_relationship_counts

result = recompute_relationship_counts(limit=5000, batch_size=500)
# Returns: {'processed': 1200, 'updated': 45, 'duration': 5.67}
```

### recompute_basic_stats

Ensures StatsMixin records have proper container structure.

```python
from common.tasks import recompute_basic_stats

result = recompute_basic_stats(limit=5000, batch_size=500)
# Returns: {'processed': 3000, 'normalized': 12, 'duration': 8.91}
```

### refresh_model_registry_docs

Regenerates model registry documentation files.

```python
from common.tasks import refresh_model_registry_docs

result = refresh_model_registry_docs()
# Returns: {'gen_model_registry_readme': {...}, 'gen_docs_index': {...}}
```

---

## Celery Integration

### Wrapping as Celery Tasks

Tasks are defined in `apps/scheduler/tasks.py` and automatically record execution history to `TaskRun` model.

```python
from apps.scheduler.tasks import task_ensure_model_defaults

# Async execution via Celery
result = task_ensure_model_defaults.delay()
print(result.get(timeout=300))

# Sync execution for testing
from apps.scheduler.services import run_task_now
result = run_task_now('ensure_model_defaults', limit=100)
```

### Task Configuration via Admin

Each task can be configured through Django admin:

1. **ScheduledTask** - Enable/disable, set frequency
2. **TaskConfig** - Adjust limits, filters, dry_run mode
3. **TaskRun** - View execution history and errors

### Celery Beat Schedule

Import in Django settings:

```python
from apps.scheduler.tasks import CELERY_BEAT_SCHEDULE
```

---

## Adding New Maintenance Tasks

1. **Create the function** in `common/tasks.py`:
   - Accept `limit` and `batch_size` parameters
   - Use `.iterator()` for memory efficiency
   - Return metrics dictionary

2. **Add management command** (optional) in `apps/core/management/commands/`:
   - Useful for manual runs and debugging
   - Add `--dry-run` flag for safety

3. **Wrap as Celery task** in `apps/scheduler/tasks.py`:
   - Use `@shared_task(bind=True)` for retries
   - Handle exceptions with retry logic
   - See [celery.md](celery.md#adding-new-tasks) for full example

4. **Schedule in Celery Beat**:
   - Choose appropriate frequency
   - Consider database load patterns

5. **Document** in this file

---

## Troubleshooting

> **Full troubleshooting**: See [celery.md](celery.md#troubleshooting)

### Task Not Running

1. Check Celery worker is running: `celery -A webclerk3_api worker -l info`
2. Check Celery beat is running: `celery -A webclerk3_api beat -l info`
3. Verify task is registered: `celery -A webclerk3_api inspect registered`

### Records Not Being Updated

1. Run with `--dry-run` to see what would change
2. Check model's `get_field_default()` method
3. Verify envelope field names match mixin definitions
