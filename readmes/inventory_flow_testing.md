# Inventory Flow Testing Plan

## Overview

This document captures our testing efforts and outlines the plan for testing inventory quantity flow across transaction types.

> **⚠️ Scope Note**: This plan addresses **inventory quantity tracking** (on_so, on_po, on_wo, on_hand buckets). We are **NOT yet addressing reserved inventory** - the allocation of specific inventory items/lots/locations to specific order lines. Reserved inventory is a separate concern that involves:
> - Lot/serial number assignment
> - Warehouse/bin location allocation  
> - FIFO/LIFO layer selection
> - Backorder management
> 
> Reserved inventory will be addressed in a future phase.

## Inventory Quantity Buckets

The `Item.quantity` JSONField tracks inventory across multiple buckets:

| Bucket | Description | Increases | Decreases |
|--------|-------------|-----------|-----------|
| `on_hand` | Physical inventory count | Receipt, Adjustment+ | Invoice (ship), Adjustment- |
| `on_so` | Reserved for Sales Orders | Order line add | Invoice (fulfills order) |
| `on_po` | Expected from Purchase Orders | Purchase line add | Receipt (from PO) |
| `on_wo` | Reserved for Work Orders | WorkOrder line add | Receipt (WO completion) |
| `on_p` | Forecast from Proposals | Proposal line add × probability | Order (converts proposal) |
| `available` | Computed: on_hand - on_so + on_po + on_wo | | |

## Transaction Flow Summary

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Proposal   │───▶│    Order    │───▶│   Invoice   │
│  (Forecast) │    │  (Commit)   │    │   (Ship)    │
│   +on_p     │    │   +on_so    │    │ -on_so      │
└─────────────┘    └─────────────┘    │ -on_hand    │
                                      └─────────────┘

┌─────────────┐    ┌─────────────┐
│  Purchase   │───▶│   Receipt   │
│  (Expect)   │    │  (Receive)  │
│   +on_po    │    │ -on_po      │
└─────────────┘    │ +on_hand    │
                   └─────────────┘

┌─────────────┐    ┌─────────────┐
│  WorkOrder  │───▶│   Receipt   │
│  (Reserve)  │    │ (Complete)  │
│   +on_wo    │    │ -on_wo      │
└─────────────┘    │ +on_hand    │
                   └─────────────┘
```

---

## Pending Record Strategy: Analysis

### The Question

When an Order is invoiced, we need to:
1. Release the Sales Order reservation (`-on_so`)
2. Record the invoice/shipment (`+on_in` if tracked)
3. Decrease physical inventory (`-on_hand`, `-available`)

**Should this be 1 or 2 pending records?**

### Option 1: Single Pending on Invoice Only

```
Order Save:   No pending record (reservation happens on invoice)
Invoice Save: One pending with -on_so, -on_hand, -available
```

**Pros:**
- Simpler - fewer pending records
- Atomic - all changes in one record

**Cons:**
- ❌ `on_so` doesn't reflect committed inventory until invoiced
- ❌ Loses visibility into order commitments
- ❌ Can't report "how much is reserved but not shipped?"
- ❌ Doesn't match business reality (order IS a commitment)

### Option 2: Two Pendings (Recommended ✓)

```
Order Save:   Pending with +on_so (commit inventory)
Invoice Save: Pending with -on_so, -on_hand (ship inventory)
```

**Pros:**
- ✅ Real-time accuracy: `on_so` always shows true committed inventory
- ✅ Clear audit trail: each transaction handles its own impact
- ✅ Business reality: order = commitment, invoice = fulfillment
- ✅ Reversibility: can undo order without touching invoice logic
- ✅ Reporting: can answer "what's committed but not shipped?"

**Cons:**
- More pending records (but they're small)

### Recommendation: Option 2

Each transaction should be responsible for its own inventory impact:

| Transaction | Pending Created | Inventory Impact |
|-------------|-----------------|------------------|
| Proposal Add Line | Yes (PP) | `+on_p` (× probability) |
| Order Add Line | Yes (SO) | `+on_so` |
| Invoice Add Line | Yes (IN) | `-on_so`, `-on_hand` |
| Purchase Add Line | Yes (PO) | `+on_po` |
| WorkOrder Add Line | Yes (WO) | `+on_wo` |
| Receipt Add Line | Yes (RC) | `-on_po` or `-on_wo`, `+on_hand` |

---

## Detailed Flow Tests

### 1. Sales Flow: Proposal → Order → Invoice

#### Step 1: Create Proposal with Line
```
Item 259 before: on_p=0, on_so=0, on_hand=100
Action: Add ProposalLine qty=10, probability=80%
Expected Pending: type=PP, on_p=+8 (10 × 0.80)
Item 259 after: on_p=8, on_so=0, on_hand=100
```

#### Step 2: Convert Proposal to Order (partial)
```
Item 259 before: on_p=8, on_so=0, on_hand=100
Action: Create Order from Proposal, OrderLine qty=5
Expected: 
  - ProposalLine.quantity.ordered=5, remaining=5
  - Pending: type=PP, on_p=-4 (release forecast for ordered qty)
  - Pending: type=SO, on_so=+5
