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
    
    # 2:00 AM - ensure model defaults
    'ensure-model-defaults-daily': {
        'task': 'apps.scheduler.tasks.task_ensure_model_defaults',
        'schedule': crontab(hour=2, minute=0),
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
