# Save Path Consolidation: Security & Inventory Tracking

**Created**: 2026-01-30  
**Updated**: 2026-02-21  
**Status**: ✅ Implemented (Collect-then-create in transaction_save + Single post() flow + Signal Safety Net)  
**Priority**: High (Security)

## Flow Architecture

All transaction lines (OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine) flow through `LineItemService` for inventory tracking:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   DRF Views     │     │   save_view.py  │     │  Direct .save() │
│ (perform_*)     │     │                 │     │  (shell/tests)  │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ Sets _pending_created │ Sets _pending_created │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LineItemService                            │
│  - _create_pending_for_new_line()     (on create)              │
│  - _create_pending_for_qty_change()   (on update)              │
│  - _create_pending_for_line_delete()  (on delete)              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Signals (fallback only)                        │
│  Checks _pending_created flag - skips if already handled        │
│  Handles: PurchaseLine, WorkOrderLine                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pending Records                             │
│  model_name='inventory_delta'                                   │
│  purpose='inventory_line_add' | 'inventory_qty_change' |        │
│          'inventory_line_delete'                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Background Processor / Celery Task                 │
│  Updates Item.quantity.on_so / on_po / on_wo / on_hand          │
└─────────────────────────────────────────────────────────────────┘
```

### Receipt Flow (PO Receiving)

```
┌─────────────────┐
│  flow.py        │
│  receive_       │
│  purchase │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Creates Directly:                            │
│  - Receipt record (inventory_receipt table)                     │
│  - InventoryLayer (stack) per line                             │
│  - Pending record with:                                         │
│      quantity_on_hand_delta: +qty_received                      │
│      quantity_on_po_delta: -qty_received                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Problem Statement

Transaction line records (OrderLine, InvoiceLine, PurchaseLine, etc.) can be created through **multiple code paths**, each bypassing centralized business logic:

1. **`/wcapi/save/`** → `SaveWcapiView.post()` — single line-processing block (dead `_perform_save()` removed 2026-02-21)
2. **`/wcapi/transaction/save/`** → `WCAPITransactionSaveView` → `transaction_save.py`
3. **`/api/transactions/orders/`** → `OrderViewSet` (DRF)
4. **`/api/tx/order/<id>/lines/`** → `TransactionLineListCreate` (unified views)
5. **Direct ORM** in various service files (`proposal_to_order.py`, `flow.py`, etc.)

### Security Implications

- **Audit bypass**: Some paths may not log who created/modified records
- **Permission bypass**: Different endpoints may have inconsistent permission checks
- **Business logic bypass**: Inventory tracking, validation, and hooks may be skipped
- **Data integrity**: Calculated fields may not be updated consistently

---

## Current Implementation (2026-02-21)

### ✅ Two Save Paths with Explicit Pending Creation

| Endpoint | Handler | Pending Strategy | Key Location |
|----------|---------|------------------|--------------|
| `/wcapi/save/` | `save_view.py` `post()` | Per-line via `LineItemService._create_pending_for_new_line()` | ~L818 |
| `/wcapi/transaction/save/` | `transaction_save.py` `save_transaction_with_lines()` | **Collect-then-create** via `_create_pending_from_deltas()` | ~L487 |

**Transaction save (collect-then-create):** Lines saved with `_pending_created=True` inside atomic block (suppresses signals). Pending deltas collected into array. After commit, `_create_pending_from_deltas()` creates Pending records with `(invoice_line_id, order_line_id)` pair keys. Single `dispatch_pending_processing()` at end.

**Generic save:** Single line-processing block in `post()` with `_pending_created=True` flag, one `_create_pending_for_new_line()` per line.

> **Note:** The dead `_perform_save()` method was removed 2026-02-21.

### ✅ Signal Safety Net

Added in `apps/transactions/signals.py` - catches ANY line creation that bypassed explicit paths:

