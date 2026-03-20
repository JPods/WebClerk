# Maintenance

Action: Centralize maintenance operations and scheduling references in one runbook.
Function: apps.support.scheduler.registry (maintenance callable registry + scheduler metadata + beat schedule builder).
Frequency: Reviewed on every maintenance/task change; used daily for operations.
Process: Define in registry -> expose via task wrapper/command -> schedule via beat -> verify via logs and targeted runs.

## Purpose

This document is the consolidated operational entry point for maintenance in wc3.

It covers:

- What maintenance jobs exist
- Where maintenance and Celery definitions are stored
- How to run jobs manually
- How recurring schedules are defined
- How to add a new maintenance job safely

## Central Storage

Maintenance and scheduler metadata are centralized in:

- apps/support/scheduler/registry.py

That registry is the source of truth for:

- MAINTENANCE_FUNCTIONS: task name -> Python callable
- SCHEDULED_TASK_DEFINITIONS: task metadata used to bootstrap ScheduledTask rows
- build_celery_beat_schedule(): periodic Celery schedule entries

Consumers:

- apps/support/scheduler/tasks.py uses run_maintenance_function(...) and sets CELERY_BEAT_SCHEDULE from build_celery_beat_schedule().
- apps/support/scheduler/services.py uses SCHEDULED_TASK_DEFINITIONS in get_or_create_scheduled_tasks().

## Core Maintenance Jobs

Current scheduler-managed maintenance jobs include:

- refresh_keywords: refresh pending keyword index rows
- recompute_relationship_counts: recompute denormalized relation counters
- recompute_basic_stats: normalize stats containers
- ensure_model_defaults: backfill/normalize JSON envelope defaults
- export_data: daily data export
- refresh_model_registry_docs: regenerate registry docs
- aggregate_user_daily_logs: roll up APILog into daily summaries

Related domain maintenance commands:

- python manage.py contact_communications_maintenance
- python manage.py org_financial_maintenance --mode daily

## Runbook Commands

Use the project venv Python.

Manual maintenance examples:

```bash
cd /Users/williamjames/Documents/CommerceExpert/webClerk3

# Contact communication repair + refs synchronization
/Users/williamjames/Documents/CommerceExpert/webClerk3/bin/python manage.py contact_communications_maintenance --limit 200

# Org financial daily maintenance
/Users/williamjames/Documents/CommerceExpert/webClerk3/bin/python manage.py org_financial_maintenance --mode daily --activity-hours 24
```

Manual scheduler task execution (synchronous):

```python
from apps.support.scheduler.services import run_task_now

run_task_now("refresh_keywords", limit=500, batch_size=200)
run_task_now("recompute_relationship_counts", limit=5000, batch_size=500)
```

## Celery Operation

Worker/beat startup:

```bash
cd /Users/williamjames/Documents/CommerceExpert/webClerk3
./start_celery.sh combined
```

Scheduler schedule source:

- apps/support/scheduler/registry.py -> build_celery_beat_schedule()
- imported in apps/support/scheduler/tasks.py as CELERY_BEAT_SCHEDULE

## Add a New Maintenance Job

1. Add implementation function (usually in common/tasks.py or app service module).
2. Register callable in MAINTENANCE_FUNCTIONS in apps/support/scheduler/registry.py.
3. Add metadata to SCHEDULED_TASK_DEFINITIONS in apps/support/scheduler/registry.py.
4. Add beat entry in build_celery_beat_schedule() when periodic execution is required.
5. Add/adjust wrapper task in apps/support/scheduler/tasks.py if it needs a dedicated task entry.
6. Add tests or dry-run validation path.
7. Run a compile/lint check and one manual run before enabling schedule.

## Legacy Docs

Legacy maintenance docs were consolidated into this runbook and removed.
Use this file as the canonical operations entry point.

## Notes

- Some environments may not have scheduler tables migrated. In that case, scheduler bootstrap should degrade safely and report the missing tables.
- Keyword aggregation fallback now includes scalar text fields + refs.tags, while refs.links labels/values are excluded.
- Keyword stop-word filtering is centralized in common/ignore_fields.py (IGNORE_WORDS). Add low-value labels and abusive/profane tokens there when tuning keyword quality.
