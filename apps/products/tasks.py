from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.transactions.services.pending_inventory_processor import process_line_item_pending as process_pending_inventory
from apps.products.services.inventory_reservations import release_expired

logger = logging.getLogger('inventory')

# =============================================================================
# Adaptive Delay Configuration
# =============================================================================
# These can be overridden in Django settings

INVENTORY_CLEAR_BASE_DELAY = getattr(settings, 'INVENTORY_CLEAR_BASE_DELAY', 5)
INVENTORY_CLEAR_MAX_DELAY = getattr(settings, 'INVENTORY_CLEAR_MAX_DELAY', 120)
INVENTORY_CLEAR_DELAY_INCREMENT = getattr(settings, 'INVENTORY_CLEAR_DELAY_INCREMENT', 5)
INVENTORY_CLEAR_IDLE_CYCLES = getattr(settings, 'INVENTORY_CLEAR_IDLE_CYCLES', 5)
INVENTORY_CLEAR_STALE_TIMEOUT = getattr(settings, 'INVENTORY_CLEAR_STALE_TIMEOUT', 300)  # 5 minutes

# Cache keys for adaptive state
CACHE_KEY_DELAY = 'inventory_clear_current_delay'
CACHE_KEY_IDLE = 'inventory_clear_idle_count'
CACHE_KEY_LAST_PROCESS = 'inventory_clear_last_process_time'


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


# =============================================================================
# Adaptive Inventory Processing
# =============================================================================

def get_adaptive_state() -> Dict[str, Any]:
    """Get the current adaptive delay state from cache."""
    return {
        'current_delay': cache.get(CACHE_KEY_DELAY, INVENTORY_CLEAR_BASE_DELAY),
        'idle_count': cache.get(CACHE_KEY_IDLE, 0),
        'last_process_time': cache.get(CACHE_KEY_LAST_PROCESS),
    }


def set_adaptive_state(current_delay: int, idle_count: int, last_process_time: Optional[float] = None):
    """Save the adaptive delay state to cache."""
    cache.set(CACHE_KEY_DELAY, current_delay, timeout=3600)
    cache.set(CACHE_KEY_IDLE, idle_count, timeout=3600)
    if last_process_time:
        cache.set(CACHE_KEY_LAST_PROCESS, last_process_time, timeout=3600)


def reset_adaptive_state():
    """Reset adaptive delay to base (for testing or manual intervention)."""
    set_adaptive_state(INVENTORY_CLEAR_BASE_DELAY, 0, timezone.now().timestamp())
    logger.info(f"[INVENTORY] Adaptive state reset to base delay {INVENTORY_CLEAR_BASE_DELAY}s")


def check_stale_inventory_records() -> Dict[str, Any]:
    """
    Check for and alert on stale pending inventory records.
    
    Returns dict with stale record info for logging/alerting.
    """
    from apps.core.models import Pending
    
    timeout_seconds = INVENTORY_CLEAR_STALE_TIMEOUT
    cutoff_ts = int((timezone.now() - timedelta(seconds=timeout_seconds)).timestamp() * 1000)
    
    # Find stale records (not yet processed, older than timeout)
    # Note: Pending model stores extra info in 'data' JSONField, not 'metadata'
    stale_qs = Pending.objects.filter(
        purpose__startswith='inventory_',
        dt_processed=0,
        dt_created__lt=cutoff_ts
    )
    
    # Exclude records that have already been alerted (check in data field)
    # We'll filter in Python since data is a JSONField
    stale_records = []
    for record in stale_qs[:100]:  # Limit to prevent huge queries
        data = record.config or {}
        if not data.get('stale_alert_sent'):
            stale_records.append(record)
            if len(stale_records) >= 10:
                break  # Enough for details
    
    stale_count = stale_qs.count()
    
    if not stale_records:
        return {'stale_count': 0}
    
    # Get details for alerting
    details = []
    for record in stale_records:
        data = record.config or {}
        age_seconds = (timezone.now().timestamp() * 1000 - record.dt_created) / 1000
        details.append({
            'pending_id': record.pk,
            'item_id': data.get('item_id'),
            'purpose': record.purpose,
            'dt_created': record.dt_created,
            'age_seconds': round(age_seconds, 1),
        })
    
    # Log warning
    logger.warning(
        f"[INVENTORY_STALE] {stale_count} pending records older than {timeout_seconds}s. "
        f"Oldest items: {[d['item_id'] for d in details[:5]]}"
    )
    
    # Send admin notification
    try:
        _notify_inventory_stale_alert(stale_count, details)
    except Exception as e:
        logger.error(f"[INVENTORY_STALE] Failed to send admin alert: {e}")
    
    # Mark records to prevent repeat alerts (store in data JSONField)
    now_iso = timezone.now().isoformat()
    alerted_count = 0
    for record in stale_qs[:100]:
        data = record.config or {}
        if not data.get('stale_alert_sent'):
            data['stale_alert_sent'] = True
            data['stale_alert_time'] = now_iso
            record.config = data
            record.save(update_fields=['config'])
            alerted_count += 1
    
    return {
        'stale_count': stale_count,
        'details': details,
        'alerted': alerted_count,
    }


