# Inventory Testing Plan - Item ID 240

## Purpose
Track and verify inventory behavior across the transaction lifecycle for **item_id=240**.

---

## Transaction Flow Overview

```
┌──────────┐    ┌───────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐
│ Proposal │ -> │ Order │ -> │ Purchase │ -> │ Invoice │ -> │ Receipt │
└──────────┘    └───────┘    └──────────┘    └─────────┘    └─────────┘
                    │              │
                    v              v
              ┌───────────┐  ┌───────────┐
              │ WorkOrder │  │  Pending  │
              └───────────┘  └───────────┘
```

---

## Inventory Fields to Monitor

### Item Record (apps.products.models.item.Item)
| Field | Description |
|-------|-------------|
| `quantity_on_hand` | Physical inventory available |
| `quantity_reserved` | Reserved for orders |
| `quantity_on_order` | Ordered from vendors (PO) |
| `quantity_available` | on_hand - reserved |

### Pending Records (apps.core.models.pending.Pending)
| Field | Description |
|-------|-------------|
| `item_id` | Foreign key to Item |
| `quantity` | Pending quantity |
| `source_type` | Transaction type (order_line, purchase_line, etc.) |
| `source_id` | Foreign key to source record |
| `status` | pending, committed, cancelled |

### Inventory Layer (apps.products.models.inventory_layer.InventoryLayer)
| Field | Description |
|-------|-------------|
| `item_id` | Foreign key to Item |
| `warehouse_id` | Location |
| `quantity` | Quantity in layer |
| `unit_cost` | Cost per unit |
| `lot` / `serial_batch` | Tracking info |

---

## Test Item Baseline

**Item ID:** 240

```bash
# Get current item state
python manage.py shell -c "
from apps.products.models.item import Item
item = Item.objects.get(pk=240)
print(f'Item: {item.name if hasattr(item, \"name\") else item.pk}')
print(f'  quantity_on_hand: {getattr(item, \"quantity_on_hand\", \"N/A\")}')
print(f'  quantity_reserved: {getattr(item, \"quantity_reserved\", \"N/A\")}')
print(f'  quantity_on_order: {getattr(item, \"quantity_on_order\", \"N/A\")}')
print(f'  quantity_available: {getattr(item, \"quantity_available\", \"N/A\")}')
"
```

---

## Test Scenarios

### Scenario 1: Order Creation (Sell Side)
**Expected:** Reserves inventory, creates pending record

```bash
# Create order with item 240
python manage.py shell -c "
from apps.transactions.models import Order, OrderLine
order = Order.objects.create(status='draft')
line = OrderLine.objects.create(
    order=order,
    item={'id_num': 240},
    quantity={'ordered': 5}
)
print(f'Created Order {order.pk} with Line {line.pk}')
"
```

### Scenario 2: Purchase Creation (Buy Side)
**Expected:** Increases quantity_on_order

```bash
# Create purchase with item 240
python manage.py shell -c "
from apps.transactions.models import Purchase, PurchaseLine
po = Purchase.objects.create(status='draft')
line = PurchaseLine.objects.create(
    purchase=po,
    item={'id_num': 240},
    quantity={'ordered': 10},
    cost={'unit': 15.00}
)
print(f'Created Purchase {po.pk} with Line {line.pk}')
"
```

### Scenario 3: Purchase Receipt
**Expected:** Increases quantity_on_hand, decreases quantity_on_order, creates inventory layer

```bash
# Receive purchase (requires existing PO)
python manage.py shell -c "
from apps.transactions.services.flow import receive_purchase_order, ReceiveLine
from apps.transactions.models import Purchase

po = Purchase.objects.get(pk=<PO_ID>)  # Replace with actual PO ID
lines = [
    ReceiveLine(po_line_id=<LINE_ID>, qty=10, warehouse_code='MAIN')
]
result = receive_purchase_order(po, 'RCV-TEST-001', lines)
print(result)
"
```

### Scenario 4: Invoice from Order
**Expected:** Commits reserved inventory, decreases quantity_on_hand

```bash
# Convert order to invoice
python manage.py shell -c "
from apps.transactions.services.flow import order_to_invoice
from apps.transactions.models import Order

order = Order.objects.get(pk=<ORDER_ID>)  # Replace with actual Order ID
invoice = order_to_invoice(order)
print(f'Created Invoice {invoice.pk}')
"
```