| Line Model | Signal Handler | Pending Type | Field Updated | DRF View Support |
|------------|----------------|--------------|---------------|------------------|
| OrderLine | `create_order_line_inventory_pending` | SO | `on_so` | ❌ (via save_view) |
| InvoiceLine | `create_invoice_line_inventory_pending` | IV | `invoiced` | ❌ (via save_view) |
| ProposalLine | `create_proposal_line_inventory_pending` | PP | `on_p` (forecast) | ❌ (via save_view) |
| PurchaseLine | `update_inventory_on_purchase_line_save` | PO | `on_po` | ✅ perform_create/update/destroy |
| WorkOrderLine | `update_inventory_on_workorder_line_save` | WO | `on_wo` | ✅ perform_create/update/destroy |

**Duplicate Prevention:**
1. Checks `_pending_created` flag (set before `.save()` by explicit paths)
2. Queries DB for existing pending with same `line_id`

### ✅ LineItemService Methods

| Method | Purpose |
|--------|---------|
| `_create_pending_for_new_line()` | Called by save_view.py for any line type |
| `_create_pending_for_line_add()` | Internal method for pending creation |
| `_create_pending_for_qty_change()` | Creates delta pending for quantity updates |

---

## Pending Inventory Processing

### Two-Phase Design

```
Line Creation → Pending Record → [Processor] → Item.on_so/on_po/on_wo updated
```

**Why decouple?**
- Reduces lock contention on Item records during high transaction volume
- Allows batch processing for efficiency
- Provides audit trail of all inventory changes
- Enables retry on failure

### Configuration

In `webclerk3_api/settings.py`:

```python
# --- Inventory Pending Processing ---
INVENTORY_PENDING_PROCESS_DELAY = 5  # seconds between daemon checks
INVENTORY_PENDING_BATCH_SIZE = 100   # records per batch
INVENTORY_PENDING_AUTO_PROCESS = False  # enable in production
```

### Processing Methods

#### Management Command (Unified)

```bash
# Process all pending inventory (stacks + line items)
python manage.py process_pending_inventory

# Process with options
python manage.py process_pending_inventory --limit=50 --dry-run

# Run as background daemon (checks every N seconds)
python manage.py process_pending_inventory --daemon --interval=5

# Process only line-item pending (skip stack adjustments)
python manage.py process_pending_inventory --skip-stacks

# Process only stack adjustments (skip line items)
python manage.py process_pending_inventory --skip-lines
```

#### Django Shell (Ad-hoc)

```python
from apps.transactions.services.inventory_pending_process import process_line_item_pending

# Process all unprocessed line item pending
result = process_line_item_pending(limit=100)
print(result)
# {'total_found': 2, 'processed': 2, 'skipped_locked': 0, ...}

# Process for specific item
from apps.transactions.services.inventory_pending_process import process_pending_for_item
result = process_pending_for_item(item_id=240)
```

#### Celery Beat (Production)

```python
# In celery.py or tasks.py
from celery import shared_task

@shared_task
def process_inventory_pending_task():
    from apps.products.services.inventory_adjustment_processor import process_pending_inventory
    from apps.transactions.services.inventory_pending_process import process_line_item_pending
    
    stack_result = process_pending_inventory(limit=100)
    line_result = process_line_item_pending(limit=100)
    return {'stacks': stack_result, 'lines': line_result}

# In CELERY_BEAT_SCHEDULE:
CELERY_BEAT_SCHEDULE = {
    'process-inventory-pending': {
        'task': 'apps.products.tasks.process_inventory_pending_task',
        'schedule': 5.0,  # every 5 seconds
    },
}
```

### Monitoring

Check pending queue depth:
```python
from apps.core.models import Pending
count = Pending.objects.filter(
    model_name='item',
    purpose__in=['inventory_line_add', 'inventory_qty_change', 'inventory_line_delete'],
    dt_processed=0
).count()
print(f"Pending inventory records: {count}")
```

---

## Future Architecture Options

### Option A: Django Signals ✅ IMPLEMENTED

Use Django's `post_save` signal on line models to centralize inventory tracking.
This is now active as a **safety net** for all line models.

**Pros**: Works regardless of save path  
**Cons**: Signal doesn't have request context (no user info), harder to debug

