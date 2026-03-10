# Pending as Compensating Transactions

## Overview

The `Pending` model (`apps/core/models/pending.py`) serves as a **general-purpose compensating transaction mechanism** for eventual consistency. When immediate consistency is blocked — by record contention, concurrent edits, locked rows, or transient failures — a Pending record captures the intended operation as a command object that Celery retries until the system converges.

This pattern is the primary tool for handling **long-tail risks**: low-probability but high-impact scenarios where data between related records can drift out of sync.

---

## Core Concept

A Pending record is a **command object**, not just a queue message:

| Property | Meaning |
|----------|---------|
| `model_name` | What type of record this affects (e.g., `item`, `invoice`) |
| `record_id` | The specific record ID to act on |
| `purpose` | Machine-readable intent (e.g., `inventory_line_add`, `ledger_sync`) |
| `name` | Human-readable description |
| `data` | JSON payload with everything the processor needs |
| `dt_processed` | `0` = unprocessed (retry needed), `>0` = epoch ms when completed |

### Lifecycle

```
Event occurs (invoice save, line add, etc.)
    │
    ├── Create Pending record (purpose + data)
    │
    ├── Attempt immediate execution (happy path)
    │       │
    │       ├── Success → mark Pending processed (dt_processed = now)
    │       │
    │       └── Failure → Pending stays unprocessed (dt_processed = 0)
    │                       │
    │                       └── Celery picks up → retries → marks processed
    │
    └── Pending persists as audit record regardless of path
```

**Key insight**: In the happy path, the Pending record is created AND processed in the same request cycle. It still exists as an audit trail. Only on failure does it become a retry command.

---

## Active Implementations

### 1. Inventory Pending (Established)

**Problem**: Many transactions reference the same `Item` row. Direct updates to `Item.quantity` create lock contention.

**Solution**: Line operations create Pending records instead of updating Item directly. A background processor aggregates and applies deltas.

| Purpose | Trigger | What It Does |
|---------|---------|-------------|
| `inventory_line_add` | New line on order/invoice/etc. | Adjusts `on_so`, `on_po`, `on_hand`, etc. |
| `inventory_qty_change` | Quantity edited on existing line | Delta applied to item quantity bucket |
| `inventory_line_delete` | Line removed from transaction | Reverses the original reservation |
| `inventory_cost_change` | Cost updated on line | Updates cost tracking on item |

**Files**:
- Creation: `apps/transactions/services/line_item_service.py`
- Processing: `apps/transactions/services/pending_inventory_processor.py`
- Dispatch: `apps/products/dispatch_pending.py`
- Celery task: `apps/products/tasks.py`

### 2. Ledger Sync (New — March 2026)

**Problem**: Invoice saves create/replace Ledger records and update OrgBase balances. If the org balance update fails (contention, transient error) or a user has the ledger open in read-write, the invoice's view of its ledger state can drift from reality.

**Solution**: Every invoice save that touches ledgers creates a `ledger_sync` Pending. Happy path marks it processed immediately. Failure leaves it for Celery.

| Purpose | Trigger | What It Does |
|---------|---------|-------------|
| `ledger_sync` | Invoice save with term changes | Ensures ledger records + org balance are in sync |

**Pipeline** (in `on_invoice_save()`):
1. Create/replace Ledger records from payment terms
2. Stamp `invoice.metadata.ledger` with entries + `dt_sync=0`
3. Create Pending with `purpose='ledger_sync'`
4. Attempt `update_org_balances(org)`
5. Success → stamp `dt_sync=now`, mark Pending processed
6. Failure → both stay at 0/unprocessed for Celery

**Self-diagnosing metadata** (`invoice.metadata.ledger`):
```json
{
    "entries": [
        {"ledger_id": 42, "value_original": 500.0, "value_available": 500.0, "dt_due": 1741564800000}
    ],
    "total_original": 500.0,
    "dt_sync": 1741478400000
}
```

| `dt_sync` State | Meaning |
|-----------------|---------|
| `> 0` | Fully synced — ledgers and org balance confirmed |
| `= 0` | Ledger records written but org balance not confirmed |
| Key absent | Ledger write itself may have failed |

**Files**:
- Creation + stamping: `apps/accounts/services/ledger_balance.py` (`on_invoice_save`)
- Processing: `apps/accounts/services/ledger_sync_processor.py`
- Phase 5 fallback: `apps/transactions/services/transaction_save.py`

---

## When to Use the Pending Pattern

Use Pending as a compensating transaction when **any** of these apply:

### Hot Row Contention
Multiple operations target the same record concurrently. Instead of fighting for a lock, queue the intent and apply it serially.

**Example**: Item quantity buckets — dozens of order saves may touch the same item.

### Record Locked by User
A user has a record open in read-write mode. The system needs to make a change but the record is locked.

**Example**: User editing a ledger record while another user saves an invoice with term changes.

