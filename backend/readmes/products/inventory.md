# Inventory & Costing Overview

## TL;DR

InventoryLayer holds per-receipt quantity & cost JSON. If a stack is locked or insufficient, issues enqueue as PendingInventoryAdjustment. Unlock or periodic processor drains queue FIFO, applying issues. Use `process_pending_inventory` (global) or `process_pending_for_stack` (single) or rely on automatic unlock signal. Cost JSON has stable keys (unit_po, landed, moving_avg, etc.) for downstream valuation and reporting.

---

## Concepts

- **InventoryLayer**: A received quantity "layer" for an Item at a Warehouse (lot/serial group). Tracks received, issued, scrapped quantities in a JSON `quantity` field and a standardized per-unit costing JSON `cost`.
- **SiteInventory**: Lightweight roll-up bucket per (Item, site_code) for fast availability queries (future use; currently scaffold).
- **PendingInventoryAdjustment**: Queue record for deferred inventory issues when a stack is locked (`is_locked=True`) or temporarily insufficient.

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

Per-unit unless noted.

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
| scrap_cost | Accumulated per-unit equivalent cost of scrapped qty (alloc basis) |
| trend_pct | Percent change vs baseline (prior moving_avg or explicit) |
| currency | 3-letter ISO code |
| exchange_rate | Currency → base conversion rate (1 if already base) |

Factory: `apps.products.models.inventory_layer.default_cost()`.

---

## Inventory Delta System (dInventory)

Instead of immediately updating item quantities when transactions occur, the system creates "delta" records that represent quantity changes. These deltas are processed periodically to update actual item inventory levels.

> **Pending Policy:** All inventory quantity changes create a Pending record — always, even if the item is unlocked. See `readmes/pending-policy.md` Rule 1.

### Inventory Quantity Buckets

Items track multiple quantity buckets in the `Item.quantity` JSON field:

**Core Quantities:**

| Field | Description | Changed By |
|-------|-------------|------------|
| `on_hand` | Physical inventory available | Receipts (+), Invoices (-), Adjustments (+/-) |
| `allocated` | Reserved/committed for orders | Allocation process |
| `available` | Computed: on_hand - allocated | Derived |

**Transaction Tracking Quantities:**

| Field | Type Code | Description | Transaction |
|-------|-----------|-------------|-------------|
| `on_so` | SO | On Sales Orders | Order line add/change/delete |
| `on_po` | PO | On Purchase Orders | Purchase line add/change/delete |
| `on_p` | PP | On Proposals | Proposal line add/change/delete |
| `on_wo` | WO | On Work Orders | WorkOrder line add/change/delete |

**Informational Quantities (Track Totals):**

| Field | Type Code | Description |
|-------|-----------|-------------|
| `on_in` | IN | Invoiced quantity (informational; actual change flows through on_hand) |
| `on_r` | RC | Received quantity (informational; actual change flows through on_hand) |

### Key Rules

- `on_hand` is only affected by **physical goods movement**: Purchase Receipt (+), Invoice/Shipment (-).
- **Order creation does NOT affect `on_hand`** — it only affects committed quantities (`on_so`).
- `on_so` tracks sales commitments: Sales Order (+), Invoice (-).
- `on_po` tracks purchase commitments: Purchase Order (+), Purchase Receipt (-).

### Pending Purposes Handled

| Purpose | Source | Description |
|---------|--------|-------------|
| `inventory_line_add` | LineItemService | New transaction line added |
| `inventory_qty_change` | LineItemService | Line quantity changed |
| `inventory_line_delete` | LineItemService | Line deleted |
| `inventory_cost_change` | LineItemService | Line cost changed |
| `receipt_line_add` | Receipt creation | Direct receipt (not through LineItemService) |

### Processing Deltas

```bash
python manage.py process_inventory_deltas --batch-size=1000
python manage.py process_inventory_deltas --dry-run
python manage.py process_inventory_deltas --item-id=123
```

