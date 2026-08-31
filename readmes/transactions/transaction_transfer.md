# Transaction Transfer — Unified Flow

## Overview

Transaction transfer moves lines from one transaction to another, creating a
lineage chain that tracks the journey of goods from initial proposal through
fulfillment.  All transfers are **atomic** — they succeed completely or roll
back.

Every transfer:
- Creates a **new** target transaction (id = null → auto-assigned)
- Links the target back to its source via `parent_model` / `parent_id`
- Records an audit trail in `refs.source` and `refs.xfer`
- Updates the source line's `children_active` tracker and recomputes `remaining`
- Uses **canonical** quantity keys: `staged` / `active` / `remaining` / `children_active`

---

## Transfer Scenarios

### 1. Proposal → Proposal  (Clone / Duplicate)

Creates a copy of the proposal with quantities reset.

| Field | Rule |
|-------|------|
| **id** | Auto-assigned (new proposal) |
| **parent_model** | `"proposal"` |
| **parent_id** | Source proposal PK |
| **customer** | `null` — not copied |
| **vendor / manufacturer** | `null` — not copied |
| **price_level** | `"retail"` |
| **status** | `"planned"` |

**Line quantities:**

```
target_line.quantity.staged    = source_line.quantity.staged
target_line.quantity.active    = source_line.quantity.staged
target_line.quantity.remaining = source_line.quantity.staged
```

The source proposal is **not modified** — no quantities change, no status
change.  This is a pure clone.

---

### 2. Proposal → Order / Invoice  (Convert with Increment Logic)

Converts proposal lines into order or invoice lines.  Supports partial
transfers via the `increment` field on each line's quantity.

| Field | Rule |
|-------|------|
| **id** | Auto-assigned (new order/invoice) |
| **parent_model** | `"proposal"` |
| **parent_id** | Source proposal PK |
| **customer** | Copied from proposal |
| **vendor / manufacturer** | Copied from proposal |
| **contact** | Copied from proposal |
| **price_level** | Copied from proposal |
| **status** | `"confirmed"` (order) / `"pending"` (invoice) |

**Increment-based quantity logic:**

For each source line, the transfer amount is determined by `increment`:

```
increment = source_line.quantity.increment   (default 0)
remaining = source_line.quantity.remaining

if increment == 0:
    # Take ALL remaining
    transfer_qty = remaining

elif increment < remaining:
    # Take exactly the increment amount
    transfer_qty = increment

else:
    # Increment >= remaining: take what's left
    transfer_qty = remaining
```

**Target line quantities:**

```
target_line.quantity.staged    = transfer_qty
target_line.quantity.active    = transfer_qty
target_line.quantity.remaining = transfer_qty
target_line.quantity.increment = source_line.quantity.increment
```

**Source line update (children_active tracker):**

```python
# Build/update children_active on the source line
children_active = source_line.quantity.get("children_active", {"sum": 0, "lines": []})
children_active["lines"].append({"id": target_line.pk, "active": transfer_qty})
children_active["sum"] = sum(c["active"] for c in children_active["lines"])
source_line.quantity["children_active"] = children_active
source_line.quantity["remaining"] = max(0, source_line.quantity["active"] - children_active["sum"])
```

If `source_line.quantity.remaining` reaches 0, its `status` → `"transferred"`.
If **all** source lines reach 0 remaining, proposal `status` → `"converted"`.

Lines with `remaining ≤ 0` are **skipped** (already fully transferred).

---

### 3. Cross-Type Transfer  (Sell ↔ Purchase)

Transfers between different transaction families:
- proposal / order / invoice → purchase
- purchase → proposal / order / invoice

These cross the **sell ↔ buy** boundary.  Customer information is **not** carried
because the counterparty context differs.

| Field | Rule |
|-------|------|
| **id** | Auto-assigned |
| **parent_model** | Source type (`"proposal"`, `"order"`, `"invoice"`, `"purchase"`) |
| **parent_id** | Source transaction PK |
| **customer** | `null` — not copied |
| **vendor / manufacturer** | `null` — not copied |
| **price_level** | Empty (to be set by user on the purchase side) |
| **status** | `"open"` (purchase) / `"planned"` (sell-side) |

**Line quantities (full reset):**

```
target_line.quantity.staged    = source_line.quantity.staged
target_line.quantity.active    = source_line.quantity.staged
target_line.quantity.remaining = source_line.quantity.staged
```

Source lines are **not decremented** — cross-type transfers are independent copies
that track procurement separately from sales fulfillment.

---

## Quantity Field Reference

```python
{
    "staged":     0,       # quantity received from parent (frozen after creation)
    "active":     0,       # user's working quantity (never system-modified)
    "remaining":  0,       # active - children_active["sum"] (or active if no children)
    "increment":  0,       # minimum transfer batch size (0 = transfer all)
    "is_fixed":   False,   # lock from editing
    "is_blanket": False,   # open-ended qty
    "precision":  2,       # decimal places
    # Present only on parent lines that have been transferred:
    "children_active": {   # denormalized tracker of child line quantities
        "sum": 0,          # total active across all children
        "lines": [         # per-child entries
            {"id": 201, "active": 5},
        ]
    }
}
```