### Cross-Record Consistency
Two or more records must stay in sync, but updating both atomically isn't practical (different tables, different services, different timing).

**Example**: Invoice → Ledger records → Org balance. Three records that must agree.

### Transient Failures
Network blips, database timeouts, external service outages. The operation is valid but can't complete right now.

**Example**: Org balance update fails due to database timeout during high-traffic period.

---

## How to Add a New Pending Domain

Follow this pattern when introducing Pending to a new domain:

### Step 1: Define the Purpose Constant

```python
# In your service module
PURPOSE_MY_SYNC = 'my_sync'
```

### Step 2: Create the Pending Record

```python
from apps.core.models import Pending

pending = Pending.objects.create(
    model_name='my_model',           # What record type
    record_id=str(record.pk),        # Which specific record
    purpose=PURPOSE_MY_SYNC,         # Machine-readable intent
    name=f'My Sync: {record.ida}',   # Human-readable description
    data={
        'record_id': record.pk,
        'reason': 'descriptive reason',
        # ... everything the processor needs to act
    },
)
```

### Step 3: Attempt Immediate Execution + Mark Processed

```python
try:
    do_the_actual_work(record)
    pending.mark_processed(save=True)  # Happy path
except Exception:
    logger.warning("Will retry via Celery (Pending %s)", pending.pk)
    # Pending stays unprocessed — Celery will pick it up
```

### Step 4: Write the Processor

Mirror `ledger_sync_processor.py` or `pending_inventory_processor.py`:

```python
def process_my_sync_pending(limit=100, dry_run=False):
    pending_records = Pending.objects.filter(
        purpose=PURPOSE_MY_SYNC,
        dt_processed=0,
    ).order_by('dt_created')[:limit]

    for pending in pending_records:
        try:
            _process_single(pending, dry_run=dry_run)
        except Exception as exc:
            logger.error("Error processing %s: %s", pending.pk, exc)
```

### Step 5: Wire Into Celery

Add a task in your app's `tasks.py` and schedule it via `CELERY_BEAT_SCHEDULE`.

---

## Observability & Long-Tail Risk Detection

### Stale Pending Detection

Pending records that stay unprocessed for too long are signals, not just queue items:

```python
# Find stuck Pendings older than 1 hour
from django.utils import timezone
one_hour_ago = int((timezone.now().timestamp() - 3600) * 1000)

stuck = Pending.objects.filter(
    dt_processed=0,
    dt_created__lt=one_hour_ago,
).values('purpose').annotate(
    count=models.Count('id'),
    oldest=models.Min('dt_created'),
)
```

### What Stuck Pendings Tell You

| Pattern | Likely Cause | Action |
|---------|-------------|--------|
| Many `inventory_line_add` for same item | Item row is persistently locked | Investigate who holds the lock |
| `ledger_sync` older than 30 min | Org balance contention or bug | Check org record, re-run manually |
| Spike of any purpose at specific time | Deploy issue or batch conflict | Check deploy logs, correlate with releases |
| Same record_id appearing repeatedly | Processor keeps failing | Check processor logs for that record |

### Monitoring Query

```sql
-- Dashboard: unprocessed Pendings by purpose and age
SELECT
    purpose,
    COUNT(*) as count,
    MIN(dt_created) as oldest_ms,
    MAX(dt_created) as newest_ms
FROM pending
WHERE dt_processed = 0
GROUP BY purpose
ORDER BY count DESC;
```

### Audit Trail

Even processed Pending records are valuable. They show:
- How often each domain experiences contention
- Average time-to-resolution per purpose
- Which records are most contentious
- Trends over time (is contention getting better or worse?)

```sql
-- Average resolution time by purpose (last 30 days)
SELECT
    purpose,
    COUNT(*) as total,
    AVG(dt_processed - dt_created) as avg_resolution_ms,
    MAX(dt_processed - dt_created) as max_resolution_ms
FROM pending
WHERE dt_processed > 0
  AND dt_created > EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days') * 1000
GROUP BY purpose;
```

---

## Design Principles

1. **Command, not message** — Pending carries everything needed to execute, not just a notification that something happened.

2. **Happy path is synchronous** — Don't add latency when things work. Create the Pending AND process it in the same request cycle.

3. **Idempotent processors** — Running a processor twice on the same Pending must produce the same result. The processor should check current state, not just blindly apply.

4. **Self-diagnosing records** — When possible, stamp the source record with sync metadata (like `invoice.metadata.ledger.dt_sync`) so any reader can tell if a re-sync is needed without querying the Pending table.

5. **One Pending per event, not per retry** — If the processor fails, it leaves the existing Pending unprocessed. Don't create a new one for each retry attempt.

6. **Audit trail persists** — Don't delete processed Pendings. They're lightweight and valuable for trend analysis.

7. **Uniform lifecycle** — Every domain follows the same lifecycle: Create → Attempt → Process/Retry → Audit. This lets a single monitoring dashboard cover all domains.