Item 259 after: on_p=4, on_so=5, on_hand=100
```

#### Step 3: Invoice the Order (partial)
```
Item 259 before: on_p=4, on_so=5, on_hand=100
Action: Create Invoice from Order, InvoiceLine qty=3
Expected:
  - OrderLine.quantity.invoiced=3, remaining=2
  - Pending: type=IN, on_so=-3, on_hand=-3
Item 259 after: on_p=4, on_so=2, on_hand=97
```

### 2. Purchase Flow: Purchase → Receipt

#### Step 1: Create Purchase with Line
```
Item 259 before: on_po=0, on_hand=100
Action: Add PurchaseLine qty=20
Expected Pending: type=PO, on_po=+20
Item 259 after: on_po=20, on_hand=100
```

#### Step 2: Receive Purchase (partial)
```
Item 259 before: on_po=20, on_hand=100
Action: Create Receipt from Purchase, ReceiptLine qty=15
Expected:
  - PurchaseLine.quantity.received=15, remaining=5
  - Pending: type=RC, on_po=-15, on_hand=+15
Item 259 after: on_po=5, on_hand=115
```

### 3. WorkOrder Flow: WorkOrder → Receipt

#### Step 1: Create WorkOrder with Line
```
Item 259 before: on_wo=0, on_hand=100
Action: Add WorkOrderLine qty=10
Expected Pending: type=WO, on_wo=+10
Item 259 after: on_wo=10, on_hand=100
```

#### Step 2: Complete WorkOrder (partial)
```
Item 259 before: on_wo=10, on_hand=100
Action: Create Receipt (completion) from WorkOrder, qty=6
Expected:
  - WorkOrderLine.quantity.completed=6, remaining=4
  - Pending: type=RC, on_wo=-6, on_hand=+6
