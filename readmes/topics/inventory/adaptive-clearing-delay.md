# Adaptive Inventory Clearing Delay

## Overview

The inventory clearing system uses an **adaptive delay** strategy to balance responsiveness with resource efficiency. Instead of polling at a fixed interval, the system dynamically adjusts its polling frequency based on workload.

**Implementation Status**: ✅ Implemented

- Task: [apps/products/tasks.py](../../../apps/products/tasks.py)
- Command: [apps/products/management/commands/process_inventory_adaptive.py](../../../apps/products/management/commands/process_inventory_adaptive.py)

## Design Goals

1. **Fast response** when pending records exist (minimize latency)
2. **Resource efficient** when idle (reduce unnecessary polling)
3. **Alerting** for stuck/stale records that fail to clear
4. **Configurable** parameters for different environments (dev vs prod)

---

## Delay Algorithm

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BASE_DELAY` | 5 seconds | Minimum polling interval |
| `MAX_DELAY` | 120 seconds | Maximum polling interval |
| `DELAY_INCREMENT` | 5 seconds | How much to increase delay per idle cycle |
| `IDLE_CYCLES_BEFORE_BACKOFF` | 5 | Consecutive empty cycles before increasing delay |
| `STALE_RECORD_TIMEOUT` | 300 seconds (5 min) | Alert if record unprocessed this long |

### State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                    ADAPTIVE DELAY STATE                      │
├─────────────────────────────────────────────────────────────┤
│  current_delay: int = BASE_DELAY                            │
│  idle_cycle_count: int = 0                                  │
│  last_process_time: datetime = now()                        │
└─────────────────────────────────────────────────────────────┘

On each polling cycle:
  
  1. Query pending inventory records
  
  2. IF records_found > 0:
       - Process records
       - Reset: current_delay = BASE_DELAY
       - Reset: idle_cycle_count = 0
       - Update: last_process_time = now()
  
  3. ELSE (no records found):
       - Increment: idle_cycle_count += 1
       - IF idle_cycle_count >= IDLE_CYCLES_BEFORE_BACKOFF:
           - Increase: current_delay = min(current_delay + DELAY_INCREMENT, MAX_DELAY)
           - Reset: idle_cycle_count = 0
  
  4. Schedule next poll in current_delay seconds
```

### Visual Timeline Example

```
Time   Delay   Records   Action
─────────────────────────────────────────────────────
0s     5s      3         Process → reset to 5s
5s     5s      0         Idle cycle 1/5
10s    5s      0         Idle cycle 2/5
15s    5s      0         Idle cycle 3/5
20s    5s      0         Idle cycle 4/5
25s    5s      0         Idle cycle 5/5 → increase to 10s
35s    10s     0         Idle cycle 1/5
45s    10s     0         Idle cycle 2/5
55s    10s     2         Process → reset to 5s ← IMMEDIATE RESPONSE
60s    5s      0         Idle cycle 1/5
...
```

---

## Stale Record Detection

Records that remain unprocessed for longer than `STALE_RECORD_TIMEOUT` trigger alerts.

### Detection Logic

```python
# On each processing cycle, check for stale records:
stale_records = Pending.objects.filter(
    purpose__in=INVENTORY_PURPOSES,
    dt_processed=0,  # Not yet processed
    dt_created__lt=now() - timedelta(seconds=STALE_RECORD_TIMEOUT)
)

if stale_records.exists():
    # 1. Log warning
    logger.warning(f"[INVENTORY] {stale_records.count()} stale pending records detected")
    
    # 2. Notify administrator
    notify_admin_stale_inventory(stale_records)
    
    # 3. Optionally mark records to prevent repeat alerts
    stale_records.update(metadata__stale_alert_sent=True)
```

### Alert Content

The admin notification should include:
- Count of stale records
- Oldest record age
- Affected item IDs
- Sample of record details (first 5)
- Suggested actions

---

## Configuration

### Django Settings

```python
# settings.py or environment variables

# Inventory Clearing - Adaptive Delay
INVENTORY_CLEAR_BASE_DELAY = int(os.getenv('INVENTORY_CLEAR_BASE_DELAY', 5))
INVENTORY_CLEAR_MAX_DELAY = int(os.getenv('INVENTORY_CLEAR_MAX_DELAY', 120))
INVENTORY_CLEAR_DELAY_INCREMENT = int(os.getenv('INVENTORY_CLEAR_DELAY_INCREMENT', 5))
INVENTORY_CLEAR_IDLE_CYCLES = int(os.getenv('INVENTORY_CLEAR_IDLE_CYCLES', 5))
INVENTORY_CLEAR_STALE_TIMEOUT = int(os.getenv('INVENTORY_CLEAR_STALE_TIMEOUT', 300))

# For development/testing - aggressive polling
if DEBUG:
    INVENTORY_CLEAR_BASE_DELAY = 5
    INVENTORY_CLEAR_MAX_DELAY = 30
```

