# Inventory Delta System (dInventory)

## Overview

This document describes the inventory delta system that tracks inventory quantity changes through the transaction flow. It follows the WebClerk2 dInventory approach using the `Pending` model for deferred processing.

## Related Documentation

- [Transaction Line Save Architecture](../transactions/transaction_line_save.md) - How lines are saved and pending records created
- [LineItemService Test Plan](../transactions/line_item_service_test_plan.md) - Testing strategy for pending creation

## Core Concept

Instead of immediately updating item quantities when transactions occur, the system creates "delta" records that represent quantity changes. These deltas are processed periodically to update the actual item inventory levels. This approach provides:

- **Audit Trail**: Every inventory change is recorded
- **Performance**: Avoids immediate database updates during transaction processing
- **Consistency**: Batch processing ensures inventory accuracy
- **Debugging**: Easy to trace inventory changes back to source transactions

## Inventory Quantity Types

Items track multiple quantity buckets in the `Item.quantity` JSON field:

### Core Quantities

| Field | Description | Changed By |
|-------|-------------|------------|
| `on_hand` | Physical inventory available | Receipts (+), Invoices (-), Adjustments (±) |
| `allocated` | Reserved/committed for orders | Allocation process |
| `available` | Computed: on_hand - allocated | Derived |

### Transaction Tracking Quantities

| Field | Type Code | Description | Transaction |
|-------|-----------|-------------|-------------|
| `on_so` | SO | On Sales Orders | Order line add/change/delete |
| `on_po` | PO | On Purchase Orders | Purchase line add/change/delete |
| `on_p` | PP | On Proposals | Proposal line add/change/delete |
| `on_wo` | WO | On Work Orders | WorkOrder line add/change/delete |

### Informational Quantities (Track Totals)

| Field | Type Code | Description | Notes |
|-------|-----------|-------------|-------|
| `on_in` | IN | Invoiced quantity | Informational only; actual change flows through on_hand (-) |
| `on_r` | RC | Received quantity | Informational only; actual change flows through on_hand (+) |

**Note:** `on_in` and `on_r` track historical totals. The real inventory impact is:
- **Invoices**: Decrease `on_hand` (goods shipped out)
- **Receipts**: Increase `on_hand` (goods received)

## When Deltas Are Created

### Sales Order Creation

```python
# When a sales order is created
_create_inventory_delta(
    item_id=item_id,
    source_type='order_line',
    source_id=order.id,
    quantity_on_order_delta=+qty_ordered,  # Increases committed quantity
    notes=f"Sales order {order.id} - ordered {qty_ordered} units"
)

```

### Purchase Order Creation

```python
# When a purchase order is created
_create_inventory_delta(
    item_id=item_id,
    source_type='purchase_order_line',
    source_id=po.id,
    quantity_on_po_delta=+qty_ordered,  # Increases committed purchases
    notes=f"Purchase order {po.id} - ordered {qty_ordered} units"
)

```

### Purchase Receipt (Goods Received)

```python
# When goods are received from vendor
_create_inventory_delta(
    item_id=item_id,
    source_type='purchase_receipt',
    source_id=receipt.id,
    quantity_on_hand_delta=+qty_received,  # Increases available inventory
    quantity_on_po_delta=-qty_received,   # Decreases committed purchases
    notes=f"Purchase receipt {receipt.ida} - received {qty_received} units"
)

```

### Invoice Creation (Goods Shipped)

```python
# When invoice is created (goods shipped)
_create_inventory_delta(
    item_id=item_id,
    source_type='invoice_line',
    source_id=invoice.id,
    quantity_on_hand_delta=-qty_shipped,  # Decreases available inventory
    quantity_on_order_delta=-qty_shipped, # Decreases committed sales
    notes=f"Invoice {invoice.id} - shipped {qty_shipped} units"
)

```

## Delta Storage

Deltas are stored as `Pending` model records:

```python
Pending.objects.create(
    model_name='inventory_delta',
    record_id=f"{item_id}_{timestamp}_{uuid}",
    purpose='inventory_delta',
    name=f"Inventory delta for item {item_id}",
    data={
        'item_id': item_id,
        'warehouse_id': warehouse_id,  # Optional
        'quantity_on_hand_delta': float(delta),
        'quantity_on_order_delta': float(delta),
        'quantity_on_po_delta': float(delta),
        'source_type': source_type,
        'source_id': source_id,
        'source_line_id': source_line_id,
        'unit_cost': unit_cost,  # Optional
        'notes': description,
        'created_at': iso_timestamp
    }
)

```

## Processing Deltas

Deltas are processed periodically via management command:

```bash
python manage.py process_inventory_deltas --batch-size=1000

```

### Pending Purposes Handled

The `pending_inventory_processor` handles the following `purpose` values:

| Purpose | Source | Description |
|---------|--------|-------------|
| `inventory_line_add` | LineItemService | New transaction line added |
| `inventory_qty_change` | LineItemService | Line quantity changed |
| `inventory_line_delete` | LineItemService | Line deleted |
| `inventory_cost_change` | LineItemService | Line cost changed |
| `receipt_line_add` | Receipt creation | Direct receipt (not through LineItemService) |

### Processing Logic

1. **Query Unprocessed Deltas**:

   ```python
   Pending.objects.filter(
       model_name='inventory_delta',
       purpose='inventory_delta',
       dt_processed=0  # Not yet processed
   )
   ```

2. **Group by Item**: Aggregate all deltas for each item

3. **Calculate Net Changes**:

   ```python
   # Sum all deltas for the item
   on_hand_change = sum(deltas' quantity_on_hand_delta)
   on_order_change = sum(deltas' quantity_on_order_delta)
   on_po_change = sum(deltas' quantity_on_po_delta)
   ```

4. **Update Item Quantities**:

   ```python
   item.quantity['on_hand'] += on_hand_change
   item.quantity['on_order'] += on_order_change
   item.quantity['on_po'] += on_po_change
   item.save()
   ```

5. **Mark Deltas Processed**:

   ```python
   for delta in deltas:
       delta.mark_processed()  # Sets dt_processed timestamp
   ```

## Key Rules

### When `quantity_on_hand` Changes

`quantity_on_hand` is only affected by **physical goods movement**:

1. **Purchase Receipt**: Goods arrive → `+on_hand`
2. **Invoice/Shipment**: Goods leave → `-on_hand`

**Order creation does NOT affect `on_hand`** - it only affects committed quantities.

### When `quantity_on_order` Changes

`quantity_on_order` tracks sales commitments:

1. **Sales Order**: Customer commits → `+on_order`
2. **Invoice**: Order fulfilled → `-on_order`

### When `quantity_on_po` Changes

`quantity_on_po` tracks purchase commitments:

1. **Purchase Order**: Vendor commits → `+on_po`
2. **Purchase Receipt**: PO fulfilled → `-on_po`

## Inventory Flow Examples

### Complete Sales Cycle

1. **Sales Order Created**: `+quantity_on_order`

   ```aaa
   Item 123: on_order: 0 → 10
   ```

2. **Invoice Created**: `-quantity_on_hand`, `-quantity_on_order`

   ```aaa
   Item 123: on_hand: 50 → 40, on_order: 10 → 0
   ```

### Complete Purchase Cycle

1. **Purchase Order Created**: `+quantity_on_po`

   ```aaa
   Item 123: on_po: 0 → 20
   ```

2. **Goods Received**: `+quantity_on_hand`, `-quantity_on_po`

   ```aaa
   Item 123: on_hand: 40 → 60, on_po: 20 → 0
   ```

## Error Handling

- **Missing Items**: Deltas for non-existent items are logged and skipped
- **Invalid Data**: Malformed deltas are logged and marked processed to prevent reprocessing
- **Concurrent Updates**: Item updates use `select_for_update()` for consistency

## Monitoring

### Check Processing Status

```sql
SELECT COUNT(*) as pending_deltas
FROM pending
WHERE model_name = 'inventory_delta'
  AND purpose = 'inventory_delta'
  AND dt_processed = 0;

```

### Recent Processed Deltas

```sql
SELECT data->>'item_id' as item_id,
       data->>'source_type' as source_type,
       dt_processed
FROM pending
WHERE model_name = 'inventory_delta'
  AND purpose = 'inventory_delta'
  AND dt_processed > 0
ORDER BY dt_processed DESC
LIMIT 10;

```

## Configuration

### Processing Batch Size

```bash
# Process in smaller batches for memory management
python manage.py process_inventory_deltas --batch-size=500

```

### Dry Run

```bash
# See what would be processed without making changes
python manage.py process_inventory_deltas --dry-run

```

### Specific Item

```bash
# Process deltas for one item only
python manage.py process_inventory_deltas --item-id=123

```

## Benefits

1. **Performance**: Transaction processing doesn't wait for inventory updates
2. **Reliability**: Batch processing prevents partial updates
3. **Auditability**: Complete history of all inventory changes
4. **Flexibility**: Easy to add new delta sources
5. **Debugging**: Clear traceability from transactions to inventory changes

## Handling Returns and Negative Quantities

The system supports negative quantities to handle returns and cancellations:

### Return Scenarios

1. **Sales Returns**: Negative quantities on sales order lines indicate pending returns
   - Creates negative `quantity_on_order_delta` (decreases committed sales)
   - When invoiced with negative quantity, creates positive `quantity_on_hand_delta` and `quantity_on_order_delta` (returns stock and reduces commitment)