**Universal remaining formula:**

```
remaining = active − children_active["sum"]
```

When a line has no children, `children_active` is absent and `remaining = active`.

---

## Lineage Tracking

### Header level — `parent_model` / `parent_id`

```
Proposal #42 ──▶ Order #61 ──▶ Invoice #85
                   │
                   └──▶ Purchase #39
```

```python
order.parent_model = "proposal"
order.parent_id    = 42
```

### Header level — `flow` JSONB

```python
# Source proposal after transfer:
proposal.flow = {
    "source":   [],
    "children": [{"type": "order", "id": 61}]
}

# Target order:
order.flow = {
    "source":   [{"type": "proposal", "id": 42}],
    "children": []
}
```

### Line level — `refs.source` + `refs.xfer`

```python
order_line.refs = {
    "source": {
        "proposal_line_id": 101,
        "proposal_id": 42
    },
    "xfer": [
        {
            "version": 1,
            "source": {"kind": "proposal", "parent_id": 42, "line_id": 101},
            "item": {"id": 7, "sku": "WDG-100", "name": "Widget"},
            "qty": {"staged": 10, "remaining": 10},
            "price": {"unit": 25.00, "extended": 250.00},
            "cost": {"unit": 12.00, "extended": 120.00}
        }
    ]
}
```

---

## API

### `POST /tx/transfers/execute/`

```json
{
    "source_type": "proposal",
    "source_id": 42,
    "target_type": "order",
    "line_ids": [101, 102],
    "transfer_all": false,
    "preserve_source": true,
    "target_status": "confirmed"
}
```

**`source_type`** / **`target_type`** — one of: `proposal`, `order`, `invoice`, `purchase`

**Response:**

```json
{
    "success": true,
    "target_id": 61,
    "target_type": "order",
    "source_id": 42,
    "source_type": "proposal",
    "lines_transferred": 2,
    "line_mapping": {"101": 201, "102": 202},
    "source_preserved": true,
    "target_status": "confirmed"
}
```

### `POST /tx/transfers/validate/`

Pre-flight check.  Returns `can_transfer`, `errors`, `warnings`.

---

## Supported Transfer Matrix

| Source ↓ / Target → | Proposal | Order | Invoice | Purchase |
|---------------------|----------|-------|---------|----------|
| **Proposal** | ✅ Clone | ✅ Convert | ✅ Convert | ✅ Cross |
| **Order** | — | — | ✅ Convert | ✅ Cross |
| **Invoice** | — | — | — | ✅ Cross |
| **Purchase** | ✅ Cross | ✅ Cross | ✅ Cross | — |

---

## Implementation

Service: `apps/transactions/services/transfer.py`

```python
from apps.transactions.services.convert.convert_engine import execute_transfer

result = execute_transfer(
    source_type="proposal",
    source_id=42,
    target_type="order",
    line_ids=None,        # None = all lines
    transfer_all=True,
    preserve_source=True,
    target_status="confirmed",
)
```

The unified `execute_transfer()` function handles clone, convert, and
cross-type transfers through a common engine. Dedicated services
(`proposal_to_order.py`, `order_to_invoice.py`) provide specialized
conversion logic for the R25 "Convert" button flows.

---

## Error Handling

| Error | When |
|-------|------|
| `TransferError("No lines to transfer")` | Source has zero lines (or all remaining ≤ 0 for converts) |
| `TransferError("Source not found")` | Invalid `source_id` |
| `TransferError("Unsupported transfer")` | Invalid source→target combination |
| `TransferError("Line IDs not found: [...]")` | `line_ids` don't belong to source |

All errors roll back the atomic transaction — no partial state.

---

## Frontend UI Behavior

### Transfer trigger

The `TransactionToolbar` component (`React2025/src/apps/common/components/TransactionToolbar.tsx`)
provides a **Transfer** dropdown on every transaction detail page.  The user
selects a target type (Invoice, Order, Proposal, Purchase, Work Order) and the
toolbar fires the `onTransfer(targetType)` callback.

### Order → Invoice: Floating InvoiceDetail window

When transferring from an **Order** to an **Invoice**, the transfer API returns
a `target_id` for the newly created invoice.  The frontend must immediately open
a **floating window** (not a route navigation) displaying `InvoiceDetail.tsx`
(`React2025/src/apps/transactions/models/invoice/pages/InvoiceDetail.tsx`)
pre-loaded with the new invoice record.

This floating window allows the user to:
- Review and edit the invoice before final save
- Adjust line quantities, pricing, tax, shipping
- Apply payments via `ApplyPaymentModal`
- Print / email the invoice directly

The source Order detail page remains open beneath the floating window so the
user can visually verify the transfer.

**Sequence:**

```
OrderDetail → [Transfer → Invoice] → POST /tx/transfers/execute/
                                          ↓
                                     { target_id: 85 }
                                          ↓
                              Open floating InvoiceDetail(id=85)
                              (OrderDetail stays open underneath)
```

> **TODO**: The floating window component does not exist yet.  Implement as a
> portal-based overlay or drawer that renders `InvoiceDetail` with the returned
> `target_id`.  The `onTransfer` callback in OrderDetail should handle opening
> this window after a successful API response.

