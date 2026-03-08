# Transaction Save Patterns

> **Reading order**: [← 07-react-integration](07-react-integration.md) | [celery-redis-pending →](celery-redis-pending.md)

---

This document covers the backend patterns for saving transactions with lines through the wcapi gateway.

## Two Save Endpoints

| Endpoint | View | Service | Purpose |
|----------|------|---------|---------|
| `POST /wcapi/save/` | `SaveWcapiView.post()` in `apps/core/views/save_view.py` | Per-line `LineItemService._create_pending_for_new_line()` | Generic create/update for any model. Used for order deactivation after transfer, non-transaction saves. |
| `POST /wcapi/transaction/save/` | `WCAPITransactionSaveView.post()` in `apps/transactions/views/wcapi.py` | `save_transaction_with_lines()` in `apps/transactions/services/transaction_save.py` | Transaction saves with lines. R25 uses `saveTransactionWithLines()` for all transaction saves. |

---

## The Collect-Then-Create Pattern

### Why Collect-Then-Create?

The previous per-line pattern created Pending records inside the save loop. Combined with Django's `post_save` signal safety net, this caused **duplicate pending records** (signal fired + explicit create = 2 per line).

The new pattern:

1. Saves all lines with `_pending_created = True` (suppresses signals)
2. Collects pending delta dicts into an array during the loop
3. After all lines are committed, creates Pending records from the array
4. Fires one `dispatch_pending_processing()` at the end

### Four-Phase Save Flow

`save_transaction_with_lines()` performs saves in four phases:

| Phase | Action |
|-------|--------|
| **Phase 1** | Save/update header record (order, invoice, purchase, etc.) |
| **Phase 2** | Save/update all line records, collecting pending deltas |
| **Phase 3** | Update source lines (for transfers: build `children_active` tracker, recompute remaining) |
| **Phase 4** | Create Pending records from collected deltas, dispatch processing |

---

## Backend Authority

The backend is authoritative for all pending-related decisions:

| Decision | Source | NOT from |
|----------|--------|----------|
| Pending type code (SO/IN/PO/PP/WO) | `_PENDING_TYPE_MAP[model_key]` | Front-end refs |
| Is this a transfer? | `header.parent_id` + `header.parent_model` | Front-end flags |
| Quantity buckets | Derived from type + transfer status | Front-end data |
| Duplicate detection | `(invoice_line_id, order_line_id)` pair guard | None |

---

## Key Functions in `transaction_save.py`

| Function | Line | Purpose |
|----------|------|---------|
| `_PENDING_TYPE_MAP` | ~L53 | Maps model_key → type code |
| `_create_pending_from_deltas()` | ~L62 | Creates Pending records from collected array |
| `_update_parent_children_active()` | ~L403 | Updates parent children_active when child active changes |
| `_update_source_lines_after_transfer()` | ~L495 | Builds children_active on parent lines after new transfer |
| `save_transaction_with_lines()` | ~L780 | Main entry point — 4-phase save |

---

## Line Number Assignment

`line_number` is a scalar `IntegerField` on every line (via `BaseLineCore`).
`line_increment` is a counter on every transaction header (via `TransactionBaseModel`, default `10`).

During `save_transaction_with_lines()`:

1. Before the line loop, read `current_line_increment` from the header
2. For each **new line** where `line_number == 0`:
   - Assign `line_number = current_line_increment`
   - Bump `current_line_increment += 10`
3. After all lines, persist the bumped value back: `header.line_increment = current_line_increment`
4. The response includes `line_number` for both created and updated lines

The backend `BaseLineCore.save()` also auto-assigns `line_number` from `parent.line_increment` when `line_number == 0` (fallback for non-transaction-save paths).

R25 uses `lineKey(line, idx)` → `line.line_number ?? line.id ?? idx` for stable line identity in state handlers.

---

## Pending Data Structure

Each Pending record's `data` JSON contains:

```python
{
    "type_id": "IN",                    # SO, PO, PP, IN, WO
    "item_id": 243,
    "item_num": "WIDGET-A",
    "doc_id": "INV-1001",
    "doc_pk": 38,
    "line_id": 8,                       # the new line PK
    "line_num": 10,                     # line_number (scalar, auto-assigned)
    # Quantity buckets (only relevant ones non-zero)
    "on_so": -3.0,                      # release SO commitment (transfer)
    "on_po": 0, "on_wo": 0,
    "on_in": 3.0,                       # invoice add
    "on_r": 0, "on_p": 0,
    "on_hand": -3.0,                    # deduct on_hand (transfer)
    # Pricing snapshot
    "unit_cost": 345.6,
    "unit_price": 721.0,
    # Line-pair IDs (forbids duplicates)
    "invoice_line_id": 8,
    "order_line_id": 5,
    # Audit
    "reason": "in line add (releases so, deducts on_hand)",
    "take_action": 1,
    "transaction_type": "invoice",
    "transaction_model": "invoice",
    "links": {"order": {"parent_id": 37}}
}
```