### Scenario 5: WorkOrder (Manufacturing)
**Expected:** Consumes components, produces finished goods

```bash
# Create work order with item 240
python manage.py shell -c "
from apps.transactions.models import WorkOrder, WorkOrderLine
wo = WorkOrder.objects.create(status='draft')
line = WorkOrderLine.objects.create(
    parent=wo,
    item={'id_num': 240},
    quantity={'planned': 5}
)
print(f'Created WorkOrder {wo.pk} with Line {line.pk}')
"
```

---

## Inventory Check Commands

### Quick Status Check
```bash
python manage.py shell -c "
from apps.products.models.item import Item
from apps.core.models.pending import Pending

item = Item.objects.get(pk=240)
pendings = Pending.objects.filter(item_id=240)

print('=== ITEM 240 STATUS ===')
print(f'on_hand: {getattr(item, \"quantity_on_hand\", 0)}')
print(f'reserved: {getattr(item, \"quantity_reserved\", 0)}')
print(f'on_order: {getattr(item, \"quantity_on_order\", 0)}')
print(f'available: {getattr(item, \"quantity_available\", 0)}')
print(f'pending records: {pendings.count()}')
for p in pendings:
    print(f'  - {p.source_type} #{p.source_id}: qty={p.quantity} status={p.status}')
"
```

### Transaction Summary
```bash
python manage.py shell -c "
from apps.transactions.models import OrderLine, PurchaseLine, InvoiceLine

print('=== TRANSACTIONS FOR ITEM 240 ===')
print(f'Order Lines: {OrderLine.objects.filter(item__id_num=240).count()}')
print(f'Purchase Lines: {PurchaseLine.objects.filter(item__id_num=240).count()}')
print(f'Invoice Lines: {InvoiceLine.objects.filter(item__id_num=240).count()}')
"
```

---

## Event Log

### Format
```
[DATE TIME] [EVENT_TYPE] [TRANSACTION] - Description
  Before: on_hand=X, reserved=Y, on_order=Z
  After:  on_hand=X, reserved=Y, on_order=Z
  Delta:  on_hand=±X, reserved=±Y, on_order=±Z
```

---

### Log Entries

#### 2026-01-25 - Baseline Established
```
[2026-01-25 XX:XX] [BASELINE] [ITEM-240] - Initial inventory state
  on_hand: ___
  reserved: ___
  on_order: ___
  available: ___
  pending_count: ___
```

#### Test 1: ___
```
[DATE TIME] [EVENT] [TRANSACTION-TYPE #ID] - Description
  Before: on_hand=___, reserved=___, on_order=___
  After:  on_hand=___, reserved=___, on_order=___
  Delta:  on_hand=___, reserved=___, on_order=___
  Notes: ___
```

#### Test 2: ___
```
[DATE TIME] [EVENT] [TRANSACTION-TYPE #ID] - Description
  Before: on_hand=___, reserved=___, on_order=___
  After:  on_hand=___, reserved=___, on_order=___
  Delta:  on_hand=___, reserved=___, on_order=___
  Notes: ___
```

#### Test 3: ___
```
[DATE TIME] [EVENT] [TRANSACTION-TYPE #ID] - Description
  Before: on_hand=___, reserved=___, on_order=___
  After:  on_hand=___, reserved=___, on_order=___
  Delta:  on_hand=___, reserved=___, on_order=___
  Notes: ___
```

---

## Issues Found

| Date | Issue | Transaction | Expected | Actual | Status |
|------|-------|-------------|----------|--------|--------|
| | | | | | |

---

## Related Files

### Models
- `apps/products/models/item.py` - Item model with inventory fields
- `apps/products/models/inventory_layer.py` - Inventory layers/stacks
- `apps/core/models/pending.py` - Pending inventory records

### Services
- `apps/transactions/services/inventory_flow.py` - Inventory delta creation
- `apps/transactions/services/flow.py` - Transaction flow (receive_purchase_order, etc.)

### Tests
- `tests/test_inventory_flow.py` - Automated inventory tests

---

## Next Steps

1. [ ] Run baseline check for item 240
2. [ ] Create test Order with item 240
3. [ ] Verify reservation created
4. [ ] Create test Purchase with item 240
5. [ ] Verify quantity_on_order updated
6. [ ] Receive Purchase
7. [ ] Verify inventory layer created
8. [ ] Convert Order to Invoice
9. [ ] Verify inventory committed/decremented
10. [ ] Document all observations in log above
