# LineItemService End-to-End Test Plan

## Related Documentation

- [Transaction Line Save Architecture](transaction_line_save.md) - How lines are saved via `/wcapi/save/`
- [Inventory Deltas](../inventory/inventory_deltas.md) - How pending records affect inventory
- [Save Path Consolidation](../architecture/save-path-consolidation.md) - Dedup strategy & known issues

## Scope

Tests LineItemService across all transaction types to verify:
1. Exactly **one** pending inventory record is created per line operation
2. The correct quantity bucket is populated
3. Parent-to-child transfers (e.g., proposal → order) produce the right deltas on both sides

## Resolved: Collect-then-Create (2026-02-21)

Two rounds of consolidation:
1. Dead `_perform_save()` removed from `save_view.py` — single `post()` flow
2. `transaction_save.py` rewritten with **collect-then-create** pattern — signals suppressed, pending deltas collected during save loop, Pending records created afterwards, single dispatch

### Two Save Paths

| Endpoint | Pending Strategy | Used By |
|----------|------------------|---------|
| `/wcapi/save/` | Per-line via `LineItemService._create_pending_for_new_line()` | Generic saves, order deactivation |
| `/wcapi/transaction/save/` | Collect-then-create via `_create_pending_from_deltas()` | R25 transaction saves with lines |

### Transaction Save Flow (Collect-then-Create)

```
POST /wcapi/transaction/save/  { model_name: "invoice", record: { lines: [...] } }
  │
  ├── Phase 1 — Atomic save (signals suppressed)
  │   ├── transaction.atomic() begins
  │   │     ├── Verify R25 calculations against WC3 math
  │   │     ├── Save header (create or update)
  │   │     ├── For each dirty line:
  │   │     │     ├── Save line (create or update)
  │   │     │     ├── Set _pending_created = True (suppresses signal)
  │   │     │     └── Collect pending delta into pending_deltas[]
  │   │     └── (No Pending records created yet)
  │   └── transaction.atomic() commits
  │
  ├── Phase 2 — _create_pending_from_deltas()
  │   ├── Backend-authoritative: type from model_key, transfer from header
  │   ├── Stores (invoice_line_id, order_line_id) pair per record
  │   ├── In-memory + DB duplicate guard
  │   └── For IN-from-order: on_in=+qty, on_so=-qty, on_hand=-qty
  │
  ├── Phase 3 — Update source lines (transfer only)
  │
  └── Phase 4 — Single dispatch_pending_processing()
```

**Rule:** Backend is authoritative for all pending decisions. Celery only **applies** pending deltas to Item records.

## Pending Type Mapping

| Transaction Type | Model Name | Line Model | Type Code | Quantity Bucket |
|------------------|------------|------------|-----------|-----------------|
| Order | `order` | `OrderLine` | SO | on_so |
| Proposal | `proposal` | `ProposalLine` | PP | on_p |
| Invoice | `invoice` | `InvoiceLine` | IN | on_in |
| Receipt | N/A | N/A | RC | on_r |
| Purchase | `purchase` | `PurchaseLine` | PO | on_po |
| Work Order | `workorder` | `WorkOrderLine` | WO | on_wo |

**Note:** Invoice (IN) and Receipt (RC) also affect `on_hand`:
- Invoice: decreases on_hand (goods shipped)
- Receipt: increases on_hand (goods received)

## Test Items

| Item ID | IDA | Description |
|---------|-----|-------------|
| 246 | Test Item 1 | Test item for line operations |
| 247 | Test Item 2 | Test item for line operations |
| 248 | Test Item 3 | Test item for line operations |

Quantity baseline: `staged = 3`

## Test Scenarios

### 1. Line Add (New Line)

**Test:** Create new transaction line
**Expected:** Exactly ONE pending record created with positive quantity in appropriate bucket

```python
# Expected Pending.data structure
{
    "type_id": "SO",  # or PO, PP, IN, WO
    "item_id": 246,
    "line_id": <new_line_id>,
    "doc_pk": <transaction_id>,
    "on_so": 3.0,     # Positive quantity in correct bucket
    "reason": "so line add"
}
```

**Dedup assertion:** `Pending.objects.filter(data__line_id=line_id, purpose='inventory_line_add').count() == 1`

### 2. Line Add with Parent Transfer (Proposal → Order)

**Test:** Create order line from a proposal line (parent_model/parent_id set)
**Expected:** TWO pending records total:
- One for the **order line** (on_so += staged)
- One for the **proposal line** (transferred += staged, remaining -= staged)

```python
# Order line pending
{ "type_id": "SO", "item_id": 246, "on_so": 3.0, "reason": "so line add" }

# Proposal parent pending (quantity transfer)
{ "type_id": "PP", "item_id": 246, "on_p": -3.0, "reason": "pp transfer to order" }
```

**Dedup assertion:** No more than 1 pending per line_id per purpose.

### 3. Line Quantity Change

**Test:** Update existing line quantity (e.g., 3 → 5)
**Expected:** Delta pending record created with difference (+2)

```python
{
    "type_id": "SO",
    "item_id": 246,
    "line_id": <existing_line_id>,
    "on_so": 2.0,     # Delta (5 - 3 = +2)
    "reason": "so qty increase",
    "quantity_delta": 2.0
}
```

### 4. Line Delete

**Test:** Delete existing line
**Expected:** Negative pending record created to reverse original quantity

```python
{
    "type_id": "SO",
    "item_id": 246,
    "line_id": <deleted_line_id>,
    "on_so": -3.0,    # Negative to reverse
    "reason": "so line delete"
}
```

## Assertions

For each transaction type:
- [ ] Exactly ONE pending created on add (single flow in `post()`)
- [ ] Pending has correct `type_id` and quantity bucket populated
- [ ] Delta pending created on quantity update
- [ ] Negative pending created on delete
- [ ] `item_id` matches line item
- [ ] `line_id` references the transaction line
- [ ] `doc_pk` references the parent transaction
- [ ] Parent transfer produces pending for both child and parent lines
- [ ] All pending creation happens inside `transaction.atomic()` block

## Verification Query

```python
from apps.core.models.pending import Pending

# Check pending records for a specific item — watch for duplicates
for p in Pending.objects.filter(record_id=246).order_by('-id')[:10]:
    data = p.data or {}
    print(f"ID: {p.id}, type_id={data.get('type_id')}, "
          f"on_so={data.get('on_so')}, on_po={data.get('on_po')}, "
          f"on_p={data.get('on_p')}, reason={data.get('reason')}, "
          f"line_id={data.get('line_id')}")

# Duplicate detection query
from django.db.models import Count
dupes = (Pending.objects
    .filter(purpose='inventory_line_add', dt_processed__isnull=True)
    .values('data__line_id')
    .annotate(cnt=Count('id'))
    .filter(cnt__gt=1))
print(f"Duplicate pending records: {list(dupes)}")
```

## Test Results Template

| Transaction | Add (1 pending) | Parent Transfer | Delta Pending | Delete Pending | Type Code | Bucket |
|-------------|-----------------|-----------------|---------------|----------------|-----------|--------|
| Order | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | SO | on_so |
| Invoice | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | IN | on_in |
| Proposal | ✅/❌ | N/A | ✅/❌ | ✅/❌ | PP | on_p |
| Purchase | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | PO | on_po |
| WorkOrder | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | WO | on_wo |

---

*Last verified: 2026-02-21*