---

## Duplicate Prevention

Three layers protect against duplicate Pending records:

1. **In-memory `seen_pairs`** — skips duplicate `(invoice_line_id, order_line_id)` in the same batch
2. **DB-level guard** — queries `Pending.objects.filter(data__invoice_line_id=X, data__order_line_id=Y, dt_processed=0)` before creating
3. **Signal suppression** — `_pending_created = True` on every saved line prevents `post_save` signal from creating a second Pending

---

## Transfer Flow (Order → Invoice)

When R25 creates an invoice from an order:

1. R25 calls `saveTransactionWithLines("invoice", payload)` → `POST /wcapi/transaction/save/`
2. Header has `parent_id` (order PK) and `parent_model: "order"`
3. Each invoice line has `refs.source.order_line_id` pointing to the source order line
4. **One Pending per invoice line** captures:
   - `on_in = +qty` (invoice add)
   - `on_so = -qty` (release SO commitment)
   - `on_hand = -qty` (deduct on-hand)
5. R25 then calls `saveRecord(order, {id, is_active: false})` → `POST /wcapi/save/` to deactivate the order (no lines, no pending)
6. Source order lines are updated in Phase 3: `children_active` tracker built, remaining recomputed, status set to "transferred" when remaining ≤ 0

---

## Generic Save Path (`/wcapi/save/`)

Used for non-transaction saves and the second call in a transfer flow.

- Line processing in `save_view.py` `post()` ~L770-845
- Sets `_pending_created = True` before `.save()`
- Calls `LineItemService._create_pending_for_new_line()` per line
- One `dispatch_pending_processing()` after all lines

This is the older per-line pattern. It works correctly because it sets the flag BEFORE save, then creates the Pending explicitly.

---

## Signal Safety Net

`apps/transactions/signals.py` registers `post_save` handlers for all 5 line types. These are a **fallback** for code paths that bypass explicit pending creation (e.g., DRF views, shell, tests).

The handler checks `getattr(instance, '_pending_created', False)` — if True, it returns immediately. This prevents duplication when the explicit path has already created the Pending.

---

## Frontend Integration

### saveTransactionWithLines (R25)

```typescript
import { saveTransactionWithLines } from '@/api/wcapi';

// Create new order with lines
const result = await saveTransactionWithLines('order', {
  header: {
    id_customer: 123,
    status: 'open'
  },
  lines: [
    { item_id: 456, quantity: 10, price: { sell: 99.99 } },
    { item_id: 789, quantity: 5, price: { sell: 49.99 } }
  ]
});
```

### Transfer (Order → Invoice)

```typescript
// Step 1: Create invoice from order
const invoice = await saveTransactionWithLines('invoice', {
  header: {
    parent_id: orderId,
    parent_model: 'order',
    id_customer: order.id_customer
  },
  lines: orderLines.map(ol => ({
    item_id: ol.item_id,
    quantity: ol.quantity,
    price: ol.price,
    refs: { source: { order_line_id: ol.id } }
  }))
});

// Step 2: Deactivate source order
await saveRecord('order', { id: orderId, is_active: false });
```

---

## Response Format

### Success Response

```json
{
  "status": "success",
  "data": {
    "record": {
      "id": 38,
      "uuid": "...",
      "ida": "INV-1001",
      "status": "open"
    },
    "lines": [
      { "id": 8, "line_number": 10, "item_id": 456 },
      { "id": 9, "line_number": 20, "item_id": 789 }
    ],
    "pending_count": 2
  }
}
```

### Error Response

```json
{
  "status": "fail",
  "error": {
    "code": "validation_error",
    "details": {
      "lines.0.quantity": ["Quantity must be positive"]
    }
  }
}
```

---

## Related Documentation

- [celery-redis-pending.md](celery-redis-pending.md) — Background processing of Pending records
- [06-api-conventions.md](06-api-conventions.md) — Model naming and related data conventions
- [05-model-registry.md](05-model-registry.md) — Available models and their configurations
