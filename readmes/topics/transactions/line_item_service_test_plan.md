## LineItemService End-to-End Test Plan

### Scope
Tests LineItemService across proposals, sales orders, invoices, purchase orders, and work orders using items 246, 247, 248 with quantity.placed = 3.

### Matrix
Transactions tested:
- Proposal
- Sales Order
- Invoice
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

