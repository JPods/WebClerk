# Inventory Delta System (dInventory)

## Overview

This document describes the inventory delta system that tracks inventory quantity changes through the transaction flow. It follows the WebClerk2 dInventory approach using the `Pending` model for deferred processing.

## Core Concept

Instead of immediately updating item quantities when transactions occur, the system creates "delta" records that represent quantity changes. These deltas are processed periodically to update the actual item inventory levels. This approach provides:

- **Audit Trail**: Every inventory change is recorded
- **Performance**: Avoids immediate database updates during transaction processing
- **Consistency**: Batch processing ensures inventory accuracy
- **Debugging**: Easy to trace inventory changes back to source transactions

## Inventory Quantity Types

Items track three types of quantities:

- **`quantity.on_hand`**: Physical inventory available for sale/shipment
- **`quantity.on_order`**: Committed to customers (sales orders)
- **`quantity.on_po`**: Committed from vendors (purchase orders)

## When Deltas Are Created

### Sales Order Creation

```python
# When a sales order is created
_create_inventory_delta(
    item_id=item_id,
    source_type='sales_order_line',
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
    notes=f"Purchase receipt {receipt.receipt_no} - received {qty_received} units"
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