2. **Purchase Returns**: Negative quantities on purchase order lines indicate returns to vendor
   - Creates negative `quantity_on_po_delta` (decreases committed purchases)

3. **Invoice Adjustments**: Negative invoice quantities mark returns
   - Increases `quantity_on_hand` (stock returned)
   - Increases `quantity_on_order` (reduces sales commitment)

### Code Changes (2025-12-05)

- **Fixed Import**: Added `Any` to typing imports in `inventory_flow.py`
- **Removed Quantity Caps**: Updated `_get_order_quantity_needed` to return actual difference without `max(0, ...)`
- **Process Negative Deltas**: Modified `create_inventory_deltas_for_order`, `create_inventory_deltas_for_purchase_order`, and `release_inventory_on_invoice` to process quantities != 0 instead of > 0
- **Reservation Logic**: For negative invoices, only positive quantities trigger reservation releases

### Delta Sign Convention

- **Positive Delta**: Increases the quantity type
- **Negative Delta**: Decreases the quantity type
- **Returns**: Use negative source quantities to generate appropriate delta signs

## Future Enhancements

- **Real-time Processing**: Option for immediate delta processing
- **Delta Compression**: Merge multiple deltas for the same item
- **Warehouse-specific Deltas**: Track deltas by warehouse location
- **Delta Validation**: Pre-processing validation of delta data
- **Performance Metrics**: Track processing times and success rates

## Inventory Receiving Functions

The system provides specialized functions for different inventory receiving scenarios in `apps/transactions/services/flow.py`:

### Function Overview

| Function | Source Type | On-Hand | Other Effects |
|----------|-------------|---------|---------------|
| `receive_purchase_order()` | Purchase Order | +qty | -on_po |
| `complete_workorder()` | Work Order | +qty | -on_wo |
| `adjust_inventory()` | Manual Adjustment | ±qty | None |
| `receive_inventory_changes()` | Dispatcher | Routes to above | - |

### receive_purchase_order(po, receipt_id, lines)

Receives goods against a Purchase Order:

```python
from apps.transactions.services.flow import receive_purchase_order, ReceiveLine

lines = [
    ReceiveLine(po_line_id=123, qty=10, warehouse_code='MAIN', unit_cost=15.00),
]
result = receive_purchase_order(po, 'RCV-2025-001', lines)
# Result: {'receipt_id': 456, 'stacks_created': [789], 'deltas_created': 1}
```

**Effects:**
- Creates `Receipt` record with `ida=receipt_id`
- Creates `InventoryLayer` per line for warehouse tracking
- Creates `Pending` delta: `+quantity_on_hand_delta`, `-quantity_on_po_delta`

### complete_workorder(wo, receipt_id, lines)

Completes a WorkOrder, producing finished goods:

```python
from apps.transactions.services.flow import complete_workorder, CompleteWorkOrderLine

lines = [
    CompleteWorkOrderLine(wo_line_id=123, qty_completed=50, warehouse_code='FG'),
]
result = complete_workorder(wo, 'WO-COMP-2025-001', lines)
```

**Effects:**
- Creates `Receipt` record with `ida=receipt_id`
- Creates `InventoryLayer` for finished goods
- Creates `Pending` delta: `+quantity_on_hand_delta`, `-quantity_on_wo_delta`

### adjust_inventory(adjustment_id, lines, notes)

Performs manual inventory adjustments:

```python
from apps.transactions.services.flow import adjust_inventory, AdjustmentLine

lines = [
    AdjustmentLine(item_id=100, qty_delta=5, warehouse_code='MAIN', reason='cycle_count'),
    AdjustmentLine(item_id=101, qty_delta=-2, warehouse_code='MAIN', reason='damage'),
]
result = adjust_inventory('ADJ-2025-001', lines, notes='Monthly cycle count')
```

**Effects:**
- Creates `Receipt` record with `ida=adjustment_id`
- Creates `InventoryLayer` for positive adjustments only
- Creates `Pending` delta: `±quantity_on_hand_delta`

### receive_inventory_changes(source_type, source, receipt_id, lines)

High-level dispatcher that routes to the appropriate handler:

```python
from apps.transactions.services.flow import receive_inventory_changes

# Receive against a PO
result = receive_inventory_changes('purchase', po, 'RCV-001', receive_lines)

# Complete a workorder
result = receive_inventory_changes('workorder', wo, 'WO-COMP-001', complete_lines)

# Manual adjustment
result = receive_inventory_changes('adjustment', None, 'ADJ-001', adjustment_lines)
```

**Valid source_type values:**
- `'purchase'` - requires `Purchase` instance, uses `ReceiveLine`
- `'workorder'` - requires `WorkOrder` instance, uses `CompleteWorkOrderLine`
- `'adjustment'` - source is `None`, uses `AdjustmentLine`
