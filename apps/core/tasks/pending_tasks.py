from celery import shared_task
"""
Celery task to process all Pending records that have not yet been processed.

This task queries the Pending model for records where `dt_processed` is 0,
indicating they are unprocessed. For each such record, it performs keyword
processing (implementation not shown) and marks the record as processed by
calling `mark_processed` with a user ID (default is 0; replace with actual
user ID if available).
"""
from apps.core.models.pending import Pending

@shared_task
def process_pending_records():
    pendings = Pending.objects.filter(dt_processed=0)
    for pending in pendings:
        # ...process keywords...
        pending.mark_processed(user_id=0)  # Pass actual user_id if available