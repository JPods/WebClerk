## LineItemService End-to-End Test Plan

### Scope
Tests LineItemService across proposals, sales orders, invoices, purchase orders, and work orders using items 246, 247, 248 with quantity.placed = 3.

### Pending Type Mapping

| Transaction Type | Type Code | Quantity Bucket |
|------------------|-----------|-----------------|
| Order | SO | on_so |
| Proposal | PP | on_p |
| Invoice | IN | on_in |
| Receipt | RC | on_r |
| Purchase | PO | on_po |
| WorkOrder | WO | on_wo |

**Note:** Invoice (IN) and Receipt (RC) also affect `on_hand`:
- Invoice: decreases on_hand (goods shipped)
- Receipt: increases on_hand (goods received)

- Purchase Order
- Work Order

Items tested:
- 246
- 247
- 248

Quantity baseline: placed = 3

### Assertions
- Pending created on add
- Pending type_id correct
- Quantity buckets mapped correctly
- Delta pending created on update
- Negative pending created on delete

### Reporting
Summaries per transaction type:
- pending_add_count
- pending_delta_count
- pending_delete_count
- qty_totals_per_bucket

