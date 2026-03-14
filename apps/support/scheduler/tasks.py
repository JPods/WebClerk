"""
Celery task wrappers for background database maintenance.

============================================================================
IMPLEMENTATION WITH CELERY + REDIS
============================================================================

1. INSTALL DEPENDENCIES
   ---------------------
   pip install celery redis

   Add to requirements.txt:
       celery>=5.3.0
       redis>=5.0.0

2. CREATE CELERY APP (webclerk3_api/celery.py)
   -------------------------------------------
   import os
   from celery import Celery

   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

   app = Celery('webclerk3_api')
   app.config_from_object('django.conf:settings', namespace='CELERY')
   app.autodiscover_tasks()

3. UPDATE __init__.py (webclerk3_api/__init__.py)
   ----------------------------------------------
   from .celery import app as celery_app
   __all__ = ('celery_app',)

4. DJANGO SETTINGS
   ----------------
   # Redis as broker and result backend
   CELERY_BROKER_URL = 'redis://localhost:6379/0'
   CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

   # Task settings
   CELERY_TASK_SERIALIZER = 'json'
   CELERY_RESULT_SERIALIZER = 'json'
   CELERY_ACCEPT_CONTENT = ['json']
   CELERY_TIMEZONE = 'UTC'
   CELERY_TASK_TRACK_STARTED = True
   CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max

   # Beat schedule (import from this file or define inline)
   from apps.scheduler.tasks import CELERY_BEAT_SCHEDULE

5. START REDIS
   ------------
   # macOS with Homebrew:
   brew services start redis

   # Or run directly:
   redis-server

   # Verify:
   redis-cli ping  # Should return PONG

6. START CELERY WORKER
   --------------------
   # Development (from project root with venv activated):
   celery -A webclerk3_api worker -l info

   # Production (with concurrency):
   celery -A webclerk3_api worker -l info -c 4

7. START CELERY BEAT (scheduler)
   ------------------------------
   # Development:
   celery -A webclerk3_api beat -l info

   # Production (combined worker + beat):
   celery -A webclerk3_api worker -l info -B

8. VERIFY TASKS ARE REGISTERED
   ----------------------------
   celery -A webclerk3_api inspect registered

9. MANUAL TASK INVOCATION (Django shell)
   --------------------------------------
   from apps.scheduler.tasks import task_ensure_model_defaults
   result = task_ensure_model_defaults.delay()
   print(result.get(timeout=300))  # Wait for result

10. MONITORING (optional)
    ----------------------
    # Install Flower for web UI:
    pip install flower
    celery -A webclerk3_api flower --port=5555
    # Visit http://localhost:5555

============================================================================
"""

import traceback
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from common.tasks import (
    refresh_keywords_task,
    recompute_relationship_counts,
    recompute_basic_stats,
    refresh_model_registry_docs,
)

logger = get_task_logger(__name__)


def _get_task_config(task_name: str) -> dict:
    """Load TaskConfig kwargs if available."""
    try:
        from .models import ScheduledTask
        task = ScheduledTask.objects.filter(name=task_name).select_related('config').first()
        if task and hasattr(task, 'config'):
            return task.config.as_kwargs()
    except Exception:
        pass
    return {}


def _create_task_run(task_name: str, celery_task_id: str, kwargs: dict):
    """Create TaskRun record for tracking."""
    try:
        from .models import ScheduledTask, TaskRun
        task = ScheduledTask.objects.filter(name=task_name).first()
        if task:
            run = TaskRun.objects.create(
                task=task,
                celery_task_id=celery_task_id,
                kwargs=kwargs,
                status=TaskRun.Status.RUNNING,
                started_at=timezone.now(),
            )
            return run
    except Exception as e:
        logger.warning(f"Could not create TaskRun: {e}")
    return None


