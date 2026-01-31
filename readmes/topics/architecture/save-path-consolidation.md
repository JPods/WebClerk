# Save Path Consolidation: Security & Inventory Tracking

**Created**: 2026-01-30  
**Updated**: 2026-01-30  
**Status**: Implemented (Signal Safety Net Active)  
**Priority**: High (Security)

## Problem Statement

Transaction line records (OrderLine, InvoiceLine, PurchaseLine, etc.) can be created through **multiple code paths**, each bypassing centralized business logic:

1. **`/wcapi/save/`** → `SaveWcapiView._perform_save()` - Two separate line-handling blocks
2. **`/wcapi/transaction/save/`** → `WCAPITransactionSaveView` → `transaction_save.py`
3. **`/api/transactions/orders/`** → `OrderViewSet` (DRF)
4. **`/api/tx/order/<id>/lines/`** → `TransactionLineListCreate` (unified views)
5. **Direct ORM** in various service files (`proposal_to_order.py`, `flow.py`, etc.)

### Security Implications

- **Audit bypass**: Some paths may not log who created/modified records
- **Permission bypass**: Different endpoints may have inconsistent permission checks
- **Business logic bypass**: Inventory tracking, validation, and hooks may be skipped
- **Data integrity**: Calculated fields may not be updated consistently

### Current State (2026-01-30)

**IMPLEMENTED:**
1. Patched inventory pending creation in 3 locations:
   - `apps/core/views/save_view.py` (2 places) - sets `_pending_created=True` flag
   - `apps/transactions/services/transaction_save.py`
   - `apps/transactions/services/line_item_service.py` (new `_create_pending_for_new_line` method)

2. **Signal Safety Net** added in `apps/transactions/signals.py`:
   - Catches ANY line creation that bypassed explicit pending creation
   - Checks for existing pending (prevents duplicates via DB query)
   - Respects `_pending_created` flag set by explicit callers

---

## Pending Inventory Processing

### Two-Phase Design

Line changes create `Pending` records which are then processed to update `Item` quantities:

```
Line Creation → Pending Record → [Processor] → Item.on_so/on_po/on_wo updated
```

**Why decouple?**
- Reduces lock contention on Item records during high transaction volume
- Allows batch processing for efficiency
- Provides audit trail of all inventory changes
- Enables retry on failure

### Configuration

Add to `webclerk3_api/settings.py`:

```python
# --- Inventory Pending Processing ---
INVENTORY_PENDING_PROCESS_DELAY = 5  # seconds between checks
INVENTORY_PENDING_BATCH_SIZE = 100   # records per batch
INVENTORY_PENDING_AUTO_PROCESS = True  # enable background processing
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
from apps.transactions.services.pending_inventory_processor import process_line_item_pending

# Process all unprocessed line item pending
result = process_line_item_pending(limit=100)
print(result)
# {'total_found': 2, 'processed': 2, 'skipped_locked': 0, ...}

# Process for specific item
from apps.transactions.services.pending_inventory_processor import process_pending_for_item
result = process_pending_for_item(item_id=240)
```

#### Celery Beat (Production)

```python
# In celery.py or tasks.py
from celery import shared_task

@shared_task
def process_inventory_pending_task():
    from apps.products.services.inventory_adjustment_processor import process_pending_inventory
    from apps.transactions.services.pending_inventory_processor import process_line_item_pending
    
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

## Recommended Architecture

### Option A: Django Signals (Quick Fix)

Use Django's `post_save` signal on line models to centralize inventory tracking:

```python
# apps/transactions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.transactions.models import OrderLine, InvoiceLine, PurchaseLine

@receiver(post_save, sender=OrderLine)
@receiver(post_save, sender=InvoiceLine) 
@receiver(post_save, sender=PurchaseLine)
def handle_line_save(sender, instance, created, **kwargs):
    if created:
        from apps.transactions.services.line_item_service import LineItemService
        service = LineItemService(create_pending=True)
        # Create pending from instance data
        service._create_pending_from_line_instance(instance)
```

**Pros**: Works regardless of save path  
**Cons**: Signal doesn't have request context (no user info), harder to debug

### Option B: Service Layer Pattern (Recommended)

Route ALL line creation through `LineItemService`:

```python
# All endpoints should use:
from apps.transactions.services.line_item_service import LineItemService

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

## Current Save Paths Inventory

| Endpoint | File | Line Creation Method | Inventory Pending? |
|----------|------|---------------------|-------------------|
| `/wcapi/save/` | `save_view.py:868` | Direct ORM | ✅ Patched |
| `/wcapi/save/` | `save_view.py:1706` | Direct ORM | ✅ Patched |
| `/wcapi/transaction/save/` | `transaction_save.py:373` | Direct ORM | ✅ Patched |
| `/api/transactions/orders/` | `order_views.py` | wcapi.save_item | ❓ Check |
| `/api/tx/order/<id>/lines/` | `unified.py:159` | serializer.save() | ❌ Not patched |
| Proposal→Order | `proposal_to_order.py:190` | Direct ORM | ❌ Not patched |
| Purchase→Order | `purchase_to_order.py:35` | Direct ORM | ❌ Not patched |
| Flow service | `flow.py:199` | Direct ORM | ❌ Not patched |

## Action Items

1. [ ] **Immediate**: Audit all paths in table above
2. [ ] **Short-term**: Implement Option A (signals) as safety net
3. [ ] **Medium-term**: Migrate to Option B (service layer)
4. [ ] **Long-term**: Add ESLint/Pylint rule to prevent direct ORM for lines

## Related Files

- `apps/core/views/save_view.py` - Main universal save endpoint
- `apps/transactions/services/transaction_save.py` - Transaction-specific save
- `apps/transactions/services/line_item_service.py` - Line item service (target)
- `apps/transactions/signals.py` - Existing signals
- `apps/transactions/views/unified.py` - Unified transaction views

## Testing Checklist

When consolidating save paths, verify:

- [ ] Adding line creates `Pending` record with correct `on_so`/`on_po`/`on_wo`
- [ ] Updating line quantity creates `Pending` with delta
- [ ] Deleting line creates `Pending` with negative quantity
- [ ] Inventory processor applies pending to `Item.quantity` JSON
- [ ] All paths enforce same permission checks
- [ ] Audit logs capture user who made changes
