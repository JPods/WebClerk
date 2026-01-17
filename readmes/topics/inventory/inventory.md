# Inventory & Costing Overview


<!-- TOC START -->

## Table of Contents

- [Inventory & Costing Overview](#inventory--costing-overview)
  - [Table of Contents](#table-of-contents)
  - [TL;DR](#tldr)
  - [Concepts](#concepts)
  - [InventoryLayer.quantity Schema](#inventorystackquantity-schema)
  - [InventoryLayer.cost Schema](#inventorystackcost-schema)
  - [Locking & Deferred Issues](#locking--deferred-issues)
  - [Reservations (Soft Holds)](#reservations-soft-holds)
    - [Reservation REST Endpoints](#reservation-rest-endpoints)
    - [PendingInventoryAdjustment Fields](#pendinginventoryadjustment-fields)
    - [Processor Strategies](#processor-strategies)
    - [Example (Programmatic)](#example-programmatic)
    - [Smoke Test Pattern](#smoke-test-pattern)
  - [Cost Update Helper](#cost-update-helper)
  - [Line Item Pending Inventory (Transaction-Level)](#line-item-pending-inventory-transaction-level)
    - [Flow](#flow)
    - [Purpose Codes](#purpose-codes)
    - [Transaction Type Codes](#transaction-type-codes)
    - [Processor](#processor)
    - [Data Structure](#data-structure)
    - [Integration Note](#integration-note)
    - [Related Documentation](#related-documentation)
  - [Roadmap / Next Steps](#roadmap--next-steps)
  - [Design Rationale](#design-rationale)
  - [Operational Metrics & Monitoring](#operational-metrics--monitoring)
    - [JSON Metrics Endpoint](#json-metrics-endpoint)
    - [Prometheus Endpoint](#prometheus-endpoint)
    - [Dashboard Ideas](#dashboard-ideas)
    - [Housekeeping](#housekeeping)
  - [Quick Reference](#quick-reference)
  - [Purchase Order Receiving](#purchase-order-receiving)

<!-- TOC END -->

## TL;DR

InventoryLayer holds per‑receipt quantity & cost JSON. If a stack is locked or insufficient, issues enqueue as PendingInventoryAdjustment. Unlock or periodic processor drains queue FIFO, applying issues. Use `process_pending_inventory` (global) or `process_pending_for_stack` (single) or rely on automatic unlock signal. Cost JSON has stable keys (unit_po, landed, moving_avg, etc.) for downstream valuation and reporting.

This document describes the inventory layering model, cost JSON schema, and the pending adjustment (deferred issue) processor recently added.

## Concepts

- InventoryLayer: A received quantity "layer" for an Item at a Warehouse (lot/serial group). Tracks received, issued, scrapped quantities in a JSON `quantity` field and a standardized per‑unit costing JSON `cost`.
- SiteInventory: Lightweight roll‑up bucket per (Item, site_code) for fast availability queries (future use; currently scaffold).
- PendingInventoryAdjustment: Queue record for deferred inventory issues when a stack is locked (`is_locked=True`) or temporarily insufficient.

## InventoryLayer.quantity Schema

```json
{
  "received": 120.0,
  "issued": 35.0,
  "scrapped": 2.0
}
```

Remaining = received - issued - scrapped.

## InventoryLayer.cost Schema

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


Some operations (adjustment, recount, cost revaluation) set `InventoryLayer.is_locked=True` to prevent direct quantity mutation. During a lock, attempts to issue stock call `stack.issue_or_enqueue(qty)`:

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
| stack | FK to InventoryLayer |
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
from apps.products.models.inventory_layer import InventoryLayer
stack = InventoryLayer.objects.get(pk=123)
# Queue an issue while locked
stack.is_locked = True; stack.save(update_fields=["is_locked"])
stack.issue_or_enqueue(5, reason="pick")
# Unlock -> auto processing
stack.is_locked = False; stack.save(update_fields=["is_locked"])
```

### Smoke Test Pattern

```bash
python manage.py shell -c "from apps.products.models.inventory_layer import InventoryLayer, PendingInventoryAdjustment; from apps.products.models.item import Item; from apps.products.models.warehouse import Warehouse; from decimal import Decimal; i=Item.objects.create(name='DocItem'); w=Warehouse.objects.create(name='Main', code='MAIN'); s=InventoryLayer.objects.create(item=i, warehouse=w, quantity={'received':50}); s.is_locked=True; s.save(); s.issue_or_enqueue(Decimal('10')); s.is_locked=False; s.save(); print(list(PendingInventoryAdjustment.objects.filter(stack=s).values_list('state', flat=True)))"
```

Expected: `['applied']` and remaining qty 40.

## Cost Update Helper

`InventoryLayer.update_cost_after_receipt(unit_po, freight=0, duty=0, handling=0, vat=0, prior_moving_avg=None, trend_baseline=None)` populates/adjusts cost JSON. Caller provides weighted moving average math externally (function does not currently compute weighted average).

## Line Item Pending Inventory (Transaction-Level)

Separate from the `PendingInventoryAdjustment` queue (which targets InventoryLayer stacks), the **Line Item Service** creates `Pending` records to track inventory effects from transaction line edits. This mirrors the WebClerk2 "DInventory" deferred pattern.

### Flow

```
┌──────────────────┐     ┌───────────────────┐     ┌────────────────┐
│  LineItemService │────▶│  Pending Record   │────▶│  Item.record   │
│  (add/edit/del)  │     │  (JSON snapshot)  │     │  qty buckets   │
└──────────────────┘     └───────────────────┘     └────────────────┘
         │                        │                        │
         │ create_pending=True    │ dt_processed=0         │ processor
         └────────────────────────┴────────────────────────┘
```

### Purpose Codes

| Purpose | Trigger | Effect |
|---------|---------|--------|
| `inventory_line_add` | Line created | Reserve qty (SO: qty_on_so+, PO: qty_on_po+, WO: qty_on_wo+) |
| `inventory_qty_change` | Line qty updated | Adjust delta (new - old) |
| `inventory_line_delete` | Line removed | Release reserved qty |
| `inventory_cost_change` | Line cost updated | Update Item moving avg (future) |

### Transaction Type Codes

| Code | Model | Inventory Effect |
|------|-------|------------------|
| `SO` | SalesOrder | `qty_on_so` |
| `PO` | PurchaseOrder | `qty_on_po` |
| `WO` | WorkOrder | `qty_on_wo` |
| `IV` | Invoice | `qty_invoiced` (actual issue) |
| `PP` | Proposal | None (quotes don't affect inventory) |

### Processor

Management command:

```bash
python manage.py process_line_item_pending --limit 100
python manage.py process_line_item_pending --item-id 123 --dry-run
python manage.py process_line_item_pending --force-locked  # process even if Item locked
```

Service functions:

```python
from apps.transactions.services import process_line_item_pending, process_pending_for_item

# Global batch processing
result = process_line_item_pending(limit=100, dry_run=False)
# {"processed": 42, "skipped": 3, "errors": 0}

# Single item focus
result = process_pending_for_item(item_id=123)
```

### Data Structure

Pending record `data` JSON:

```json
{
  "type_code": "SO",
  "type_id": 1,
  "item_id": 123,
  "doc_id": 456,
  "line_id": 789,
  "qty_on_so": 10.0,
  "qty_on_po": 0,
  "qty_on_wo": 0,
  "qty_invoiced": 0,
  "price_snapshot": {"unit_price": 25.0, "cost": 15.0},
  "created_by": "api",
  "dt_action": "2025-01-15T10:30:00Z"
}
```

### Integration Note

The two pending systems serve different layers:

| System | Model | Target | Trigger |
|--------|-------|--------|---------|
| **PendingInventoryAdjustment** | InventoryLayer (stack) | Physical qty (issued/received) | Receipt, pick, scrap |
| **Pending (Line Item)** | Item.record buckets | Logical qty (on_so, on_po, etc.) | Transaction line CRUD |

Both use deferred processing to reduce lock contention. Celery beat schedules run both processors periodically.

### Related Documentation

- [Transaction Services](../../../React2025/readmes/topics/transaction-services.md#line-item-service) – Frontend/backend API details
- [Transaction Flow Plan](transactions/transaction_flow_calc_plan.md) – WebClerk2 migration mapping

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
| Management command (stacks) | `process_pending_inventory` |
| Management command (line items) | `process_line_item_pending` |
| Celery task (stacks) | `products.tasks.process_pending_inventory` |
| Celery task (line items) | `transactions.tasks.process_line_item_pending` |
| Signal auto-run | InventoryLayer post-save (unlock) |
| Single stack processor | `process_pending_for_stack` |
| Single item processor | `process_pending_for_item` |
| Global processor (stacks) | `process_pending_inventory` |
| Global processor (line items) | `process_line_item_pending` |

Add enhancements to this document; keep README root concise by linking here.

## Purchase Order Receiving

Endpoint (writes inventory):

- POST `/transactions/purchase-orders/<pk>/receive/`

Request body:

```json
{
  "receipt_no": "RCPT-2025-0001",
  "lines": [
    {
      "po_line_id": 123,
      "qty": 5,
      "warehouse_code": "MAIN",
      "unit_cost": 12.5,
      "lot": "LOT-A",
      "serial_batch": ""
    }
  ]
}
```

Success (201):

```json
{ "receipt_id": 987, "stacks_created": [321, 322] }
```

Behavior

- Validates the Purchase Order header (`<pk>`) and that each `po_line_id` belongs to it.
- Resolves the Item from the PO line JSON `item.id_num` (fallback: `id` / `item_id`).
- Looks up `Warehouse` by `warehouse_code`.
- Creates one `InventoryLayer` per received line with:
  - `quantity`: `{ "received": qty, "issued": 0, "scrapped": 0 }`
  - `source_doc_type`: `"purchase_receipt"`
  - `source_doc_id`: the created `PurchaseReceipt.id`
- Updates cost via `InventoryLayer.update_cost_after_receipt(unit_cost)`; if `unit_cost` omitted, uses the PO line `cost.unit` when present.
- Increments a `received` hint inside the PO line `quantity` JSON when available.

Error modes (400)

- Missing `receipt_no`.
- `po_line_id` not found for this purchase order.
- PO line lacks `item.id_num` and no fallback ID present.
- Item or Warehouse not found.

Notes

- This action is not idempotent; repeated calls will create additional stacks. Call once per receipt.
- Authorization follows the project `view_edit` rules; ensure the user can edit purchase orders and inventory.
- Lot/serial fields are optional; provide when your process requires traceability.

Example

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
        "receipt_no":"RCPT-1001",
        "lines":[{"po_line_id":1,"qty":3.5,"warehouse_code":"MAIN","unit_cost":9.99}] 
      }' \
  http://localhost:8000/transactions/purchase-orders/42/receive/
```