### Environment Presets

| Environment | BASE | MAX | INCREMENT | IDLE_CYCLES | STALE_TIMEOUT |
|-------------|------|-----|-----------|-------------|---------------|
| Development | 5s   | 30s | 5s        | 3           | 120s          |
| Testing     | 5s   | 60s | 5s        | 5           | 180s          |
| Production  | 10s  | 120s| 10s       | 5           | 300s          |

---

## Implementation

### Option A: Celery Beat with Dynamic Scheduling

```python
# apps/products/tasks.py

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

CACHE_KEY_DELAY = 'inventory_clear_current_delay'
CACHE_KEY_IDLE = 'inventory_clear_idle_count'

@shared_task(bind=True)
def process_pending_inventory_adaptive(self):
    """Process pending inventory with adaptive delay."""
    from apps.transactions.services.pending_inventory_processor import (
        process_line_item_pending
    )
    
    # Get current state from cache
    base_delay = getattr(settings, 'INVENTORY_CLEAR_BASE_DELAY', 5)
    max_delay = getattr(settings, 'INVENTORY_CLEAR_MAX_DELAY', 120)
    increment = getattr(settings, 'INVENTORY_CLEAR_DELAY_INCREMENT', 5)
    idle_threshold = getattr(settings, 'INVENTORY_CLEAR_IDLE_CYCLES', 5)
    
    current_delay = cache.get(CACHE_KEY_DELAY, base_delay)
    idle_count = cache.get(CACHE_KEY_IDLE, 0)
    
    # Process pending records
    result = process_line_item_pending(limit=200)
    records_processed = result.get('processed', 0)
    
    # Check for stale records
    check_stale_inventory_records()
    
    # Adaptive delay logic
    if records_processed > 0:
        # Work done - reset to base delay
        current_delay = base_delay
        idle_count = 0
    else:
        # No work - increment idle counter
        idle_count += 1
        if idle_count >= idle_threshold:
            current_delay = min(current_delay + increment, max_delay)
            idle_count = 0
    
    # Save state
    cache.set(CACHE_KEY_DELAY, current_delay, timeout=3600)
    cache.set(CACHE_KEY_IDLE, idle_count, timeout=3600)
    
    # Schedule next run
    self.apply_async(countdown=current_delay)
    
    return {
        'processed': records_processed,
        'next_delay': current_delay,
        'idle_count': idle_count
    }


def check_stale_inventory_records():
    """Check for and alert on stale pending records."""
    from apps.core.models import Pending
    from django.utils import timezone
    from datetime import timedelta
    import logging
    
    logger = logging.getLogger('inventory')
    timeout = getattr(settings, 'INVENTORY_CLEAR_STALE_TIMEOUT', 300)
    cutoff = timezone.now() - timedelta(seconds=timeout)
    
    stale = Pending.objects.filter(
        purpose__startswith='inventory_',
        dt_processed=0,
        dt_created__lt=int(cutoff.timestamp() * 1000)
    ).exclude(
        metadata__contains={'stale_alert_sent': True}
    )
    
    if stale.exists():
        count = stale.count()
        logger.warning(f"[INVENTORY_STALE] {count} pending records older than {timeout}s")
        
        # Notify admin
        notify_inventory_stale_alert(stale[:10])  # First 10 for details
        
        # Mark to prevent repeat alerts (for 1 hour)
        for record in stale[:100]:
            meta = record.metadata or {}
            meta['stale_alert_sent'] = True
            meta['stale_alert_time'] = timezone.now().isoformat()
            record.metadata = meta
            record.save(update_fields=['metadata'])


def notify_inventory_stale_alert(records):
    """Send alert to admin about stale inventory records."""
    from apps.core.services.notification_service import send_admin_alert
    
    details = []
    for r in records:
        data = r.data or {}
        details.append({
            'pending_id': r.pk,
            'item_id': data.get('item_id'),
            'purpose': r.purpose,
            'created': r.dt_created,
            'age_seconds': (timezone.now().timestamp() * 1000 - r.dt_created) / 1000
        })
    
    send_admin_alert(
        subject='[INVENTORY] Stale Pending Records Detected',
        message=f'{len(records)} inventory records have not been processed in over 5 minutes.',
        details=details,
        severity='warning'
    )
```

### Option B: Management Command with Loop