# -----------------------------------------------------------------------------
# Keyword & Search Maintenance
# -----------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_refresh_keywords(self, limit=500, batch_size=200):
    """
    Refresh search keywords for records with pending updates.
    
    Run frequently (every 15 min) to keep search index current.
    """
    task_name = 'refresh_keywords'
    config = _get_task_config(task_name)
    limit = config.get('limit', limit)
    batch_size = config.get('batch_size', batch_size)
    
    run = _create_task_run(task_name, self.request.id or '', {'limit': limit, 'batch_size': batch_size})
    
    try:
        logger.info(f"Starting keyword refresh (limit={limit})")
        result = refresh_keywords_task(limit=limit, batch_size=batch_size)
        logger.info(f"Keyword refresh complete: {result}")
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"Keyword refresh failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


# -----------------------------------------------------------------------------
# Relationship & Stats Maintenance
# -----------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_recompute_relationship_counts(self, limit=5000, batch_size=500):
    """
    Update denormalized relationship counts (parents, children, linked).
    
    Run hourly to keep counts in sync.
    """
    task_name = 'recompute_relationship_counts'
    config = _get_task_config(task_name)
    limit = config.get('limit', limit)
    batch_size = config.get('batch_size', batch_size)
    
    run = _create_task_run(task_name, self.request.id or '', {'limit': limit, 'batch_size': batch_size})
    
    try:
        logger.info(f"Starting relationship count recompute (limit={limit})")
        result = recompute_relationship_counts(limit=limit, batch_size=batch_size)
        logger.info(f"Relationship recompute complete: {result}")
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"Relationship recompute failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_recompute_basic_stats(self, limit=5000, batch_size=500):
    """
    Normalize stats containers on StatsMixin models.
    
    Run weekly to ensure container structure integrity.
    """
    task_name = 'recompute_basic_stats'
    config = _get_task_config(task_name)
    limit = config.get('limit', limit)
    batch_size = config.get('batch_size', batch_size)
    
    run = _create_task_run(task_name, self.request.id or '', {'limit': limit, 'batch_size': batch_size})
    
    try:
        logger.info(f"Starting stats normalization (limit={limit})")
        result = recompute_basic_stats(limit=limit, batch_size=batch_size)
        logger.info(f"Stats normalization complete: {result}")
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"Stats normalization failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


# -----------------------------------------------------------------------------
# Schema & Default Maintenance
# -----------------------------------------------------------------------------

@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def task_ensure_model_defaults(self, app=None, model=None):
    """
    Ensure all JSONB envelope fields have proper default structures.
    
    Run daily to catch any drift. Safe to run multiple times.
    Uses deep merge - never overwrites existing data.
    """
    task_name = 'ensure_model_defaults'
    config = _get_task_config(task_name)
    app = config.get('app', app)
    model = config.get('model', model)
    
    run = _create_task_run(task_name, self.request.id or '', {'app': app, 'model': model})
    
    try:
        logger.info(f"Starting ensure_model_defaults (app={app}, model={model})")
        out = StringIO()
        kwargs = {}
        if app:
            kwargs['app'] = app
        if model:
            kwargs['model'] = model
        call_command('ensure_model_defaults', stdout=out, **kwargs)
        output = out.getvalue()
        logger.info(f"ensure_model_defaults complete:\n{output}")
        result = {'success': True, 'output': output}
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"ensure_model_defaults failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


# -----------------------------------------------------------------------------
# Backup & Documentation
# -----------------------------------------------------------------------------