Processing logic:
1. Query unprocessed Pending records (`dt_processed=0`)
2. Group by Item
3. Calculate net changes per bucket
4. Update `Item.quantity` atomically (using `select_for_update()`)
5. Mark deltas processed

### Delta Sign Convention

- **Positive Delta**: Increases the quantity type
- **Negative Delta**: Decreases the quantity type
- **Returns**: Use negative source quantities to generate appropriate delta signs

### Handling Returns and Negative Quantities

Sales returns: negative quantities on sales order lines create negative `quantity_on_order_delta`. When invoiced with negative quantity, creates positive `quantity_on_hand_delta` (stock returned).

Purchase returns: negative quantities on purchase order lines create negative `quantity_on_po_delta`.

---

## Locking & Deferred Issues

Some operations (adjustment, recount, cost revaluation) set `InventoryLayer.is_locked=True` to prevent direct quantity mutation. During a lock, attempts to issue stock call `stack.issue_or_enqueue(qty)`:

1. If locked OR insufficient remaining, a `PendingInventoryAdjustment` row is created (state `pending`).
2. If unlocked and sufficient, quantity is applied immediately (no queue record).

Unlock flow: When `is_locked` transitions True → False, a post-save signal schedules processing of that stack's pending rows (FIFO). Each row either applies (marking issued) or remains pending if still locked/insufficient.

Manual / periodic drain:
```bash
python manage.py process_pending_inventory --limit 200
```

Celery task: `products.tasks.process_pending_inventory` (schedule via beat every minute).

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

1. **Global**: `process_pending_inventory(limit=100, apply_insufficient=False, cancel_on_insufficient=False, dry_run=False)`
2. **Single stack**: `process_pending_for_stack(stack_id, ...)` (used by unlock signal)

Options:
- `apply_insufficient`: force application even if remaining < qty (would drive negative remaining; default False)
- `cancel_on_insufficient`: cancel rows that cannot be applied (instead of retrying later)
- `dry_run`: simulate without persistence

Reservation Interaction: The issuer treats active pending reservations as reducing available quantity. If `(remaining_qty - active_reserved) < request_qty` the adjustment is enqueued with reason `reserved_conflict`. Both global and per-stack processors skip these rows until reservations expire or are explicitly released. Force override: `apply_insufficient=True` also bypasses reservation protection (use sparingly).

---

## Reservations (Soft Holds)

`InventoryReservation` provides short-lived soft holds (cart/seat reservations) that reduce logical availability without immediately issuing quantity.

Lifecycle:

1. Create reservation (state=pending) if `remaining_qty - active_reserved >= qty`.
2. Availability = `remaining_qty - sum(active pending reservations)`.
3. Commit: convert to real issue (marks stack issued, state=committed).
4. Release (canceled) or Expire: state updated, availability restored.
5. Expiration driven by `expires_at`; periodic task / command reclaims expired rows.

Key API (service functions in `inventory_reserve.py`):

- `create_reservation(layer, qty, ttl_seconds=86400)`
- `availability_for_layer(layer)`
- `availability_for_item(item_id, warehouse_id=None)`
- `reserve_for_order(item_id, qty, order_id=None, ...)`
- `release_expired(batch=500)`

States: pending, committed, canceled, expired.

### Reservation REST Endpoints

Base path prefix: `/products/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/products/inventory/availability/<stack_id>/` | GET | Returns remaining vs available (minus active reservations) |
| `/products/inventory/reservations/` | POST | Create reservation (body: stack_id, qty, ttl_seconds?, reason?, ctx?) |
| `/products/inventory/reservations/action/` | POST | Commit or release (body: reservation_id, action=commit\|release, reason?) |

Management command: `python manage.py expire_inventory_reservations`

Celery beat entries:

| Purpose | Task | Default Schedule |
|---------|------|------------------|
| Drain pending adjustments | `products.tasks.process_pending_inventory` | every minute |
| Expire stale reservations | `products.tasks.expire_inventory_reservations` | every minute |

---

## Cost Update Helper

