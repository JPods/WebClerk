# WC3 Transaction Save - Dirty Tracking & Calculation Verification

> **Status**: ✅ IMPLEMENTED  
> **Updated**: 2026-01-14  
> **Endpoint**: `POST /wcapi/transaction/save/`

---

## Overview

WC3 provides a specialized transaction save endpoint that:

1. **Verifies R25's calculations** against WC3's authoritative math
2. **Tracks dirty lines** to skip unchanged lines during saves
3. **Returns recalculated totals** so R25 can sync with WC3's authoritative values

---

## Why This Matters

- **R25 performs optimistic calculations** for responsive UI
- **WC3 is authoritative** for all calculations (backend truth)
- **On save, WC3 verifies** that R25's calculations match within tolerance
- **If mismatch detected**, save is rejected with details for debugging

---

## Endpoint

```
POST /wcapi/transaction/save/
```

### Request Payload

```json
{
  "model_name": "invoice",
  "record": {
    "id": 123,
    "totals": {
      "subtotal": 1000.00,
      "tax": 80.00,
      "total": 1080.00
    },
    "finance": {
      "margin": 250.00,
      "margin_pct": 25.0
    },
    "lines": [
      {
        "id": 1,
        "_dirty": false,
        "quantity": { "qty": 5 },
        "price": { "unit": 100.00, "extended": 500.00 },
        "discount": { "pct": 10, "amt": 50.00 }
      },
      {
        "id": 2,
        "_dirty": true,
        "quantity": { "qty": 10 },
        "price": { "unit": 50.00, "extended": 450.00 },
        "discount": { "pct": 10, "amt": 50.00 }
      },
      {
        "_dirty": true,
        "quantity": { "qty": 2 },
        "price": { "unit": 25.00, "extended": 50.00 },
        "discount": { "pct": 0, "amt": 0.00 }
      }
    ]
  },
  "options": {
    "verify_calculations": true,
    "save_only_dirty": true
  }
}
```

> **Note**: Lines are provided inside `record.lines` (consistent with existing `/wcapi/save/` pattern).
```

### Line `_dirty` Flag

| `_dirty` Value | Line Has `id` | Action |
|----------------|---------------|--------|
| `true` | Yes | Update existing line |
| `true` | No | Create new line |
| `false` | Yes | Skip (no save) |
| `false` | No | Skip (ignored) |

### Response (Success)

```json
{
  "header": { "id": 123 },
  "lines": [
    { "id": 1, "line_number": 10, "action": "skipped", "reason": "not_dirty" },
    { "id": 2, "line_number": 20, "action": "updated" },
    { "id": 789, "line_number": 30, "action": "created" }
  ],
  "lines_saved": 2,
  "lines_skipped": 1,
  "action": "updated",
  "recalculated_totals": {
    "subtotal": 1000.00,
    "tax": 80.00,
    "total": 1080.00,
    "margin": 250.00,
    "margin_pct": 25.0
  }
}
```

### Response (Calculation Mismatch)

```json
{
  "detail": "Calculation mismatch",
  "error": "Line 2: 'extended' mismatch - R25: 500.00 vs WC3: 450.00",
  "field": "extended",
  "r25_value": 500.00,
  "wc3_value": 450.00,
  "line_id": 2
}
```

### Response (Item ID Change Blocked)

```json
{
  "detail": "Item ID change not allowed",
  "error": "Line 5: item_id changed from 'ITEM-001' to 'ITEM-002'",
  "line_id": 5,
  "old_item_id": "ITEM-001",
  "new_item_id": "ITEM-002"
}
```

---

## R25 Integration

### Setting the `_dirty` Flag

In R25, track line changes using `useLineState` or equivalent:

```typescript
interface TransactionLine {
  id?: number;          // Undefined for new lines
  line_number?: number; // Stable identity (auto-assigned by backend if 0 or absent)
  _dirty: boolean;      // True if created or modified
  quantity: { qty: number };
  price: { unit: number; extended: number };
  discount: { pct: number; amt: number };
  cost?: { unit: number; extended: number; grossCost: number; discountCost: number };
  item: { item_id: string; /* ... */ };
}

