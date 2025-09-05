# Inventory & Costing Overview


<!-- TOC START -->

## Table of Contents

- [Inventory & Costing Overview](#inventory-costing-overview)
  - [TL;DR](#tldr)
  - [Concepts](#concepts)
  - [InventoryStack.quantity Schema](#inventorystackquantity-schema)
  - [InventoryStack.cost Schema](#inventorystackcost-schema)
  - [Locking & Deferred Issues](#locking-deferred-issues)
  - [Reservations (Soft Holds)](#reservations-soft-holds)
    - [Reservation REST Endpoints](#reservation-rest-endpoints)
    - [PendingInventoryAdjustment Fields](#pendinginventoryadjustment-fields)
    - [Processor Strategies](#processor-strategies)
    - [Example (Programmatic)](#example-programmatic)
- [Queue an issue while locked](#queue-an-issue-while-locked)
- [Unlock -> auto processing](#unlock-auto-processing)
    - [Smoke Test Pattern](#smoke-test-pattern)
  - [Cost Update Helper](#cost-update-helper)
  - [Roadmap / Next Steps](#roadmap-next-steps)
  - [Design Rationale](#design-rationale)
  - [Operational Metrics & Monitoring](#operational-metrics-monitoring)
    - [JSON Metrics Endpoint](#json-metrics-endpoint)
    - [Prometheus Endpoint](#prometheus-endpoint)
    - [Dashboard Ideas](#dashboard-ideas)
    - [Housekeeping](#housekeeping)
  - [Quick Reference](#quick-reference)

<!-- TOC END -->

## TL;DR

InventoryStack holds per‑receipt quantity & cost JSON. If a stack is locked or insufficient, issues enqueue as PendingInventoryAdjustment. Unlock or periodic processor drains queue FIFO, applying issues. Use `process_pending_inventory` (global) or `process_pending_for_stack` (single) or rely on automatic unlock signal. Cost JSON has stable keys (unit_po, landed, moving_avg, etc.) for downstream valuation and reporting.

This document describes the inventory layering model, cost JSON schema, and the pending adjustment (deferred issue) processor recently added.

## Concepts

- InventoryStack: A received quantity "layer" for an Item at a Warehouse (lot/serial group). Tracks received, issued, scrapped quantities in a JSON `quantity` field and a standardized per‑unit costing JSON `cost`.
- SiteInventory: Lightweight roll‑up bucket per (Item, site_code) for fast availability queries (future use; currently scaffold).
- PendingInventoryAdjustment: Queue record for deferred inventory issues when a stack is locked (`is_locked=True`) or temporarily insufficient.

## InventoryStack.quantity Schema

```json
{
  "received": 120.0,
  "issued": 35.0,
  "scrapped": 2.0
}
```

Remaining = received - issued - scrapped.

## InventoryStack.cost Schema

Per‑unit unless noted.

| Key | Meaning |
|-----|---------|
| unit_po | Original PO unit cost (base currency) |
| fifo_snapshot | FIFO pick price at layer creation |
| lifo_snapshot | LIFO pick price at layer creation |
| moving_avg | System moving average AFTER this receipt (per unit) |
| landed | Landed unit cost (unit_po + alloc freight/duty/handling + vat - scrap alloc) |
| freight | Allocated freight per unit |
| duty | Allocated duties/tariffs per unit |
| handling | Allocated handling per unit |
| vat | VAT per unit (0 if N/A) |
| scrap_cost | Accumulated per‑unit equivalent cost of scrapped qty (alloc basis) |
| trend_pct | Percent change vs baseline (prior moving_avg or explicit) |
| currency | 3‑letter ISO code |
| exchange_rate | Currency → base conversion rate (1 if already base) |

Factory: `apps.products.models.inventory_layer.default_cost()`.

## Locking & Deferred Issues

## Reservations (Soft Holds)

`InventoryReservation` provides short‑lived soft holds (cart/seat reservations) that reduce logical availability without immediately issuing quantity.

Lifecycle:

1. Create reservation (state=pending) if `remaining_qty - active_reserved >= qty`.
2. Availability = `remaining_qty - sum(active pending reservations)`.
3. Commit: convert to real issue (marks stack issued, state=committed).
4. Release (canceled) or Expire: state updated, availability restored.
5. Expiration driven by `expires_at`; periodic task / command reclaims expired rows.

Key API (service functions in `inventory_reservations.py`):

- `create_reservation(stack, qty, ttl_seconds=900)`
- `availability_for_stack(stack)`
- `release_expired(batch=500)`

### Reservation REST Endpoints

Base path prefix: `/products/` (Django app namespace `products`).

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/products/inventory/availability/<stack_id>/` | GET | Returns remaining vs available (minus active reservations) |
| `/products/inventory/reservations/` | POST | Create reservation (body: stack_id, qty, ttl_seconds?, reason?, ctx?) |
| `/products/inventory/reservations/action/` | POST | Commit or release (body: reservation_id, action=commit\|release, reason?) |

Examples:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/products/inventory/availability/123/

curl -X POST -H "Authorization: Bearer <token>" -H 'Content-Type: application/json' \
  -d '{"stack_id":123, "qty":5, "ttl_seconds":600}' \
  http://localhost:8000/products/inventory/reservations/

curl -X POST -H "Authorization: Bearer <token>" -H 'Content-Type: application/json' \
  -d '{"reservation_id":77, "action":"commit"}' \
  http://localhost:8000/products/inventory/reservations/action/
```

Management command: `python manage.py expire_inventory_reservations`.

States: pending, committed, canceled, expired.

Celery beat entries:

| Purpose | Task | Default Schedule |
|---------|------|------------------|
| Drain pending adjustments | `products.tasks.process_pending_inventory` | *every minute* |
| Expire stale reservations | `products.tasks.expire_inventory_reservations` | *every minute* |

`ctx` field: Optional JSON payload stored on the reservation for correlation (e.g., cart_id, user_session). Use small, non-PII keys.

Commit only issues inventory if sufficient remaining when commit occurs; otherwise commit attempts can be retried after upstream replenishment.


Some operations (adjustment, recount, cost revaluation) set `InventoryStack.is_locked=True` to prevent direct quantity mutation. During a lock, attempts to issue stock call `stack.issue_or_enqueue(qty)`:

1. If locked OR insufficient remaining, a `PendingInventoryAdjustment` row is created (state `pending`).
2. If unlocked and sufficient, quantity is applied immediately (no queue record).

Unlock flow: When `is_locked` transitions True → False, a post-save signal schedules processing of that stack's pending rows (FIFO). Each row either applies (marking issued) or remains pending if still locked/insufficient.

Manual / periodic drain: Management command:

```bash
python manage.py process_pending_inventory --limit 200
```

Celery task: `products.tasks.process_pending_inventory` (optionally schedule via beat every minute).

### PendingInventoryAdjustment Fields

| Field | Notes |
|-------|-------|
| stack | FK to InventoryStack |
| qty | Decimal quantity to issue |
| state | pending / applied / canceled |
| reason | Short code (e.g. `issue`, `insufficient_issue`) |
| reserved_conflict | Immediate issue would violate active (pending) reservations; processor defers until reservations release/expire |
| request_ref | Opaque JSON (caller context / correlation id) |
| dt_created | Auto timestamp |
| dt_applied | Set on success |
| cancel_reason | Explanation when state=canceled |

### Processor Strategies

Two processors:

1. Global: `process_pending_inventory(limit=100, apply_insufficient=False, cancel_on_insufficient=False, dry_run=False)`
2. Single stack: `process_pending_for_stack(stack_id, ...)` (used by unlock signal)

Options:

- apply_insufficient: force application even if remaining < qty (would drive negative remaining; default False)
- cancel_on_insufficient: cancel rows that cannot be applied (instead of retrying later)
- dry_run: simulate without persistence.

Reservation Interaction: The issuer treats active pending reservations as reducing available quantity. If `(remaining_qty - active_reserved) < request_qty` the adjustment is enqueued with reason `reserved_conflict` rather than immediately issued, preserving soft holds.

Processor Behavior for reserved_conflict:

- Both global and per-stack processors perform an extra check for rows whose reason is `reserved_conflict`.
- They compute `active_reserved` for the stack. If `(remaining - active_reserved) < qty` the row is skipped this run (counter: `reserved_conflict_skipped`).
- Once reservations expire (via `expire_inventory_reservations` task) or are explicitly released, the next processor run applies the pending issue normally.
- Force override: `apply_insufficient=True` also bypasses reservation protection (use sparingly).


Processor summary now includes: `reserved_conflict_skipped`.

### Example (Programmatic)

```python
from apps.products.models.inventory_layer import InventoryStack
stack = InventoryStack.objects.get(pk=123)
# Queue an issue while locked
stack.is_locked = True; stack.save(update_fields=["is_locked"])
stack.issue_or_enqueue(5, reason="pick")
# Unlock -> auto processing
stack.is_locked = False; stack.save(update_fields=["is_locked"])
```

### Smoke Test Pattern

```bash
python manage.py shell -c "from apps.products.models.inventory_layer import InventoryStack, PendingInventoryAdjustment; from apps.products.models.item import Item; from apps.products.models.warehouse import Warehouse; from decimal import Decimal; i=Item.objects.create(name='DocItem'); w=Warehouse.objects.create(name='Main', code='MAIN'); s=InventoryStack.objects.create(item=i, warehouse=w, quantity={'received':50}); s.is_locked=True; s.save(); s.issue_or_enqueue(Decimal('10')); s.is_locked=False; s.save(); print(list(PendingInventoryAdjustment.objects.filter(stack=s).values_list('state', flat=True)))"
```

Expected: `['applied']` and remaining qty 40.

## Cost Update Helper

`InventoryStack.update_cost_after_receipt(unit_po, freight=0, duty=0, handling=0, vat=0, prior_moving_avg=None, trend_baseline=None)` populates/adjusts cost JSON. Caller provides weighted moving average math externally (function does not currently compute weighted average).

## Roadmap / Next Steps

- Batch recompute of moving average across historical layers (service + command).
- Optional negative prevention: auto-cancel pending rows after timeout if insufficient.
- Movement ledger integration (`InventoryMovement`) for full audit trail.
- SiteInventory synchronization logic on every applied issue/receipt.
- Cost roll-up into `Item.cost` (components.avg / components.last sync).

## Design Rationale

Why queue instead of blocking:

- Avoid holding transactions open waiting for long-running recount or valuation tasks.
- Provide observability (pending rows) instead of silent retries.
- Enable force-apply or cancel policies without changing call sites.

Why JSON fields for quantity/cost:

- Flexibility for incremental enrichment (e.g., reserved, damaged) without migration churn.
- Low cardinality updates; entire document small.
- Future: could project critical fields to materialized columns / views if needed for analytics.

## Operational Metrics & Monitoring

### JSON Metrics Endpoint

Path: `/products/inventory/metrics/`

Query params:

- `raw=1` return bare JSON (no envelope)
- `samples=1` include sample pending adjustments and active reservations

Response (key sections):

- `reservations`: counts, qty, `active_reserved_qty`, TTL analytics (`avg_pending_ttl_s`, `soonest_expiry_in_s`, `pending_ttl_buckets`)
- `pending_adjustments`: counts, qty, `reserved_conflict_pending`, `insufficient_pending`
- `stacks`: total, locked, remaining_total, received_total
- `protection`: `reserved_vs_remaining_pct`
- `processor_runs`: latest global & stack processor run summaries plus duration buckets

Example snippet:

```json
{
  "reservations": {
    "counts": {"pending": 3},
    "qty": {"pending": 15.0},
    "active_reserved_qty": 15.0,
    "avg_pending_ttl_s": 42.5,
    "soonest_expiry_in_s": 120,
    "pending_ttl_buckets": {"30":1,"60":1,"120":1,"300":0,"600":0,"1200":0,"3600":0,"7200":0,"14400":0,"28800":0,"86400":0,"+Inf":0}
  },
  "pending_adjustments": {"counts": {"pending": 2}, "qty": {"pending": 6.0}, "reserved_conflict_pending": 1, "insufficient_pending": 1},
  "stacks": {"total": 12, "locked": 1, "remaining_total": 320.0, "received_total": 400.0},
  "processor_runs": {
    "latest_global": {"attempted":5, "applied":4, "reserved_conflict_skipped":1, "duration_s":0.12},
    "latest_global_duration_buckets": {"0.01":0,"0.05":1,"0.1":0,"0.25":1,"0.5":0,"1":0,"2":0,"5":0,"+Inf":0}
  }
}
```

### Prometheus Endpoint

Path: `/products/inventory/metrics/prometheus`

Auth control:

- Setting `INVENTORY_PROMETHEUS_REQUIRE_AUTH` (default True). If enabled, unauthenticated scrape requires `?auth=0` query param (internal / controlled use) or an authenticated user.

Exports (plain text):

- `inventory_reservations_count{state="..."}`
- `inventory_reservations_qty{state="..."}`
- `inventory_reservations_active_reserved_qty`
- `inventory_reservations_avg_pending_ttl_seconds`
- `inventory_reservations_soonest_expiry_seconds`
- `inventory_reservations_pending_ttl_bucket{le="..."}` (histogram style buckets)
- `inventory_pending_adjustments_count{state="..."}` / `..._qty{state="..."}`
- `inventory_pending_reserved_conflict_pending`, `inventory_pending_insufficient_pending`
- `inventory_stacks_total`, `inventory_stacks_locked`, `inventory_stacks_remaining_total`, `inventory_stacks_received_total`
- `inventory_reserved_vs_remaining_pct`
- Processor run gauges: `inventory_processor_global_attempted`, etc., plus histogram-ish buckets: `inventory_processor_global_duration_bucket{le="..."}` and similarly for `_stack_`.

Sample:

```text
inventory_reservations_count{state="pending"} 3
inventory_reservations_active_reserved_qty 15.0
inventory_reservations_pending_ttl_bucket{le="60"} 1
inventory_processor_global_attempted 5
inventory_processor_global_duration_bucket{le="0.25"} 1
```

### Dashboard Ideas

- Gauge: Active reserved vs remaining (pct) – alert > threshold (e.g. 80%).
- Counter / Rate: reserved_conflict_pending & reserved_conflict_skipped – rising trend indicates reservation/issue contention.
- Histogram: processor run durations – watch tail latency for spikes.
- Pending TTL: high avg_pending_ttl_s may mean reservations not being consumed / released promptly.

### Housekeeping

- Consider snapshotting metrics (`snapshot_inventory_metrics`) for historical trending separate from Prom scrape (Prom pull model only stores what it scrapes).
- If adding new fields, keep names stable; append rather than rename to avoid dashboard churn.

## Quick Reference

| Action | Path |
|--------|------|
| Management command | `process_pending_inventory` |
| Celery task | `products.tasks.process_pending_inventory` |
| Signal auto-run | InventoryStack post-save (unlock) |
| Single stack processor | `process_pending_for_stack` |
| Global processor | `process_pending_inventory` |

Add enhancements to this document; keep README root concise by linking here.
