# Transaction Line Save Architecture

This document describes how transaction lines are created, updated, and deleted across all transaction types, and how pending inventory records are generated.

## Table of Contents

- [Overview](#overview)
- [Supported Transaction Types](#supported-transaction-types)
- [Save Flow](#save-flow)
- [Model Mapping](#model-mapping)
- [Line Data Structure](#line-data-structure)
- [Pending Inventory Records](#pending-inventory-records)
- [Frontend Integration](#frontend-integration)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## Overview

Transaction lines (order lines, invoice lines, etc.) are saved as part of the parent transaction save operation via the unified `/wcapi/save/` endpoint. The backend:

1. Saves the parent transaction (Order, Invoice, Proposal, Purchase, WorkOrder)
2. Processes embedded `lines` array
3. Creates/updates line records using the appropriate line model
4. Generates Pending inventory records for new lines

This ensures atomicity and consistency across the transaction and its lines.

---

## Supported Transaction Types

| Transaction Type | Model Name(s) | Line Model | FK Field | Pending Type |
|-----------------|---------------|------------|----------|--------------|
| Order | `order` | `OrderLine` | `order` | `SO` |
| Invoice | `invoice` | `InvoiceLine` | `invoice` | `IN` |
| Proposal | `proposal` | `ProposalLine` | `proposal` | `PP` |
| Purchase | `purchase` | `PurchaseLine` | `purchase` | `PO` |
| Work Order | `workorder`, `work_order` | `WorkOrderLine` | `workorder` | `WO` |

---

## Save Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     POST /wcapi/save/                               │
│  { model_name: "purchase", record: { id: 39, lines: [...] } }       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. Parse & Validate Request                                        │
│     - Extract model_name, record, options                           │
│     - Merge 'record' fields into main data                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. Save Parent Transaction                                         │
│     - Create or update Order/Invoice/Proposal/Purchase/WorkOrder    │
│     - Apply field updates (skip corrupted JSON fields)              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. Determine Line Model                                            │
│     - Look up in line_model_map based on normalized model_key       │
│     - Get LineModel class and fk_field_name                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. Process Each Line                                               │
│     For each line_data in lines:                                    │
│     ├─ If id is None or starts with "temp-":                        │
│     │    → Create new LineModel instance                            │
│     │    → Set FK field (e.g., purchase_id = parent.id)             │
│     │    → Copy all fields from line_data                           │
│     │    → Save line                                                │
│     │    → Create Pending inventory record                          │
│     └─ Else:                                                        │
│          → Load existing line by id                                 │
│          → Update fields from line_data                             │
│          → Save line                                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. Update Parent refs.links                                        │
│     - Add new line IDs to refs.links.{model}_line                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6. Return Response                                                 │
│     { status: "success", data: { id, record, messages } }           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Model Mapping

The save view uses a unified mapping to determine the line model:

```python
line_model_map = {
    'order': ('OrderLine', 'order'),
    'invoice': ('InvoiceLine', 'invoice'),
    'purchase': ('PurchaseLine', 'purchase'),
    'workorder': ('WorkOrderLine', 'workorder'),
    'work_order': ('WorkOrderLine', 'workorder'),
    'proposal': ('ProposalLine', 'proposal'),
}
```

The FK field name is used to set the relationship:
```python
setattr(line_obj, f'{fk_field_name}_id', parent_obj.id)
# e.g., line_obj.purchase_id = 39
```

---

## Line Data Structure

All line types share a common structure with type-specific variations:

### Common Fields

```json
{
  "id": null,                    // null for new, integer for existing
  "item": {
    "item_id": 236,
    "ida_item": "BBD10",
    "description": "10 Dz. Dimple Baseball YELLOW",
    "unit_measure": "EA"
  },
  "quantity": {
    "placed": 5,                 // Quantity placed/committed on this line
    "actioned": 0,               // Quantity acted on (context-dependent: shipped, received, etc.)
    "remaining": 5,              // placed - actioned
    "is_fixed": false,           // Whether quantity is locked
    "precision": 2               // Decimal precision
  },
  "price": {                     // For sell-side (order, invoice, proposal)
    "unit": 220.00,
    "extended": 1100.00
  },
  "cost": {                      // For exec-side (purchase, workorder)
    "unit": 150.00,
    "extended": 750.00
  }
}
```

> **Canonical quantity keys**: All transaction types use `placed` / `actioned` / `remaining`.
> Legacy keys like `ordered`, `invoiced`, `received`, `shipped`, `packed` are **deprecated**.
> `actioned` replaces the type-specific verb — its meaning is contextual:
>
> | Transaction Type | `actioned` means |
> |------------------|------------------|
> | Proposal         | converted to order |
> | Order            | shipped / invoiced |
> | Invoice          | delivered |
> | Purchase         | received from vendor |
> | WorkOrder        | completed |

### Type-Specific Fields

| Field | Order | Invoice | Proposal | Purchase | WorkOrder |
|-------|-------|---------|----------|----------|-----------|
| `quantity.placed` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `quantity.actioned` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `quantity.remaining` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `price.unit` | ✓ | ✓ | ✓ | - | - |
| `cost.unit` | - | - | - | ✓ | ✓ |

---

## Pending Inventory Records

When a new line is created, a Pending record is generated to track the inventory impact without locking the Item record.

### Pending Type Codes

| Type Code | Transaction | Quantity Bucket | Description |
|-----------|-------------|-----------------|-------------|
| `SO` | Order | `on_so` | Reserved for customer orders |
| `IN` | Invoice | `on_in` | Issued/shipped (reduces on_hand) |
| `PP` | Proposal | `on_p` | Forecast/pipeline (probability-weighted) |
| `PO` | Purchase | `on_po` | On order from vendor |
| `WO` | Work Order | `on_wo` | Committed to work orders |
| `RC` | Receipt | `on_r` | Received into inventory (increases on_hand) |

### Pending Record Structure

```json
{
  "model_name": "item",
  "record_id": 236,              // Item ID
  "data": {
    "type_id": "PO",
    "item_id": 236,
    "item_num": "BBD10",
    "line_id": 71,
    "doc_pk": 39,
    "doc_id": "PO-2026-001",
    "transaction_type": "purchase",
    "transaction_model": "purchase",
    "reason": "po line add",
    "on_po": 5.0,                // Quantity in appropriate bucket
    "on_so": 0,
    "on_in": 0,
    "on_p": 0,
    "on_r": 0,
    "on_wo": 0,
    "unit_cost": 150.00,
    "unit_price": 0.0,
    "take_action": 1
  }
}
```

### LineItemService Integration

The `LineItemService._create_pending_for_new_line()` method creates pending records:

```python
from apps.transactions.services.line_item_service import LineItemService

service = LineItemService(create_pending=True)
service._create_pending_for_new_line(
    parent=purchase_obj,
    parent_model_key='purchase',
    line=line_obj,
    line_data=line_data,
)
```

---

## Frontend Integration

### Payload Format

The frontend sends a unified payload format:

```typescript
const payload = {
  model_name: "purchase",        // Normalized model name
  record: {
    id: 39,
    ida: "PO-2026-001",
    status: "planned",
    // ... other transaction fields
    lines: [
      // Existing line (has id)
      {
        id: 64,
        item: { item_id: 231, ... },
        quantity: { placed: 4 },
      },
      // New line (no id or temp id)
      {
        item: { item_id: 236, ida_item: "BBD10", ... },
        quantity: { placed: 5 },         // Use placed, NOT ordered
        cost: { unit: 150 },
      }
    ]
  },
  id: 39,
  options: {
    verify_calculations: false,
    save_only_dirty: false
  }
};
```

### API Call

```typescript
import { saveTransactionWithLines } from '@/api/wcapi';

const result = await saveTransactionWithLines('purchase', payload);
```

### TransactionDetailBase Component

All transaction detail pages extend `TransactionDetailBase` which handles:
- Line state management via `onLinesChange`
- Save orchestration via `performSave`
- Toast notifications for success/error

---

## Error Handling

### Corrupted JSON Fields

The save view skips corrupted non-dict values for JSON fields:

```python
elif is_json_field and not isinstance(value, (dict, list)) and value is not None:
    console_logger.warning(f"[SAVE_VIEW] Skipping corrupted JSON field '{field}': got {type(value).__name__}")
    continue
```

### Line Save Errors

Errors during line save are logged but don't fail the entire operation:

```python
except Exception as e:
    console_logger.error(f"[SAVE_VIEW] Error saving line {idx}: {e}")
```

### Pending Creation Errors

Pending creation failures are warnings, not fatal errors:

```python
except Exception as pending_err:
    console_logger.warning(f"[SAVE_VIEW] Failed to create pending for line {line_obj.id}: {pending_err}")
```

---

## Examples

### Creating a Purchase with Lines

**Request:**
```http
POST /wcapi/save/
Content-Type: application/json

{
  "model_name": "purchase",
  "record": {
    "id": null,
    "ida": "PO-2026-002",
    "vendor_id": 100,
    "status": "draft",
    "lines": [
      {
        "item": { "item_id": 236, "ida_item": "BBD10" },
        "quantity": { "placed": 10 },
        "cost": { "unit": 150.00 }
      }
    ]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "data": {
    "id": 42,
    "model_name": "purchase",
    "version": 1,
    "record": { ... }
  }
}
```

**Database Effects:**
1. `Purchase` record created (id=42)
2. `PurchaseLine` record created (id=72, purchase_id=42)
3. `Pending` record created (type_id=PO, on_po=10.0, item_id=236)

### Updating an Order with New Line

**Request:**
```http
POST /wcapi/save/

{
  "model_name": "order",
  "record": {
    "id": 61,
    "lines": [
      { "id": 144, "quantity": { "placed": 9 } },  // Update existing
      { "item": { "item_id": 259 }, "quantity": { "placed": 3 } }  // Add new
    ]
  },
  "id": 61
}
```

**Database Effects:**
1. `Order` record updated (version incremented)
2. `OrderLine` id=144 updated (quantity changed)
3. New `OrderLine` created (id=145)
4. `Pending` record created (type_id=SO, on_so=3.0, item_id=259)

---

## Related Documentation

- [Transaction Flow Responsibilities](transaction-flow-responsibilities.md) - Frontend vs Backend split
- [LineItemService Test Plan](line_item_service_test_plan.md) - Testing strategy
- [Inventory Deltas](../inventory/inventory_deltas.md) - Pending processing

---

*Last updated: 2026-02-17*
