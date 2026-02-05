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
  - [Roadmap / Next Steps](#roadmap--next-steps)
  - [Design Rationale](#design-rationale)
  - [Operational Metrics & Monitoring](#operational-metrics--monitoring)
    - [JSON Metrics Endpoint](#json-metrics-endpoint)
    - [Prometheus Endpoint](#prometheus-endpoint)
    - [Dashboard Ideas](#dashboard-ideas)
    - [Housekeeping](#housekeeping)
  - [Quick Reference](#quick-reference)
  - [Purchase Order Receiving](#purchase-order-receiving)
  - [Bill of Materials (BOM)](#bill-of-materials-bom)
    - [BOM Model](#bom-model)
    - [BOM REST Endpoints](#bom-rest-endpoints)
    - [Serializer Computed Fields](#serializer-computed-fields)
    - [React Component](#react-component)
    - [Test Data Structure](#test-data-structure)
    - [Management Commands](#management-commands)
    - [Source Data](#source-data)

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
| Management command | `process_pending_inventory` |
| Celery task | `products.tasks.process_pending_inventory` |
| Signal auto-run | InventoryLayer post-save (unlock) |
| Single stack processor | `process_pending_for_stack` |
| Global processor | `process_pending_inventory` |

Add enhancements to this document; keep README root concise by linking here.

## Inventory Receiving Functions

The system provides three specialized functions for receiving inventory in `apps/transactions/services/flow.py`:

| Function | Use Case | On-Hand Effect |
|----------|----------|----------------|
| `receive_purchase_order(po, receipt_id, lines)` | Receiving goods from vendors | +qty, -on_po |
| `complete_workorder(wo, receipt_id, lines)` | Completing manufacturing | +qty, -on_wo |
| `adjust_inventory(adjustment_id, lines, notes)` | Manual adjustments | ±qty |

A high-level dispatcher `receive_inventory_changes(source_type, source, receipt_id, lines)` routes to the appropriate handler based on `source_type` ('purchase', 'workorder', 'adjustment').

See [Inventory Deltas - Receiving Functions](inventory_deltas.md#inventory-receiving-functions) for detailed documentation and code examples.

## Purchase Order Receiving

Endpoint (writes inventory):

- POST `/transactions/purchase-orders/<pk>/receive/`

Request body:

```json
{
  "receipt_id": "RCPT-2025-0001",
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

- Missing `receipt_id`.
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
        "receipt_id":"RCPT-1001",
        "lines":[{"po_line_id":1,"qty":3.5,"warehouse_code":"MAIN","unit_cost":9.99}] 
      }' \
  http://localhost:8000/transactions/purchase-orders/42/receive/
```

## Bill of Materials (BOM)

The `BillOfMaterial` model tracks parent-child component relationships for assembled/bundled items.

### BOM Model

Located at `apps/products/models/bill_of_material.py`. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | FK → Item | Parent (assembled) item |
| `component_id` | FK → Item | Child component item |
| `quantity` | Decimal | Quantity needed per assembly |
| `cost_snapshot` | Decimal | Component unit cost at creation |
| `scrap_factor` | Decimal | Scrap ratio (0-1) |
| `sequence` | Int | Sort order |
| `revision` | Char | BOM revision code |
| `dt_effective_from/to` | Date | Effectivity window |
| `is_alternate` | Bool | Alternate component flag |
| `alternate_group` | Char | Group key for alternates |

### BOM REST Endpoints

Base path: `/api/products/items/<parent_id>/bom/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/products/items/<id>/bom/` | GET | List BOM lines for parent item |
| `/api/products/items/<id>/bom/` | POST | Create new BOM line |
| `/api/products/items/<id>/bom/<line_id>/` | GET | Get single BOM line detail |
| `/api/products/items/<id>/bom/<line_id>/` | PUT/PATCH | Update BOM line |
| `/api/products/items/<id>/bom/<line_id>/` | DELETE | Delete BOM line |
| `/api/products/items/<id>/bom/recalc-cost/` | POST | Recalculate cost snapshots |

Query parameters for list:
- `as_of=YYYY-MM-DD` - Resolve BOM at historical date (effectivity filtering)
- `revision=CODE` - Filter to specific revision

### Serializer Computed Fields

The `BillOfMaterialSerializer` returns these computed fields:

| Field | Type | Description |
|-------|------|-------------|
| `extended_cost` | Decimal | `quantity × cost_snapshot` |
| `component_child_count` | Int | Count of BOM children for this component (0 if not a subassembly) |
| `refs.links.bom` | Array | Nested BOM children of this component (one level deep) |

Example response with nested data:
```json
{
  "id": 32,
  "component": {"id": 255, "sku": "BB110", "name": "..."},
  "quantity": "1.0000",
  "cost_snapshot": "40.0000",
  "extended_cost": 40.0,
  "component_child_count": 1,
  "refs": {
    "links": {
      "bom": [
        {"id": 25, "component": {"sku": "BB105"}, "quantity": "10.0000", ...}
      ]
    }
  }
}
```

### React Component

`BOMSection` in `React2025/src/apps/products/models/item/components/BOMSection.tsx`:

- Lazy-loads BOM data when section is expanded
- Displays component SKU, description, quantity, unit cost, extended cost
- Shows total extended cost across all components
- Badge indicators for:
  - **Child count** (info badge) - Shows when component has its own BOM children
  - **Optional** (warning badge)
  - **Alternate** (primary badge)
  - **Scrap %** (error badge)
- Refreshes automatically when viewing different items

### Test Data Structure

Seeded via `python manage.py seed_sample_bom`. Baseball equipment kits:

**BB401** (WS Baseball Starter Inventory - 8 components):
| Child | Qty | Description |
|-------|:---:|-------------|
| BB1 | 5 | All-Star BB1 Bat Carry Bag/Rack |
| BB105 | 7 | Little League Baseballs |
| BB103 | 10 | Batting Glove-Wilson |
| BB102 | 1 | Batting Glove, Saranac |
| BB101 | 11 | Little League Bat |
| BB100 | 1 | Fielders Glove-Wilson, G. Brut |
| BB110 | 1 | Little League Baseballs, Box of 10 dozen |
| BB405 | 6 | WS Baseball Starter Inventory |

**bb401_2** (variant kit - 7 components):
Same as BB401 minus BB405.

**BB404** (smaller starter kit - 4 components):
| Child | Qty | Description |
|-------|:---:|-------------|
| BB102 | 2 | Batting Glove, Saranac |
| BB101 | 1 | Little League Bat |
| BB103 | 1 | Batting Glove-Wilson |
| BB110 | 1 | Little League Baseballs, Box of 10 dozen |

**BB110** (nested BOM - 1 component):
| Child | Qty | Description |
|-------|:---:|-------------|
| BB105 | 10 | Little League Baseballs |

> **Note:** BB110 is both a parent (contains BB105) AND a child (used in BB401/BB404) — demonstrating nested BOM support.

### Management Commands

```bash
# Seed test BOM data (clears existing, inserts baseball kit data)
python manage.py seed_sample_bom

# Dry run (preview without changes)
python manage.py seed_sample_bom --dry-run

# Import from TSV file
python manage.py import_bom_tsv path/to/bom.tsv
```

### Source Data

Test data files in `readmes/topics/inventory/`:
- `bom_parent.json` - Parent items with `BomHasChild=True`
- `bom_children.json` - Component relationships