// Mark dirty when line is modified
const updateLine = (index: number, changes: Partial<TransactionLine>) => {
  setLines(prev => prev.map((line, i) => 
    i === index ? { ...line, ...changes, _dirty: true } : line
  ));
};

// New lines are always dirty
const addLine = (newLine: Omit<TransactionLine, 'id' | '_dirty'>) => {
  setLines(prev => [...prev, { ...newLine, _dirty: true }]);
};
```

### Calling the Endpoint

```typescript
const saveTransaction = async (
  modelName: string,
  record: TransactionRecord,
  lines: TransactionLine[]
) => {
  const response = await fetch('/wcapi/transaction/save/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model_name: modelName,
      record,
      lines,
      options: {
        verify_calculations: true,
        save_only_dirty: true
      }
    })
  });

  if (!response.ok) {
    const error = await response.json();
    if (error.field) {
      // Calculation mismatch - log for debugging
      console.error(`Calculation mismatch on ${error.field}:`, error);
    }
    throw new Error(error.detail);
  }

  const result = await response.json();
  
  // Sync R25 totals with WC3's authoritative values
  updateTotals(result.recalculated_totals);
  
  // Clear dirty flags and assign IDs to new lines
  result.lines.forEach(lineResult => {
    if (lineResult.action === 'created') {
      // New line now has ID from server
    }
  });
  
  return result;
};
```

---

## Calculation Tolerance

WC3 allows a small tolerance for floating-point precision:

```python
CALC_TOLERANCE = Decimal("0.01")  # $0.01 tolerance
```

This handles rounding differences between JavaScript and Python decimal math.

---

## Verified Calculations

### Per-Line

| Field | Formula |
|-------|---------|
| `price.extended` | `qty × unit` |
| `discount.amt` | `extended × (pct / 100)` |
| `cost.extended` | `qty × unit` |
| `cost.grossCost` | `cost.extended` |
| `cost.discountCost` | `cost.extended - discount.amt` (cost side) |

### Header Totals

| Field | Formula |
|-------|---------|
| `totals.subtotal` | `Σ(line.price.extended - line.discount.amt)` |
| `totals.tax` | `subtotal × tax_rate` |
| `totals.total` | `subtotal + tax` |
| `finance.margin` | `subtotal - Σ(line.cost.extended)` |
| `finance.margin_pct` | `(margin / subtotal) × 100` |

---

## Options Reference

| Option | Default | Description |
|--------|---------|-------------|
| `verify_calculations` | `true` | Compare R25 values to WC3 calculations |
| `save_only_dirty` | `true` | Skip lines where `_dirty: false` |

Set `verify_calculations: false` during development to bypass math checks (not recommended for production).

---

## Changelog

| Date | Status | Notes |
|------|--------|-------|
| 2026-01-14 | ✅ Implemented | Created `transaction_save.py` service and `WCAPITransactionSaveView` |
| 2026-02-21 | ✅ Refactored | **Collect-then-create pattern** — lines saved with signals suppressed, pending deltas collected into array, Pending records created afterwards with backend-authoritative type/transfer detection, single dispatch. Eliminates duplicate pending records. |

---

## Backend-Authoritative Pending (2026-02-21)

The backend is authoritative for all pending-related decisions during transaction saves:

- **Pending type** (SO/IN/PO/PP/WO) derived from `model_key`, not front-end data
- **Transfer detection** uses `header.parent_id` + `header.parent_model`
- **Quantity buckets** set server-side based on type and transfer status
- **Duplicate prevention** — `(invoice_line_id, order_line_id)` pair stored in every Pending record; duplicates blocked in-memory and at DB level

### Transfer Flow (Order → Invoice)

1. R25 calls `saveTransactionWithLines("invoice", payload)` with `parent_id` and `parent_model: "order"` on the header
2. Each invoice line should include `refs.source.order_line_id` pointing to the source order line (for traceability)
3. Backend creates **one Pending per invoice line** capturing `on_in=+qty, on_so=-qty, on_hand=-qty`
4. R25 calls `saveRecord("order", { id, is_active: false })` to deactivate the source order

> **Do not send pending-related fields from R25.** The backend derives everything it needs from the saved data.
