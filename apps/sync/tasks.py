"""
Celery tasks for the sync app.

Beat schedule (add to settings.py CELERY_BEAT_SCHEDULE):
    'process-pending': {
        'task': 'apps.sync.tasks.process_pending',
        'schedule': 3600,  # hourly
    },
"""

from celery import shared_task
import logging

logger = logging.getLogger("sync.tasks")


@shared_task(name="apps.sync.tasks.process_pending")
def process_pending():
    """Process all Pending records with dt_processed=0.

    Runs hourly via Beat.  Each purpose has a registered handler.
    Handlers stamp dt_processed on success; failures stay pending
    for the next cycle.
    """
    from apps.sync.services.pending_processor import process_all_pending

    processed, failed, skipped = process_all_pending()
    return {
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
    }
