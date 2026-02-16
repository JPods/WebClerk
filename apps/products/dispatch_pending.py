"""
Dispatch helper for pending inventory processing.

Tries Celery first (only if a worker is actually alive), otherwise
processes inline synchronously. Used by save_view.py and
transaction_save.py after lines are saved.
"""
import logging
import time

from django.core.cache import cache

logger = logging.getLogger('inventory')

# Cache key: tracks whether a Celery worker has been seen recently
_CACHE_KEY_WORKER_ALIVE = 'celery_worker_alive'
_WORKER_CHECK_TTL = 60  # seconds to cache the worker-alive check


def _is_worker_alive() -> bool:
    """
    Return True if a Celery worker has been seen within the last 60 s.

    Uses a Redis cache flag that the worker itself refreshes on every
    task execution, plus an initial probe via inspect().
    """
    cached = cache.get(_CACHE_KEY_WORKER_ALIVE)
    if cached is not None:
        return bool(cached)

    # Probe: try to ping workers (fast, 1 s timeout)
    try:
        from webclerk3_api.celery import app
        inspector = app.control.inspect(timeout=1.0)
        pong = inspector.ping()
        alive = bool(pong)
    except Exception:
        alive = False

    cache.set(_CACHE_KEY_WORKER_ALIVE, alive, timeout=_WORKER_CHECK_TTL)
    return alive


def mark_worker_alive():
    """Called by the task itself to refresh the alive flag."""
    cache.set(_CACHE_KEY_WORKER_ALIVE, True, timeout=_WORKER_CHECK_TTL)


def dispatch_pending_processing(limit: int = 200, caller: str = '') -> dict:
    """
    Process pending inventory records — Celery if worker alive, else inline.

    Returns a dict with 'method' ('celery' | 'inline') and processing info.
    """
    prefix = f"[{caller}] " if caller else ""

    # ── Try Celery dispatch ──────────────────────────────────────────
    if _is_worker_alive():
        try:
            from apps.products.tasks import process_pending_inventory_adaptive_task
            result = process_pending_inventory_adaptive_task.apply_async(
                kwargs={'limit': limit},
                countdown=2,
            )
            logger.info(
                "%sDispatched pending inventory task to Celery "
                "(task_id=%s, countdown=2s)", prefix, result.id,
            )
            return {'method': 'celery', 'task_id': result.id}
        except Exception as exc:
            logger.warning(
                "%sCelery dispatch failed, will process inline: %s",
                prefix, exc,
            )

    # ── Inline fallback ──────────────────────────────────────────────
    try:
        from apps.transactions.services.pending_inventory_processor import (
            process_line_item_pending,
        )
        summary = process_line_item_pending(limit=limit)
        logger.info("%sInline pending processing: %s", prefix, summary)
        return {'method': 'inline', 'summary': summary}
    except Exception as exc:
        logger.warning(
            "%sInline pending processing failed (non-fatal): %s",
            prefix, exc,
        )
        return {'method': 'failed', 'error': str(exc)}