```python
# apps/products/management/commands/process_inventory_adaptive.py

from django.core.management.base import BaseCommand
from django.conf import settings
import time
import logging

logger = logging.getLogger('inventory')


class Command(BaseCommand):
    help = 'Process pending inventory with adaptive delay'
    
    def add_arguments(self, parser):
        parser.add_argument('--base-delay', type=int, default=5)
        parser.add_argument('--max-delay', type=int, default=120)
        parser.add_argument('--increment', type=int, default=5)
        parser.add_argument('--idle-cycles', type=int, default=5)
        parser.add_argument('--daemon', action='store_true', help='Run continuously')
    
    def handle(self, *args, **options):
        from apps.transactions.services.pending_inventory_processor import (
            process_line_item_pending
        )
        
        base_delay = options['base_delay']
        max_delay = options['max_delay']
        increment = options['increment']
        idle_threshold = options['idle_cycles']
        daemon = options['daemon']
        
        current_delay = base_delay
        idle_count = 0
        
        self.stdout.write(f"Starting adaptive inventory processor")
        self.stdout.write(f"  Base delay: {base_delay}s, Max: {max_delay}s")
        
        while True:
            result = process_line_item_pending(limit=200)
            processed = result.get('processed', 0)
            
            if processed > 0:
                current_delay = base_delay
                idle_count = 0
                logger.info(f"[INVENTORY] Processed {processed} records, delay reset to {current_delay}s")
            else:
                idle_count += 1
                if idle_count >= idle_threshold:
                    current_delay = min(current_delay + increment, max_delay)
                    idle_count = 0
                    logger.debug(f"[INVENTORY] Idle backoff, delay now {current_delay}s")
            
            if not daemon:
                break
            
            time.sleep(current_delay)
```

---

## Monitoring & Observability

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `inventory_pending_count` | Current unprocessed records | > 100 |
| `inventory_clear_delay_current` | Current polling delay | N/A (info) |
| `inventory_clear_processed_per_cycle` | Records processed per run | N/A (info) |
| `inventory_stale_record_count` | Records older than timeout | > 0 |
| `inventory_clear_cycle_duration_ms` | Time to process one cycle | > 5000ms |

### Log Messages

```
# Normal operation
INFO  [INVENTORY] Processed 5 records, delay reset to 5s
DEBUG [INVENTORY] No pending records, idle cycle 3/5, delay 5s
DEBUG [INVENTORY] Idle backoff, delay now 10s

# Alerts
WARN  [INVENTORY_STALE] 3 pending records older than 300s
ERROR [INVENTORY] Failed to process pending record id=123: <error>
```

---

## Testing

### Quick Test (Single Run)

```bash
# Dry run - no changes made
python manage.py process_inventory_adaptive --dry-run -v 2

# Single run with actual processing
python manage.py process_inventory_adaptive -v 2
```

### Daemon Mode for Development

```bash
# Fast polling for testing (2s base, 10s max)
python manage.py process_inventory_adaptive --daemon --base-delay=2 --max-delay=10 -v 2

# Standard development settings (5s base)
python manage.py process_inventory_adaptive --daemon --base-delay=5 --max-delay=30 -v 2

# Reset state and start fresh
python manage.py process_inventory_adaptive --daemon --reset -v 2
```

### Manual Test Sequence

```bash
# 1. Start the processor in debug mode
python manage.py process_inventory_adaptive --base-delay=2 --max-delay=10 --daemon

# 2. In another terminal, create test pending records
python manage.py shell
>>> from apps.transactions.services.line_item_service import LineItemService
>>> # Create an order with lines to generate pending records
>>> # Watch the processor output

# 3. Observe:
#    - Delay resets to 2s when records processed
#    - Delay increases after idle cycles
#    - Stale alert after 5 minutes (or configured timeout)
```

### Unit Test

```python
# tests/test_adaptive_inventory.py

def test_adaptive_delay_resets_on_work():
    """Delay should reset to BASE when records are processed."""
    ...

def test_adaptive_delay_increases_on_idle():
    """Delay should increase after IDLE_CYCLES empty runs."""
    ...

def test_adaptive_delay_caps_at_max():
    """Delay should never exceed MAX_DELAY."""
    ...

def test_stale_record_alert():
    """Alert should fire for records older than STALE_TIMEOUT."""
    ...
```

---

## Migration Path

### Phase 1: Add Configuration (No behavior change)
- Add settings with current fixed 60s as default
- Deploy and verify no issues

### Phase 2: Enable Adaptive (Testing)
- Set `INVENTORY_CLEAR_BASE_DELAY=5` in dev/staging
- Monitor for 1 week

### Phase 3: Production Rollout
- Gradually reduce `BASE_DELAY` from 60 → 30 → 10
- Monitor latency and resource usage

---

## FAQ

**Q: What happens if the processor crashes mid-cycle?**  
A: The pending records remain unprocessed and will be picked up on restart. The stale alert will trigger if they sit too long.

**Q: Can multiple processors run simultaneously?**  
A: Yes, but they should use `select_for_update()` to avoid double-processing. The current implementation handles this.

**Q: Why not use websockets/push instead of polling?**  
A: Polling is simpler, more reliable, and sufficient for this use case. The adaptive delay minimizes the overhead while maintaining responsiveness.

**Q: How do I force immediate processing?**  
A: Call `process_inventory_deltas_immediately([item_id])` for urgent updates, or run `python manage.py process_pending_inventory --limit=1000` manually.