def _notify_inventory_stale_alert(count: int, details: list):
    """Send alert to admin about stale inventory records."""
    try:
        from apps.core.services.notification_service import send_admin_alert
        send_admin_alert(
            subject='[INVENTORY] Stale Pending Records Detected',
            message=f'{count} inventory records have not been processed in over {INVENTORY_CLEAR_STALE_TIMEOUT} seconds.',
            details=details,
            severity='warning'
        )
    except ImportError:
        # notification_service not available, just log
        logger.warning(f"[INVENTORY_STALE] Admin alert: {count} stale records (notification service unavailable)")
    except Exception as e:
        logger.error(f"[INVENTORY_STALE] Admin alert failed: {e}")


def process_pending_inventory_adaptive(
    limit: int = 200,
    dry_run: bool = False,
    check_stale: bool = True,
) -> Dict[str, Any]:
    """
    Process pending inventory with adaptive delay logic.
    
    This function:
    1. Processes pending inventory records
    2. Adjusts the polling delay based on workload
    3. Checks for stale records that need attention
    
    Returns:
        Dict with processing results and next delay info
    """
    from apps.transactions.services.pending_inventory_processor import process_line_item_pending
    
    # Get current adaptive state
    state = get_adaptive_state()
    current_delay = state['current_delay']
    idle_count = state['idle_count']
    
    # Process pending records
    try:
        result = process_line_item_pending(limit=limit, dry_run=dry_run)
        records_processed = result.get('processed', 0)
    except Exception as e:
        logger.error(f"[INVENTORY] Error processing pending records: {e}")
        records_processed = 0
        result = {'error': str(e)}
    
    # Check for stale records
    stale_info = {}
    if check_stale:
        try:
            stale_info = check_stale_inventory_records()
        except Exception as e:
            logger.error(f"[INVENTORY] Error checking stale records: {e}")
    
    # Adaptive delay logic
    if records_processed > 0:
        # Work done - reset to base delay
        new_delay = INVENTORY_CLEAR_BASE_DELAY
        new_idle_count = 0
        last_process_time = timezone.now().timestamp()
        logger.info(
            f"[INVENTORY] Processed {records_processed} records, "
            f"delay reset to {new_delay}s"
        )
    else:
        # No work - increment idle counter
        new_idle_count = idle_count + 1
        last_process_time = state.get('last_process_time')
        
        if new_idle_count >= INVENTORY_CLEAR_IDLE_CYCLES:
            # Time to back off
            new_delay = min(current_delay + INVENTORY_CLEAR_DELAY_INCREMENT, INVENTORY_CLEAR_MAX_DELAY)
            new_idle_count = 0
            logger.debug(
                f"[INVENTORY] Idle backoff after {INVENTORY_CLEAR_IDLE_CYCLES} cycles, "
                f"delay increased to {new_delay}s"
            )
        else:
            new_delay = current_delay
            logger.debug(
                f"[INVENTORY] No pending records, idle cycle {new_idle_count}/{INVENTORY_CLEAR_IDLE_CYCLES}, "
                f"delay stays at {new_delay}s"
            )
    
    # Save state
    set_adaptive_state(new_delay, new_idle_count, last_process_time)
    
    return {
        'processed': records_processed,
        'result': result,
        'previous_delay': current_delay,
        'next_delay': new_delay,
        'idle_count': new_idle_count,
        'stale_info': stale_info,
    }


# Celery task version (if using Celery)
try:
    from celery import shared_task
    
    @shared_task(bind=True)
    def process_pending_inventory_adaptive_task(self, limit: int = 200):
        """
        Celery task for adaptive inventory processing.

        Beat kicks this every 30 s. The task itself no longer self-reschedules
        to avoid duplicate chains and broken loops when the worker restarts.
        """
        # Let the dispatch helper know the worker is alive
        from apps.products.dispatch_pending import mark_worker_alive
        mark_worker_alive()

        result = process_pending_inventory_adaptive(limit=limit)
        return result
    
except ImportError:
    # Celery not installed - provide a no-op placeholder
    def process_pending_inventory_adaptive_task(limit: int = 200):
        """Celery not available - use management command instead."""
        return process_pending_inventory_adaptive(limit=limit)
