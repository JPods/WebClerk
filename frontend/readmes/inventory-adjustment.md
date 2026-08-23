# Inventory Adjustment & Pending Architecture

Established 2026-08-05. Documents the inventory adjustment system, the pending contract, and the lock lifecycle.

---

## The Pending Contract

**Inventory and cash never mutate directly.** Every change flows through a pending record first.

| Domain | Pending Model | Service |
|--------|--------------|---------|
| Inventory | `PendingInventoryAdjustment` | `inventory_adjustment_processor.py` |
| Payment | `PendingPaymentApplication` | `payment_pending.py` |

The pending record IS the audit trail. Whether the change applies in 1ms or waits an hour, the record of intent exists from the moment the request is made.

### The pattern

```
Caller requests change
    → Pending record created (STATE_PENDING)
    → If target unlocked: apply immediately, mark STATE_APPLIED
    → If target locked: pending waits for unlock drain
    → If insufficient: pending waits for replenishment
```

### Other models

Non-inventory, non-cash models use a different pattern: post directly if possible, create pending if the target is locked. The distinction: inventory and cash are **always pending** because the audit trail is non-negotiable.

---

## Lock Lifecycle

```
acquire_lock()
    → is_locked = True
    → dt_locked = now()

release_lock()
    → is_locked = False
    → dt_locked = None
    → process_pending_for_stack(pk)  ← drains the queue

check_lock_expired()
    → if now() - dt_locked > 300s: release_lock()

LifecycleMixin.lock() / unlock()
    → Overridden on InventoryLayer to call acquire_lock() / release_lock()
    → Admin lock = same pending contract
```

**Every unlock path drains pending.** There are no unlock paths that leave pending records behind.

### Management command

```bash
# Clear stale locks older than 5 minutes (default)
./manage.py clear_stale_locks

# Custom threshold
./manage.py clear_stale_locks --minutes 10

# Dry run — report without clearing
./manage.py clear_stale_locks --dry-run
```

Each cleared lock calls `release_lock()` which drains pending per stack.

---

## Backend API Endpoints

All under `/api/products/`:

| Method | Path | What it does |
|--------|------|-------------|
| POST | `inventory/adjust/` | Create adjustments. Always pending first. Body: `{warehouse_id, lines: [{item_id, qty, reason, notes}]}` |
| POST | `inventory/adjust-bom/` | BOM build/unbuild. Explodes children, adjusts all components + parent. Body: `{item_id, warehouse_id, qty, reason}` |
| GET | `inventory/adjustments/` | Adjustment history. Params: `item_id`, `warehouse_id`, `limit` |
| GET | `inventory/layers/` | FIFO/LIFO cost layers for an item. Params: `item_id` |

### Reason codes

`cycle_count`, `damage`, `return`, `shrinkage`, `correction`, `receipt`, `bom_build`, `bom_consume`, `other`

### BOM adjustment logic

- `qty > 0` = Build: consume children (negative), receive parent (positive)
- `qty < 0` = Unbuild: issue parent (negative), receive children (positive)
- Scrap factor applied to child quantities: `child_qty * (1 + scrap_factor)`

---

## Frontend Pages

### Desktop: Inventory Adjust (`/inventory-adjust`)

Based on WC2 `diaInvAdjust`. Spreadsheet-style page:

- Search items by number or keyword
- Warehouse selector (dropdown from active warehouses)
- Grid: Item | Description | Reason | Qty O/H | Adjust | New O/H | Cost
- Type adjustment qty (+/-) and select reason per row
- Apply button creates pending adjustments for all non-zero lines
- Green/red highlighting for positive/negative adjustments

In sidebar under "Adjust".

### Mobile: Cycle Count (`/cycle-count`)

Phone-sized page for warehouse workers:

- Scan bar with barcode/QR camera button (uses BarcodeDetector API)
- Scanned item auto-looks up and shows expected quantity from layers
- Card layout per item: Expected | Actual (input) | Variance
- Location and warehouse displayed per card
- Sticky Apply button at bottom
- All adjustments go through pending with reason `cycle_count`

### Item Dashboard Tabs

Two new tabs on the Item detail page (`/item/:id`):