`InventoryLayer.update_cost_after_receipt(unit_po, freight=0, duty=0, handling=0, vat=0, prior_moving_avg=None, trend_baseline=None)` populates/adjusts cost JSON. Caller provides weighted moving average math externally.

---

## Inventory Receiving Functions

The system provides three specialized functions for receiving inventory in `apps/transactions/services/flow.py`:

| Function | Use Case | On-Hand Effect |
|----------|----------|----------------|
| `receive_purchase(po, receipt_id, lines)` | Receiving goods from vendors | +qty, -on_po |
| `complete_workorder(wo, receipt_id, lines)` | Completing manufacturing | +qty, -on_wo |
| `adjust_inventory(adjustment_id, lines, notes)` | Manual adjustments | +/-qty |
| `receive_inventory_changes(source_type, source, receipt_id, lines)` | High-level dispatcher | Routes to above |

### receive_purchase

```python
from apps.transactions.services.flow import receive_purchase, ReceiveLine
lines = [ReceiveLine(po_line_id=123, qty=10, warehouse_code='MAIN', unit_cost=15.00)]
result = receive_purchase(po, 'RCV-2025-001', lines)
# Result: {'receipt_id': 456, 'stacks_created': [789], 'deltas_created': 1}
```

Effects: Creates Receipt record, creates InventoryLayer per line, creates Pending delta (+on_hand, -on_po).

### complete_workorder

```python
from apps.transactions.services.flow import complete_workorder, CompleteWorkOrderLine
lines = [CompleteWorkOrderLine(wo_line_id=123, qty_completed=50, warehouse_code='FG')]
result = complete_workorder(wo, 'WO-COMP-2025-001', lines)
```

Effects: Creates Receipt record, creates InventoryLayer, creates Pending delta (+on_hand, -on_wo).

### adjust_inventory

```python
from apps.transactions.services.flow import adjust_inventory, AdjustmentLine
lines = [
    AdjustmentLine(item_id=100, qty_delta=5, warehouse_code='MAIN', reason='cycle_count'),
    AdjustmentLine(item_id=101, qty_delta=-2, warehouse_code='MAIN', reason='damage'),
]
result = adjust_inventory('ADJ-2025-001', lines, notes='Monthly cycle count')
```

Effects: Creates Receipt record, creates InventoryLayer for positive adjustments, creates Pending delta (+/-on_hand).

---

## Purchase Order Receiving (REST)

Endpoint: `POST /transactions/purchase-orders/<pk>/receive/`

Request body:
```json
{
  "receipt_id": "RCPT-2025-0001",
  "lines": [
    {"po_line_id": 123, "qty": 5, "warehouse_code": "MAIN", "unit_cost": 12.5, "lot": "LOT-A", "serial_batch": ""}
  ]
}
```

Behavior: Validates PO header and lines, resolves Item from PO line JSON, looks up Warehouse by code, creates InventoryLayer per received line, updates cost, increments PO line `quantity.received` hint.

Not idempotent — repeated calls create additional stacks. Call once per receipt. Lot/serial fields are optional.

---

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

Query parameters: `as_of=YYYY-MM-DD` (effectivity filtering), `revision=CODE` (filter to revision).

### Management Commands

```bash
python manage.py seed_sample_bom [--dry-run]
python manage.py import_bom_tsv path/to/bom.tsv
```

---

## Operational Metrics & Monitoring

### JSON Metrics Endpoint

Path: `/products/inventory/metrics/`

Response includes: reservations (counts, qty, TTL analytics), pending_adjustments, stacks (total, locked, remaining, received), protection (reserved_vs_remaining_pct), processor_runs (latest summaries, duration buckets).

### Prometheus Endpoint

Path: `/products/inventory/metrics/prometheus`

Auth: `INVENTORY_PROMETHEUS_REQUIRE_AUTH` (default True). Exports inventory_reservations_*, inventory_pending_*, inventory_stacks_*, inventory_processor_* gauges and histogram buckets.

---

## Testing

