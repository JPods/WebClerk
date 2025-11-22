from __future__ import annotations

from apps.products.services.inventory_adjustment_processor import process_pending_inventory
from apps.products.services.inventory_reservations import release_expired


def process_pending_inventory_task(limit: int = 200, dry_run: bool = False):
    """Celery wrapper around process_pending_inventory.

    Schedule via beat for periodic drain of pending adjustments.
    Example beat entry (settings):
        CELERY_BEAT_SCHEDULE = {
            'inventory-pending-drain': {
                'task': 'products.tasks.process_pending_inventory',
                'schedule': 60,  # every minute
                'args': [200, False]
            }
        }
    """
    return process_pending_inventory(limit=limit, dry_run=dry_run)


def expire_inventory_reservations_task(batch: int = 500):
    """Expire stale pending inventory reservations (soft holds)."""
    return release_expired(batch=batch)