**Layers tab** — `InventoryLayersPanel`
- FIFO/LIFO cost layers grouped by warehouse
- Columns: Lot, Rcvd, Issued, Remain, PO Cost, Landed, FIFO, LIFO, Avg, Ext Value, Source
- Lock indicator, depleted layers dimmed
- Warehouse subtotals (units + value)

**Counts tab** — `CycleCountPanel`
- Desktop version of cycle count for a single item
- Shows all active layers with system qty
- User enters counted qty, variance auto-calculated
- Apply button creates cycle_count adjustments

---

## Security (from Phase 1)

| Fix | Implementation |
|-----|---------------|
| Gateway response sanitization | `Payment.save()` strips PII via `sanitize_gateway_response()` whitelist. Non-staff get gateway fields removed from API. |
| API rate limiting | 100/min auth, 20/min anon, 10/min payment, 30/min webhook. `ScopedRateThrottle`. |
| Field-level access | `PaymentSerializer.to_representation()` strips sensitive fields for non-staff. |
| Audit trail | `add_audit_entry()` uses serializable ISO timestamps. |
| Lock timeout | `dt_locked` + 5-min auto-expire + management command. |

---

## Bug Fixes (from Phase 1)

| Bug | Fix |
|-----|-----|
| `po_totals.py` missing imports | Added `Decimal` and `cast` imports |
| Payment double-apply | `select_for_update()` on payment row |
| Orphaned inventory locks | `dt_locked` field + `clear_stale_locks` command |
| Parent-child cascade | Already correct — no fix needed |
| Multi-currency exchange_rate | Documented as placeholder for Phase 5 |

---

## WC2 Lineage

| WC2 (4D) | WC3 (Django + React) |
|-----------|---------------------|
| `diaInvAdjust` dialog | `InventoryAdjust.tsx` at `/inventory-adjust` |
| `Invt_dRecCreate` → array staging | `PendingInventoryAdjustment.objects.create()` |
| `INVT_dInvtApply` → DInventory records | `process_pending_for_stack()` on unlock |
| `TallyInventory` → recalculate | `layer.quantity` updated in place on apply |
| Single BOM / Multi BOM buttons | `POST /api/products/inventory/adjust-bom/` |
| `InvtAdjDiaSave` → save one item | Apply button → POST to `/api/products/inventory/adjust/` |

---

## File Map

### Backend (webClerk3)

| File | What |
|------|------|
| `apps/products/models/inventory_layer.py` | InventoryLayer (lock lifecycle, issue_or_enqueue), PendingInventoryAdjustment |
| `apps/products/views/inventory_adjustment_views.py` | 4 API views: adjust, adjust-bom, adjustments history, layers |
| `apps/products/services/inventory_adjustment_processor.py` | `process_pending_inventory()`, `process_pending_for_stack()` |
| `apps/products/management/commands/clear_stale_locks.py` | Stale lock cleanup command |
| `apps/products/urls.py` | URL routing for all inventory endpoints |
| `apps/transactions/services/payment_pending.py` | Always-pending payment application (the one path) |
| `apps/transactions/services/payment_application.py` | DEPRECATED — old direct path, kept for `unapply` and `get_status` |
| `apps/transactions/models/pending_payment.py` | PendingPaymentApplication model |
| `apps/transactions/models/payment.py` | Payment model with sanitize_gateway_response, save override |
| `apps/transactions/serializers/payment_serializers.py` | Field stripping for non-staff |
| `apps/transactions/views/payment_views.py` | ScopedRateThrottle on payment endpoints |
| `apps/transactions/services/po_totals.py` | Fixed missing Decimal/cast imports |
| `apps/products/migrations/0011_add_dt_locked_to_inventorylayer.py` | dt_locked migration |

### Frontend (React2025)

| File | What |
|------|------|
| `src/apps/products/pages/InventoryAdjust.tsx` | Desktop adjustment page |
| `src/apps/products/pages/CycleCountMobile.tsx` | Mobile cycle count with barcode scan |
| `src/apps/products/components/InventoryLayersPanel.tsx` | Item dashboard Layers tab |
| `src/apps/products/components/CycleCountPanel.tsx` | Item dashboard Counts tab |
| `src/apps/products/pages/ItemDetailJson.tsx` | Item dashboard (Layers + Counts tabs added) |
| `src/routes/Router.tsx` | Routes: `/inventory-adjust`, `/cycle-count` |
| `src/layout/AppSidebar.tsx` | "Adjust" added to sidebar |
