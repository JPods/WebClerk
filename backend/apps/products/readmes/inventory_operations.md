# Inventory — Operations Guide
**Built:** 2026-07-04 | **Source:** WC2 INVT_dInvtApply, Invent_LIFOFIFO, TallyInventoryProcess mining

---

## Overview

Inventory is managed through layers — each layer is a quantity at a cost at a location. Layers accumulate on receipt, erode on issue, and can be split or transferred. Four costing methods: average, last, FIFO, LIFO — configurable per item. Margin velocity computed nightly on every item.

**Terminology:** Layer, not stack. Layers accumulate, erode, split. Stack implies push/pop which is wrong for inventory that gets partially consumed and transferred.

---

## Data Model

```
InventoryLayer (one per receipt lot)
  ├── item FK                → which product
  ├── warehouse FK           → where it is
  ├── quantity               → JSON: {received, issued, scrapped}
  ├── cost                   → JSON: {unit_po, landed, freight, duty, handling, vat,
  │                                    moving_avg, fifo_snapshot, lifo_snapshot, trend_pct}
  ├── lot                    → lot/batch number
  ├── serial_numbers         → list of serial numbers in this layer
  ├── source_doc_type/id     → PO, WO, adjustment that created this
  ├── source                 → JSON: lineage tracking
  ├── refs.links             → {parent_layer_id, child_layer_ids, split_from, transfer_id}
  └── is_locked              → when true, issues queue to PendingInventoryAdjustment

InventoryMovement (append-only ledger)
  ├── item FK, warehouse FK, inventory_layer FK
  ├── movement_type          → receipt | issue | adjust
  ├── quantity               → signed: positive=in, negative=out
  ├── reason, source_doc_type/id

SiteInventory (rollup per item+site)
  ├── item FK, site_code
  └── quantity               → JSON: {on_hand}

Warehouse (location)
  ├── name, code, site_code
  ├── location               → JSON: physical address
  └── count                  → JSON: {value, aisle, column, shelf, bin, counted_by, dt_counted, deviation}
```

---

## Four Costing Methods

Per-item via `item.config.costing_method` (default: average):

| Method | How It Works | When to Use |
|---|---|---|
| **Average** | Weighted avg across all layers | Default — general merchandise |
| **Last** | Newest layer's unit cost | Market pricing — what you'd pay today |
| **FIFO** | Consume oldest layers first | Perishables, first-expire-first-out |
| **LIFO** | Consume newest layers first | Tax optimization (in jurisdictions that allow it) |

```python
# Consume using the item's configured method:
total_cost, batch_id = consume_by_item_method(item_id=250, qty=Decimal('10'))
```

---

## Core Operations (13 services)

| Service | What It Does |
|---|---|
| `create_layer` | Receipt → new layer at landed cost (freight+duty computed at create time) |
| `consume_fifo` | Walk layers oldest→newest, drain qty, accumulate cost |
| `consume_lifo` | Walk layers newest→oldest |
| `consume_by_item_method` | Reads item.config.costing_method, dispatches to fifo/lifo/avg |
| `recalc_average_cost` | Weighted avg across all layers → updates item.cost.avg |
| `split_layer` | One layer → N layers at different locations (lineage in refs.links) |
| `transfer_layer` | Move between warehouses — atomic (both sides or neither) |
| `get_count_sheet` | Generate count sheet — blind mode hides expected qty |
| `record_count` | Compare expected vs actual, post adjustment if variance |
| `classify_abc` | A/B/C by margin velocity for cycle count scheduling |
| `compute_margin_velocity` | Per-item: (margin% × turns) |
| `update_item_margin_velocity` | Store velocity on Item fields (nightly by Alice) |
| `check_orphaned_events` | Find unprocessed movements older than 1 hour |
| `tally_site_buckets` | Rebuild SiteInventory rollups from current layers |

---

## WC2 Bug Fixed

WC2's `Invent_LIFOFIFO` didn't accumulate cost when a layer was partially consumed — the cost of the last partial drain was lost. WC3 fixes this: every unit drained contributes to total_cost regardless of full or partial consumption.

---

## Layer Split & Transfer

**Split:** One layer becomes N layers at different locations. Original layer is drained. Each child carries `refs.links.parent_layer_id` and `refs.links.split_from`. Parent carries `refs.links.child_layer_ids`.

**Transfer:** Move qty from warehouse A to warehouse B. Atomic — wrapped in `@transaction.atomic`. Creates paired InventoryMovement records with same transfer_id. If either side fails, both roll back.

---

## Counting Workflow

1. `get_count_sheet(warehouse_id, blind=True)` — generates list with item, location, QR code. Phase 1: no expected qty shown (prevents bias).
2. Operator scans QR → opens JSON viewer showing the layer.
3. Operator enters actual count + explanation.
4. `record_count(layer_id, actual_qty, explanation)` — compares, posts adjustment movement if variance.
5. Phase 2: reveal expected qty, show variance.

ABC classification drives count schedule:
- A items (top 20% by velocity): count weekly
- B items (middle 30%): count monthly
- C items (bottom 50%): count quarterly

---

## Margin Velocity (4 real Item fields)

```
margin_velocity   — (margin% × turns/year) — higher = better capital use
margin_pct        — (sale_price - cost_avg) / cost_avg × 100
annual_turns      — units issued / avg on-hand, annualized
velocity_category — dead_capital | volume_driver | star | normal
```

All four are indexed, sortable, filterable in DataBrowser. Alice computes nightly.

Categories:
- **Star:** >20% margin, >20 turns — best items, protect supply
- **Dead capital:** >50% margin, <2 turns — money sitting on shelves
- **Volume driver:** <10% margin, >50 turns — protect availability, never stock out

---

## Negative Inventory

When consumption exceeds available layers, the system:
1. Creates a synthetic deficit layer at average cost
2. Creates an Action alert: "BB005 went negative — investigate"
3. Does NOT block the transaction

The Action drives investigation. The deficit layer covers accounting.

---

## Reservation Integration

`InventoryReservation` holds inventory without touching the layer:
- `reserve_for_order()` — FIFO allocation across layers on order confirm
- `commit_order_reservations()` — converts to real issue on ship
- `release_order_reservations()` — releases on cancel
- Replaces WC2's non-journalable invoice hack

---

## 10 Improvements Over WC2

1. Partial-consume bug fixed
2. Per-item costing method (not global)
3. Layer lineage via refs.links
4. ABC classification for cycle counting
5. Two-phase blind counting
6. Negative inventory creates Action alert
7. Pending event heartbeat monitoring
8. Landed cost computed at receipt time
9. Transfers are atomic
10. Margin velocity as real fields

---

## Files

| File | Purpose |
|------|---------|
| `apps/products/models/inventory_layer.py` | InventoryLayer, SiteInventory, InventoryMovement, PendingInventoryAdjustment |
| `apps/products/models/warehouse.py` | Warehouse with W-A-C-S-B location hierarchy |
| `apps/products/services/inventory_services.py` | 13 operations |
| `apps/products/services/inventory_reservations.py` | Order allocation workflow |
| `apps/products/models/inventory_reservation.py` | Reservation model with commit/release/expire |
