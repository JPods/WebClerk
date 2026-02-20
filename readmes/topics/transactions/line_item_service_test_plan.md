# LineItemService End-to-End Test Plan

## Related Documentation

- [Transaction Line Save Architecture](transaction_line_save.md) - How lines are saved via `/wcapi/save/`
- [Inventory Deltas](../inventory/inventory_deltas.md) - How pending records affect inventory

## Scope

Tests LineItemService across all transaction types to verify pending inventory records are created correctly.

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

Quantity baseline: `placed = 3`

## Test Scenarios

### 1. Line Add (New Line)

**Test:** Create new transaction line
**Expected:** Pending record created with positive quantity in appropriate bucket

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

### 2. Line Quantity Change

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

### 3. Line Delete

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
- [ ] Pending created on add with correct `type_id`
- [ ] Pending has correct quantity bucket populated
- [ ] Delta pending created on quantity update
- [ ] Negative pending created on delete
- [ ] `item_id` matches line item
- [ ] `line_id` references the transaction line
- [ ] `doc_pk` references the parent transaction

## Verification Query

```python
from apps.core.models.pending import Pending

# Check pending records for a specific item
for p in Pending.objects.filter(record_id=246).order_by('-id')[:10]:
    data = p.data or {}
    print(f"ID: {p.id}, type_id={data.get('type_id')}, "
          f"on_so={data.get('on_so')}, on_po={data.get('on_po')}, "
          f"on_p={data.get('on_p')}, reason={data.get('reason')}")
```

## Test Results Template

| Transaction | Add Pending | Delta Pending | Delete Pending | Type Code | Bucket |
|-------------|-------------|---------------|----------------|-----------|--------|
| Order | ✅/❌ | ✅/❌ | ✅/❌ | SO | on_so |
| Invoice | ✅/❌ | ✅/❌ | ✅/❌ | IN | on_in |
| Proposal | ✅/❌ | ✅/❌ | ✅/❌ | PP | on_p |
| Purchase | ✅/❌ | ✅/❌ | ✅/❌ | PO | on_po |
| WorkOrder | ✅/❌ | ✅/❌ | ✅/❌ | WO | on_wo |

---

*Last verified: 2026-02-01*

