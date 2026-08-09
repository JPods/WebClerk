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
from django.apps import apps
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from .registry import (
    build_celery_beat_schedule,
    run_maintenance_function,
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
        result = run_maintenance_function(
            task_name=task_name,
            limit=limit,
            batch_size=batch_size,
        )
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
        result = run_maintenance_function(
            task_name=task_name,
            limit=limit,
            batch_size=batch_size,
        )
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
        result = run_maintenance_function(
            task_name=task_name,
            limit=limit,
            batch_size=batch_size,
        )
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


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def task_cleanup_metadata_temp(self, limit_per_model: int = 1000):
    """Prune expired metadata.temp snippets from BaseModel-backed records.

    A temp entry must have clear_dt (epoch ms). Entries with clear_dt <= now are removed.
    Invalid temp entries are also removed to prevent unbounded metadata growth.
    """
    task_name = 'cleanup_metadata_temp'
    run = _create_task_run(task_name, self.request.id or '', {'limit_per_model': limit_per_model})

    now_ms = int(timezone.now().timestamp() * 1000)
    scanned_models = 0
    changed_records = 0
    removed_entries = 0
    model_stats: dict[str, dict[str, int]] = {}

    try:
        for model in apps.get_models():
            try:
                if model._meta.abstract:
                    continue
                field_names = {f.name for f in model._meta.get_fields()}
                if 'metadata' not in field_names:
                    continue
                if not hasattr(model, 'clear_expired_temp_entries'):
                    continue

                qs = model.objects.all()
                if 'is_deleted' in field_names:
                    qs = qs.filter(is_deleted=False)
                # Prefer recently touched rows when sampling is limited.
                if 'dt_modified' in field_names:
                    qs = qs.order_by('-dt_modified')
                elif 'id' in field_names:
                    qs = qs.order_by('-id')

                scanned_models += 1
                scanned = 0
                changed = 0
                removed = 0

                for obj in qs.iterator():
                    if scanned >= max(limit_per_model, 1):
                        break
                    scanned += 1
                    try:
                        count = obj.clear_expired_temp_entries(now_ms=now_ms)
                    except Exception:
                        continue
                    if count > 0:
                        obj.save(update_fields=['metadata'])
                        changed += 1
                        removed += count

                changed_records += changed
                removed_entries += removed
                model_stats[f"{model._meta.app_label}.{model.__name__}"] = {
                    'scanned': scanned,
                    'changed': changed,
                    'removed_entries': removed,
                }
            except Exception:
                continue

        result = {
            'status': 'ok',
            'scanned_models': scanned_models,
            'changed_records': changed_records,
            'removed_entries': removed_entries,
            'model_stats': model_stats,
        }
        if run:
            run.complete(result)
        logger.info(
            "metadata.temp cleanup complete: models=%s changed_records=%s removed_entries=%s",
            scanned_models,
            changed_records,
            removed_entries,
        )
        return result
    except Exception as exc:
        logger.error(f"metadata.temp cleanup failed: {exc}")
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
        result = run_maintenance_function(task_name=task_name)
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
@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def task_audit_refs_fk(self, batch_size=200):
    """Nightly audit: detect FK ↔ refs.links mismatches and log them.

    Walks key models, compares FK-based related record sets against
    refs.links arrays, and writes RefsMismatchLog entries for any drift.
    Runs at 3:40 AM UTC via Celery beat.
    """
    from apps.core.models.refs_mismatch_log import RefsMismatchLog
    from apps.orgs.models import OrgBase
    from apps.core.models import Contact
    import logging
    logger = logging.getLogger(__name__)

    # Define FK↔refs pairs to audit: (parent_model, parent_qs, related_model, fk_field, refs_link_key)
    audit_pairs = [
        ('customer', OrgBase.objects.filter(org_type='customer', is_active=True, is_deleted=False),
         'contact', 'customer_id', 'contact'),
        ('vendor', OrgBase.objects.filter(org_type='vendor', is_active=True, is_deleted=False),
         'contact', 'vendor_id', 'contact'),
    ]

    total_checked = 0
    total_mismatches = 0

    for parent_model, parent_qs, related_model, fk_field, refs_key in audit_pairs:
        for parent in parent_qs[:batch_size]:
            total_checked += 1
            # FK-based: find related records via FK
            fk_ids = list(
                Contact.objects.filter(**{fk_field: parent.pk})
                .values_list('pk', flat=True)
            )
            # Refs-based: read from parent.refs.links
            refs = getattr(parent, 'refs', None) or {}
            links = refs.get('links', {})
            refs_entries = links.get(refs_key, [])
            refs_ids = [
                e.get('id') for e in refs_entries
                if isinstance(e, dict) and e.get('id')
            ]

            entry = RefsMismatchLog.log_mismatch(
                parent_model=parent_model,
                parent_id=parent.pk,
                related_model=related_model,
                fk_field=fk_field,
                fk_ids=fk_ids,
                refs_ids=refs_ids,
                caller='task_audit_refs_fk',
            )
            if entry:
                total_mismatches += 1

    logger.info(
        "Refs↔FK audit: %d records checked, %d mismatches logged",
        total_checked, total_mismatches,
    )
    return {'checked': total_checked, 'mismatches': total_mismatches}


@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def task_reconcile_aging(self, batch_size=100):
    """Nightly aging reconciliation — recalculates aging buckets for all orgs.

    Calls reconcile_financials management command logic.
    Runs at 2:40 AM UTC via Celery beat.
    """
    from apps.accounts.services.ledger_balance import update_org_balances
    from apps.orgs.models import OrgBase
    import logging
    logger = logging.getLogger(__name__)

    orgs = OrgBase.objects.filter(is_active=True, is_deleted=False)[:batch_size]
    updated = 0
    errors = 0
    for org in orgs:
        try:
            update_org_balances(org)
            updated += 1
        except Exception as e:
            errors += 1
            logger.warning("Aging update failed for org #%s: %s", org.pk, e)

    logger.info("Aging reconciliation: %d orgs updated, %d errors", updated, errors)
    return {'updated': updated, 'errors': errors}


# Import this in Django settings:
#
#   from apps.scheduler.tasks import CELERY_BEAT_SCHEDULE
#


# ─── Athena integrity verification ──────────────────────────────────────────
@shared_task(bind=True, max_retries=1, default_retry_delay=300)
def task_athena_verify(self):
    """Athena security rounds — verify integrity of all signed assets.

    Reads the Athena manifest (Document ida='athena-manifest'), hashes each
    checkpoint file, compares to signed hash. Mismatches generate immediate
    FAULT files. Clean rounds are batch-logged for nightly synthesis.

    Runs every 4 hours via Celery beat.
    """
    import hashlib
    import json
    import logging
    from pathlib import Path
    from datetime import datetime, timezone as tz

    logger = logging.getLogger('athena')

    try:
        from apps.docs.models import Document
        manifest_doc = Document.objects.filter(
            ida='athena-manifest', is_active=True, is_deleted=False
        ).first()

        if not manifest_doc:
            logger.warning('Athena: no manifest document found (ida=athena-manifest)')
            return {'status': 'skipped', 'reason': 'no manifest'}

        manifest = manifest_doc.config or {}
        checkpoints = manifest.get('checkpoints', [])

        if not checkpoints:
            return {'status': 'skipped', 'reason': 'empty manifest'}

        results = []
        failures = []

        for cp in checkpoints:
            path = cp.get('path')
            expected = cp.get('hash')
            cp_type = cp.get('type', 'unknown')

            if not path or not expected:
                results.append({'path': path, 'status': 'invalid', 'reason': 'missing path or hash'})
                continue

            filepath = Path(path)
            if not filepath.exists():
                entry = {'path': path, 'status': 'MISSING', 'type': cp_type}
                results.append(entry)
                failures.append(entry)
                continue

            actual = hashlib.sha256(filepath.read_bytes()).hexdigest()
            if actual == expected:
                results.append({'path': path, 'status': 'ok', 'type': cp_type})
            else:
                entry = {
                    'path': path,
                    'status': 'TAMPERED',
                    'type': cp_type,
                    'expected': expected[:16] + '...',
                    'actual': actual[:16] + '...',
                }
                results.append(entry)
                failures.append(entry)

        # Update manifest with last check timestamp
        manifest['last_check'] = datetime.now(tz.utc).isoformat()
        manifest['last_result'] = 'FAIL' if failures else 'PASS'
        manifest['check_count'] = manifest.get('check_count', 0) + 1
        manifest_doc.config = manifest
        manifest_doc.save(update_fields=['config'])

        if failures:
            # Immediate FAULT — capacity to defend is uncertain
            _athena_fault(failures)
            logger.error(f'Athena: INTEGRITY FAILURE — {len(failures)} checkpoint(s) failed')
        else:
            logger.info(f'Athena: all {len(checkpoints)} checkpoints verified')

        return {
            'status': 'FAIL' if failures else 'PASS',
            'checked': len(checkpoints),
            'passed': len(checkpoints) - len(failures),
            'failed': len(failures),
            'failures': failures,
        }

    except Exception as e:
        logger.error(f'Athena: verification error — {e}')
        return {'status': 'error', 'reason': str(e)}


def _athena_fault(failures):
    """Write immediate FAULT file for integrity failures."""
    from pathlib import Path
    from datetime import datetime, timezone as tz

    ts = datetime.now(tz.utc)
    ts_str = ts.strftime('%Y-%m-%dT%H:%M:%SZ')
    ts_file = ts.strftime('%Y%m%dT%H%M%S')

    # Try Allie inbox first, fall back to local
    allie_inbox = Path.home() / 'Allie' / 'process' / 'inbox'
    local_inbox = Path('/var/log/athena/faults')
    inbox = allie_inbox if allie_inbox.exists() else local_inbox
    inbox.mkdir(parents=True, exist_ok=True)

    details = '\n'.join(
        f"  - {f['path']}: {f['status']}" + (f" (expected {f.get('expected')}, got {f.get('actual')})" if f.get('actual') else '')
        for f in failures
    )

    fault_text = (
        f"# FAULT — {ts_str}\n\n"
        f"system:      SYS\n"
        f"detected_by: Athena\n"
        f"fault:       Integrity check failed — {len(failures)} file(s) tampered or missing\n"
        f"context:     Athena periodic verification\n"
        f"details:\n{details}\n"
        f"resolved_at: \n"
    )

    path = inbox / f'{ts_file}-fault.md'
    path.write_text(fault_text)


# ── Alice: Pending Record Archive & Analysis ─────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def task_archive_pending(self, batch_size=1000):
    """Archive processed pending records to external dated storage.

    Nightly task. Extracts applied/canceled/processed pending records
    from PendingInventoryAdjustment, PendingPaymentApplication, and
    generic Pending. Writes to .local/dated_outside/ as JSONL.gz files
    organized by type/category/month. Deletes from operational DB.
    """
    task_name = 'archive_pending'
    run = _create_task_run(task_name, self.request.id or '', {'batch_size': batch_size})
    try:
        from apps.support.services.pending_archive import archive_processed_pending
        result = archive_processed_pending(batch_size=batch_size)
        logger.info("Archive pending complete: %s total records", result.get('total_archived', 0))
        if run:
            run.complete(result)
        return result
    except Exception as exc:
        logger.error("Archive pending failed: %s", exc)
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def task_pending_patterns(self):
    """Analyze inventory pending archives for trend, cycle, and volatility.

    Weekly task. Runs pattern analysis across all archived product classes.
    Results feed ItemUsage metrics and Alice's coaching signals.
    """
    task_name = 'pending_patterns'
    run = _create_task_run(task_name, self.request.id or '', {})
    try:
        from apps.support.services.pending_analysis import (
            list_archived_categories,
            compute_demand_trend,
            detect_seasonal_cycle,
            compute_volatility,
            flag_pattern_changes,
        )
        categories = list_archived_categories('inventory')
        results = []
        coaching_flags = []

        for cat in categories:
            if cat.startswith('_'):
                continue
            trend = compute_demand_trend(cat, months=12)
            cycle = detect_seasonal_cycle(cat, min_months=12)
            vol = compute_volatility(cat, months=12)
            pattern = flag_pattern_changes(cat)

            results.append({
                'product_class': cat,
                'trend_direction': trend.get('direction'),
                'trend_slope': trend.get('slope'),
                'has_seasonal_pattern': cycle.get('has_pattern'),
                'seasonality_index': cycle.get('seasonality_index'),
                'volatility_band': vol.get('band'),
                'cv': vol.get('cv'),
                'band_shifted': pattern.get('band_shifted'),
            })

            if pattern.get('coaching_signal'):
                coaching_flags.append({
                    'product_class': cat,
                    'from_band': pattern.get('historical_band'),
                    'to_band': pattern.get('recent_band'),
                })

        summary = {
            'categories_analyzed': len(results),
            'coaching_flags': len(coaching_flags),
            'results': results,
            'coaching': coaching_flags,
        }

        logger.info(
            "Pending patterns complete: %d categories, %d coaching flags",
            len(results), len(coaching_flags),
        )
        if run:
            run.complete(summary)
        return summary
    except Exception as exc:
        logger.error("Pending patterns failed: %s", exc)
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def task_cash_flow_patterns(self):
    """Analyze cash flow pending archives for seasonality and process health.

    Weekly task. Runs cash flow analysis across all archived payment categories.
    Reveals revenue concentration, payment timing, and collection effectiveness.
    """
    task_name = 'cash_flow_patterns'
    run = _create_task_run(task_name, self.request.id or '', {})
    try:
        from apps.support.services.pending_analysis import (
            list_archived_categories,
            compute_cash_flow_seasonality,
            compute_conversion_rates,
            compute_processing_latency,
        )
        categories = list_archived_categories('cash_flow')
        results = []

        for cat in categories:
            if cat.startswith('_'):
                continue
            seasonality = compute_cash_flow_seasonality(cat, months=24)
            conversion = compute_conversion_rates('cash_flow', cat, months=6)
            latency = compute_processing_latency('cash_flow', cat, months=6)

            results.append({
                'category': cat,
                'concentration_pct': seasonality.get('concentration_pct'),
                'quarter_distribution': seasonality.get('quarter_distribution'),
                'peak_months': seasonality.get('peak_months'),
                'conversion_rate': conversion.get('conversion_rate'),
                'avg_processing_ms': latency.get('avg_ms'),
                'latency_trend': latency.get('trend_direction'),
            })

        summary = {
            'categories_analyzed': len(results),
            'results': results,
        }

        logger.info("Cash flow patterns complete: %d categories", len(results))
        if run:
            run.complete(summary)
        return summary
    except Exception as exc:
        logger.error("Cash flow patterns failed: %s", exc)
        if run:
            run.fail(str(exc), traceback.format_exc())
        self.retry(exc=exc)


CELERY_BEAT_SCHEDULE = build_celery_beat_schedule()