Item 259 after: on_wo=4, on_hand=106
```

---

## Test Status

### Completed Tests ✅

| Transaction | Line Add | Line Update | Line Delete | Pending Created |
|-------------|----------|-------------|-------------|-----------------|
| Order | ✅ | - | - | ✅ (SO) |
| Invoice | ✅ | - | - | ✅ (IN) |
| Proposal | ✅ | - | - | ✅ (PP) |
| Purchase | ✅ | - | - | ✅ (PO) |
| WorkOrder | ✅ | - | - | ✅ (WO) |
| Receipt | ✅ | - | - | ✅ (RC) |

---

## Test Run Results (Item 232)

### Test Date: 2026-02-03

**Test Script**: `test_inventory_flow_232.py`

**Flow Tested**:
1. Proposal (15 units) → Order (11 units) → Invoice (9 units)
2. Purchase (11 units) → Receipt (7 units)

**Results** (Combined Pending Records):

| Step | Transaction | Qty | Pending Type | Pending Values | Links | Status |
|------|-------------|-----|--------------|----------------|-------|--------|
| 1 | Proposal 70 | 15 | PP | `on_p=+15` | - | ✅ |
| 2 | Order 66 | 11 | SO | `on_so=+11` | - | ✅ |
| 3 | Invoice 45 | 9 | IN | `on_in=+9, on_so=-9, on_hand=-9` | `{order: {parent_id: 66}}` | ✅ |
| 4 | Purchase 46 | 11 | PO | `on_po=+11` | - | ✅ |
| 5 | Receipt 17 | 7 | RC | `on_r=+7, on_po=-7, on_hand=+7` | `{purchase: {parent_id: 46}}` | ✅ |

**Pending Records Created**: 5 (one per line) ✅

**Key Implementation Details**:

1. **Invoice from Order**: Single pending captures complete flow:
   - `on_in=+9` (track invoice)
   - `on_so=-9` (release order commitment)
   - `on_hand=-9` (deduct inventory)
   - `links.order.parent_id` documents lineage

2. **Receipt from Purchase**: Single pending captures complete flow:
   - `on_r=+7` (track receipt)
   - `on_po=-7` (release purchase commitment)
   - `on_hand=+7` (add inventory)
   - `links.purchase.parent_id` documents lineage

3. **Receipt from WorkOrder**: (not tested yet) Will capture:
   - `on_r=+qty` (track receipt)
   - `on_wo=-qty` (release workorder commitment)
   - `on_hand=+qty` (add completed inventory)
   - `links.workorder.parent_id` documents lineage

**Net Effect After Processing** (example run):
- `on_p`: +15 (proposal forecast)
- `on_so`: +11 - 9 = +2 (remaining order commitment)
- `on_po`: +11 - 7 = +4 (remaining purchase commitment)
- `on_hand`: 100 - 9 + 7 = 98 (starting - invoiced + received)

---

### Pending Tests 🔄

1. **Parent-Child Linking**
   - [ ] Order.parent_id links to Proposal
   - [ ] Invoice.parent_id links to Order
   - [ ] Receipt.purchase_id links to Purchase
   - [ ] Receipt.workorder_id links to WorkOrder

2. **Quantity Cascade**
   - [ ] OrderLine updates ProposalLine.quantity.ordered/remaining
   - [ ] InvoiceLine updates OrderLine.quantity.invoiced/remaining
   - [ ] ReceiptLine updates PurchaseLine.quantity.received/remaining
   - [ ] ReceiptLine updates WorkOrderLine.quantity.completed/remaining

3. **Dual Pending on Invoice/Receipt**
   - [ ] Invoice creates pending to release on_so AND decrease on_hand
   - [ ] Receipt creates pending to release on_po/on_wo AND increase on_hand

4. **Pending Processor**
   - [ ] Verify PendingInventoryProcessor applies changes correctly
   - [ ] Verify Item.quantity buckets update atomically

---

## Implementation Notes

### Current State

The `LineItemService` creates pending records for new lines:
- `_create_pending_for_new_line()` handles initial commitment
- Pending record includes: `type_id`, `item_id`, `doc_id`, `line_id`, quantity buckets

### Needed Enhancements

1. **Invoice/Receipt Release Logic**
   - When creating invoice line from order: release on_so in same pending
   - When creating receipt line from purchase: release on_po in same pending
   - When creating receipt line from workorder: release on_wo in same pending

2. **Parent Line Update**
   - Track `quantity.ordered`, `quantity.invoiced`, `quantity.received`, `quantity.completed`
   - Calculate `quantity.remaining` automatically

3. **Available Calculation**
   - `available = on_hand - on_so + on_po + on_wo`
   - Update after each pending is processed

---

## Test Commands

```bash
# Check latest pending records
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()
from apps.core.models import Pending
for p in Pending.objects.order_by('-id')[:10]:
    print(f'ID:{p.id} model={p.model_name} data={p.data}')
"

# Check item quantity buckets
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()
from apps.products.models import Item
item = Item.objects.get(pk=259)
print(f'Item {item.ida}: {item.quantity}')
"

# Process pending inventory
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()
from apps.transactions.services.pending_inventory_processor import process_pending_for_item
result = process_pending_for_item(259)
print(f'Processed: {result}')
"
```