> **Scope Note**: The testing plan addresses **inventory quantity tracking** (on_so, on_po, on_wo, on_hand buckets). Reserved inventory (lot/serial assignment, warehouse allocation, FIFO/LIFO layer selection, backorder management) is a separate future phase.

### Transaction Flow Summary

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Proposal   │───>│    Order    │───>│   Invoice   │
│  (Forecast) │    │  (Commit)   │    │   (Ship)    │
│   +on_p     │    │   +on_so    │    │ -on_so      │
└─────────────┘    └─────────────┘    │ -on_hand    │
                                      └─────────────┘

┌─────────��───┐    ┌─────────────┐
│  Purchase   │───>│   Receipt   │
│  (Expect)   │    │  (Receive)  │
│   +on_po    │    │ -on_po      │
└─────────────┘    │ +on_hand    │
                   └─────────────┘

┌─────────────┐    ┌─────────────┐
│  WorkOrder  │───>│   Receipt   │
│  (Reserve)  │    │ (Complete)  │
│   +on_wo    │    │ -on_wo      │
└─────────────┘    │ +on_hand    │
                   └─────────────┘
```

### Pending Record Strategy

Each transaction is responsible for its own inventory impact (Option 2 — two pending records):

| Transaction | Pending Created | Inventory Impact |
|-------------|-----------------|------------------|
| Proposal Add Line | Yes (PP) | `+on_p` (x probability) |
| Order Add Line | Yes (SO) | `+on_so` |
| Invoice Add Line | Yes (IN) | `-on_so`, `-on_hand` |
| Purchase Add Line | Yes (PO) | `+on_po` |
| WorkOrder Add Line | Yes (WO) | `+on_wo` |
| Receipt Add Line | Yes (RC) | `-on_po` or `-on_wo`, `+on_hand` |

### Smoke Test

```bash
python manage.py shell -c "from apps.products.models.inventory_layer import InventoryLayer, PendingInventoryAdjustment; from apps.products.models.item import Item; from apps.products.models.warehouse import Warehouse; from decimal import Decimal; i=Item.objects.create(name='DocItem'); w=Warehouse.objects.create(name='Main', code='MAIN'); s=InventoryLayer.objects.create(item=i, warehouse=w, quantity={'received':50}); s.is_locked=True; s.save(); s.issue_or_enqueue(Decimal('10')); s.is_locked=False; s.save(); print(list(PendingInventoryAdjustment.objects.filter(stack=s).values_list('state', flat=True)))"
```

Expected: `['applied']` and remaining qty 40.

---

## Design Rationale

Why queue instead of blocking:
- Avoid holding transactions open waiting for long-running recount or valuation tasks.
- Provide observability (pending rows) instead of silent retries.
- Enable force-apply or cancel policies without changing call sites.

Why JSON fields for quantity/cost:
- Flexibility for incremental enrichment without migration churn.
- Low cardinality updates; entire document small.
- Future: could project critical fields to materialized columns / views if needed for analytics.

---

## Roadmap / Next Steps

- Batch recompute of moving average across historical layers (service + command).
- Optional negative prevention: auto-cancel pending rows after timeout if insufficient.
- Movement ledger integration (`InventoryMovement`) for full audit trail.
- SiteInventory synchronization logic on every applied issue/receipt.
- Cost roll-up into `Item.cost` (components.avg / components.last sync).
- Real-time processing option for immediate delta processing.
- Delta compression: merge multiple deltas for the same item.
- Warehouse-specific deltas.

## Quick Reference

| Action | Path |
|--------|------|
| Management command | `process_pending_inventory` |
| Celery task | `products.tasks.process_pending_inventory` |
| Signal auto-run | InventoryLayer post-save (unlock) |
| Single stack processor | `process_pending_for_stack` |
| Global processor | `process_pending_inventory` |

## Related Documentation

- [Transaction Line Save Architecture](../transactions/transaction_line_save.md) — How lines are saved and pending records created
- [LineItemService Test Plan](../transactions/line_item_service_test_plan.md) — Testing strategy for pending creation