@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def task_export_data(self):
    """
    Export all model data to JSON backup files.
    
    Run daily for backup. Output: /webclerk3_data/
    """
    task_name = 'export_data'
    run = _create_task_run(task_name, self.request.id or '', {})
    
    try:
        logger.info("Starting data export")
        out = StringIO()
        call_command('export_data', stdout=out)
        output = out.getvalue()
        logger.info(f"Data export complete:\n{output}")
        result = {'success': True, 'output': output}
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"Data export failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def task_refresh_model_registry_docs(self):
    """
    Regenerate model registry README, JSON, and CSV files.
    
    Run daily to keep documentation in sync with schema.
    """
    task_name = 'refresh_model_registry_docs'
    run = _create_task_run(task_name, self.request.id or '', {})
    
    try:
        logger.info("Starting model registry docs refresh")
        result = refresh_model_registry_docs()
        logger.info(f"Model registry docs refresh complete: {result}")
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error(f"Model registry docs refresh failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


# -----------------------------------------------------------------------------
# User Daily Log Aggregation
# -----------------------------------------------------------------------------

def _aggregate_for_date(target_date):
    """
    Crunch APILog rows for *target_date* into UserDailyLog summaries.

    Returns a dict of ``{user_id: UserDailyLog}`` that were created/updated.
    """
    import datetime
    from collections import defaultdict
    from django.db.models import Avg, Count, Max, Q
    from apps.core.models.log import APILog, UserDailyLog

    day_start_ms = int(datetime.datetime.combine(
        target_date, datetime.time.min, tzinfo=datetime.timezone.utc
    ).timestamp() * 1000)
    day_end_ms = int(datetime.datetime.combine(
        target_date + datetime.timedelta(days=1), datetime.time.min,
        tzinfo=datetime.timezone.utc
    ).timestamp() * 1000)

    logs_qs = APILog.objects.filter(
        dt_created__gte=day_start_ms,
        dt_created__lt=day_end_ms,
        user__isnull=False,
    )

    if not logs_qs.exists():
        logger.info(f"No APILog entries for {target_date}")
        return {}

    # Group logs by user
    user_ids = list(logs_qs.values_list('user', flat=True).distinct())
    results = {}

    for uid in user_ids:
        user_logs = logs_qs.filter(user_id=uid)

        # ── Call counts ──────────────────────────────────────────
        total = user_logs.count()
        by_method = dict(
            user_logs.values_list('method')
            .annotate(c=Count('id'))
            .values_list('method', 'c')
        )

        # Parse endpoint category from endpoint path
        by_endpoint = defaultdict(int)
        by_model = defaultdict(int)
        for ep, body in user_logs.values_list('endpoint', 'request_body'):
            # Detect wcapi endpoint type (/wcapi/get/, /wcapi/save/, etc.)
            for key in ('get', 'save', 'query', 'manage', 'delete', 'transaction'):
                if f'/{key}' in (ep or ''):
                    by_endpoint[key] += 1
                    break
            else:
                by_endpoint['other'] += 1
            # Extract model_name from request body or endpoint
            if isinstance(body, dict) and body.get('model_name'):
                by_model[body['model_name']] += 1
            elif 'model_name=' in (ep or ''):
                parts = ep.split('model_name=')
                if len(parts) > 1:
                    mn = parts[1].split('&')[0]
                    by_model[mn] += 1

        by_source = dict(
            user_logs.values_list('source')
            .annotate(c=Count('id'))
            .values_list('source', 'c')
        )

        call_counts = {
            'total': total,
            'by_method': dict(by_method),
            'by_endpoint': dict(by_endpoint),
            'by_model': dict(by_model),
            'by_source': dict(by_source),
        }

        # ── Response summary ─────────────────────────────────────
        success_q = user_logs.filter(status_code__gte=200, status_code__lt=300)
        error_q = user_logs.filter(status_code__gte=400)
        success_count = success_q.count()
        error_count = error_q.count()

        agg = user_logs.aggregate(
            avg_dur=Avg('duration_ms'),
            max_dur=Max('duration_ms'),
        )

        status_codes = dict(
            user_logs.exclude(status_code__isnull=True)
            .values_list('status_code')
            .annotate(c=Count('id'))
            .values_list('status_code', 'c')
        )
        status_codes = {str(k): v for k, v in status_codes.items()}

        # Top 5 slowest
        slowest = list(
            user_logs.exclude(duration_ms__isnull=True)
            .order_by('-duration_ms')
            .values('endpoint', 'duration_ms')[:5]
        )
        slowest_endpoints = [
            {'endpoint': s['endpoint'], 'duration_ms': s['duration_ms']}
            for s in slowest
        ]

        avg_dur = int(agg['avg_dur'] or 0)
        max_dur = int(agg['max_dur'] or 0)

        response_summary = {
            'success_count': success_count,
            'error_count': error_count,
            'error_rate': round(error_count / total, 4) if total else 0,
            'avg_duration_ms': avg_dur,
            'max_duration_ms': max_dur,
            'status_codes': status_codes,
            'slowest_endpoints': slowest_endpoints,
        }

        # ── Error details ────────────────────────────────────────
        error_details = []
        if error_count > 0:
            from django.db.models import Min
            err_groups = (
                error_q
                .values('endpoint', 'status_code')
                .annotate(
                    count=Count('id'),
                    first_at=Min('dt_created'),
                    last_at=Max('dt_created'),
                )
                .order_by('-count')[:10]
            )
            for eg in err_groups:
                sample = (
                    error_q
                    .filter(endpoint=eg['endpoint'], status_code=eg['status_code'])
                    .values_list('error_message', flat=True)
                    .first()
                )
                error_details.append({
                    'endpoint': eg['endpoint'],
                    'status_code': eg['status_code'],
                    'count': eg['count'],
                    'error_message': (sample or '')[:300],
                    'first_at': eg['first_at'],
                    'last_at': eg['last_at'],
                })

        # ── Generate hints ───────────────────────────────────────
        hints = []
        # High error rate
        if total > 10 and error_count / total > 0.1:
            hints.append({
                'level': 'warning',
                'category': 'error_rate',
                'message': f"Error rate is {round(error_count / total * 100, 1)}% — "
                           f"{error_count} of {total} requests failed",
                'count': error_count,
            })
        # Slow endpoints
        slow_count = user_logs.filter(duration_ms__gte=2000).count()
        if slow_count > 0:
            hints.append({
                'level': 'info',
                'category': 'performance',
                'message': f"{slow_count} request(s) over 2 s — consider query optimization or caching",
                'count': slow_count,
            })
        # Repeated validation errors (400s)
        bad_req_count = user_logs.filter(status_code=400).count()
        if bad_req_count >= 3:
            # Find the most common bad-request model
            bad_models = (
                user_logs.filter(status_code=400)
                .values_list('request_body', flat=True)
            )
            model_counts = defaultdict(int)
            for body in bad_models:
                if isinstance(body, dict) and body.get('model_name'):
                    model_counts[body['model_name']] += 1
            top_model = max(model_counts, key=model_counts.get) if model_counts else 'unknown'
            hints.append({
                'level': 'error',
                'category': 'validation',
                'message': f"{bad_req_count} validation errors — most on '{top_model}' model. "
                           f"Check required fields and data types",
                'count': bad_req_count,
            })
        # Server errors
        server_err_count = user_logs.filter(status_code__gte=500).count()
        if server_err_count > 0:
            hints.append({
                'level': 'error',
                'category': 'server_error',
                'message': f"{server_err_count} server error(s) — check application logs for stack traces",
                'count': server_err_count,
            })
        # Rate limiting (429)
        rate_count = user_logs.filter(status_code=429).count()
        if rate_count > 0:
            hints.append({
                'level': 'warning',
                'category': 'rate_limit',
                'message': f"Hit rate limit {rate_count} time(s) — consider batching or throttling requests",
                'count': rate_count,
            })
        # Heavy usage
        if total > 500:
            hints.append({
                'level': 'info',
                'category': 'usage',
                'message': f"{total} API calls today — high volume. "
                           f"Top model: {max(by_model, key=by_model.get) if by_model else 'N/A'}",
                'count': total,
            })

        # ── Upsert UserDailyLog ──────────────────────────────────
        daily_log, created = UserDailyLog.objects.update_or_create(
            user_id=uid,
            log_date=target_date,
            defaults={
                'call_counts': call_counts,
                'response_summary': response_summary,
                'hints': hints,
                'error_details': error_details,
                'total_calls': total,
                'total_errors': error_count,
                'avg_duration_ms': avg_dur,
            },
        )
        results[uid] = daily_log
        action = 'created' if created else 'updated'
        logger.info(f"UserDailyLog {action} for user {uid} on {target_date}: "
                     f"{total} calls, {error_count} errors, {len(hints)} hints")

    return results


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def task_aggregate_user_daily_logs(self, target_date_str=None):
    """
    Aggregate APILog entries into UserDailyLog summaries.

    Runs nightly at 1:30 AM for the previous day.
    Can be called manually with a specific date string (YYYY-MM-DD).
    """
    import datetime

    task_name = 'aggregate_user_daily_logs'
    run = _create_task_run(task_name, self.request.id or '', {
        'target_date': target_date_str,
    })

    try:
        if target_date_str:
            target_date = datetime.date.fromisoformat(target_date_str)
        else:
            target_date = (
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
            ).date()

        logger.info(f"Starting UserDailyLog aggregation for {target_date}")
        results = _aggregate_for_date(target_date)
        summary = {
            'date': str(target_date),
            'users_processed': len(results),
            'user_ids': list(results.keys()),
        }
        logger.info(f"UserDailyLog aggregation complete: {summary}")
        if run:
            run.complete(summary)
        return summary

    except Exception as exc:
        logger.error(f"UserDailyLog aggregation failed: {exc}")
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


# -----------------------------------------------------------------------------
# Celery Beat Schedule
# -----------------------------------------------------------------------------
# Import this in Django settings:
#
#   from apps.scheduler.tasks import CELERY_BEAT_SCHEDULE
#

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # -------------------------------------------------------------------------
    # Frequent tasks (< 1 hour)
    # -------------------------------------------------------------------------
    
    # Every 15 minutes - keep search keywords fresh
    'refresh-keywords-every-15-min': {
        'task': 'apps.scheduler.tasks.task_refresh_keywords',
        'schedule': crontab(minute='*/15'),
        'kwargs': {'limit': 500, 'batch_size': 200},
    },
    
    # -------------------------------------------------------------------------
    # Hourly tasks
    # -------------------------------------------------------------------------
    
    # Every hour at :00 - sync relationship counts
    'recompute-relationship-counts-hourly': {
        'task': 'apps.scheduler.tasks.task_recompute_relationship_counts',
        'schedule': crontab(minute=0),
        'kwargs': {'limit': 5000, 'batch_size': 500},
    },
    
    # -------------------------------------------------------------------------
    # Daily tasks (off-peak hours)
    # -------------------------------------------------------------------------

    # 1:30 AM - aggregate user daily logs from APILog
    'aggregate-user-daily-logs-nightly': {
        'task': 'apps.support.scheduler.tasks.task_aggregate_user_daily_logs',
        'schedule': crontab(hour=1, minute=30),
    },
    
    # 2:00 AM - ensure model defaults
    'ensure-model-defaults-daily': {
        'task': 'apps.scheduler.tasks.task_ensure_model_defaults',
        'schedule': crontab(hour=2, minute=0),
    },

    # 2:20 AM - Alice schema watch assessment
    'alice-schema-watch-nightly': {
        'task': 'apps.ai_assistant.tasks.alice_schema_watch_task',
        'schedule': crontab(hour=2, minute=20),
    },
    
    # 3:00 AM - data backup
    'export-data-backup-daily': {
        'task': 'apps.scheduler.tasks.task_export_data',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # 5:00 AM - refresh documentation
    'refresh-model-registry-docs-daily': {
        'task': 'apps.scheduler.tasks.task_refresh_model_registry_docs',
        'schedule': crontab(hour=5, minute=0),
    },
    
    # -------------------------------------------------------------------------
    # Weekly tasks
    # -------------------------------------------------------------------------
    
    # Sunday 4:00 AM - full stats normalization
    'recompute-basic-stats-weekly': {
        'task': 'apps.scheduler.tasks.task_recompute_basic_stats',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
        'kwargs': {'limit': 50000, 'batch_size': 500},
    },
}