### Option B: Service Layer Pattern (Recommended for Future)

Route ALL line creation through `LineItemService`:

```python
# All endpoints should use:
from apps.transactions.services.line_manage import LineItemService

service = LineItemService(create_pending=True)
line = service.add_item_to_transaction(
    transaction=order,
    item_id=item_id,
    quantity=qty,
    # ... other fields
)
```

**Implementation Steps**:

1. **Deprecate direct ORM access** for transaction lines
2. **Update `save_view.py`** to call `LineItemService.add_item_to_transaction()`
3. **Update `transaction_save.py`** to call `LineItemService`
4. **Update DRF ViewSets** to use `LineItemService` in `perform_create()`
5. **Add linting rule** to flag direct `OrderLine.objects.create()` calls

### Option C: Model-Level Override (Alternative)

Override `save()` on line models to enforce business logic:

```python
class OrderLine(BaseSellLineModel):
    def save(self, *args, skip_inventory=False, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and not skip_inventory:
            self._create_inventory_pending()
```

**Pros**: Guaranteed to run on every save  
**Cons**: Circular import risks, harder to test

---

## Save Paths Status

| Endpoint | File | Line Creation | Pending Status |
|----------|------|---------------|----------------|
| `/wcapi/save/` | `save_view.py` post() | Direct ORM + flag | ✅ Single block + Signal |
| `/wcapi/transaction/save/` | `transaction_save.py` | Collect-then-create | ✅ Backend-authoritative, duplicate-pair guard |
| `/api/transactions/orders/` | `order_views.py` | wcapi.save_item | ✅ Signal catches |
| `/api/tx/order/<id>/lines/` | `unified.py:159` | serializer.save() | ✅ Signal catches |
| `/api/tx/purchase-lines/` | `line_views.py` | perform_create() | ✅ LineItemService |
| `/api/tx/workorder-lines/` | `line_views.py` | perform_create() | ✅ LineItemService |
| Proposal→Order | `proposal_to_order.py:190` | Direct ORM | ✅ Signal catches |
| Purchase→Order | `purchase_to_order.py:35` | Direct ORM | ✅ Signal catches |
| Flow service | `flow.py:199` | Direct ORM | ✅ Signal catches |
| PO Receiving | `flow.py:receive_purchase` | Direct Pending | ✅ Explicit |

---

## Action Items

- [x] **Immediate**: Signal safety net for all line types
- [x] **Short-term**: Explicit pending creation in save_view.py
- [x] **Short-term**: ProposalLine signal handler added
- [ ] **Medium-term**: Migrate all paths to use LineItemService
- [ ] **Long-term**: Add Pylint rule to prevent direct ORM for lines

---

## Related Files

- `apps/core/views/save_view.py` - Main universal save endpoint
- `apps/transactions/services/transaction_save.py` - Transaction-specific save
- `apps/transactions/services/line_item_service.py` - Line item service (target)
- `apps/transactions/signals.py` - Signal safety net handlers
- `apps/transactions/services/pending_inventory_processor.py` - Processes pending to Item
- `apps/products/management/commands/process_pending_inventory.py` - Management command

---

## Testing Checklist

When consolidating save paths, verify:

- [x] Adding line creates `Pending` record with correct `on_so`/`on_po`/`on_wo`
- [ ] Updating line quantity creates `Pending` with delta
- [ ] Deleting line creates `Pending` with negative quantity
- [x] Inventory processor applies pending to `Item.quantity` JSON
- [ ] All paths enforce same permission checks
- [ ] Audit logs capture user who made changes

### Verified Test Results (2026-01-31)

| Line ID | Item | Qty | Pending ID | on_so Before | on_so After |
|---------|------|-----|------------|--------------|-------------|
| 112 | 240 | 8 | 44 | 5.0 | 15.0 |
| 115 | 240 | 2 | 49 | 15.0 | 15.0* |
| 116 | 240 | 6 | 50 | 15.0 | 21.0 |

*Line 115 was part of batch with Line 112
