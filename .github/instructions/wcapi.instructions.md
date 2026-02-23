# WCAPI Instructions — Transaction Save & Pending System

These instructions supplement `copilot.instructions.md` with details specific
to the WCAPI save endpoints and the Pending inventory system.

---

## Two Save Endpoints

| Endpoint | View | Service | Purpose |
|----------|------|---------|---------|
| `POST /wcapi/save/` | `SaveWcapiView.post()` in `apps/core/views/save_view.py` | `LineItemService._create_pending_for_new_line()` | Generic create/update for any model. Used for order deactivation after transfer, non-transaction saves. |
| `POST /wcapi/transaction/save/` | `WCAPITransactionSaveView.post()` in `apps/transactions/views/wcapi.py` L124 | `save_transaction_with_lines()` in `apps/transactions/services/transaction_save.py` | Transaction saves with lines. R25 uses `saveTransactionWithLines()` for all transaction saves. |

---

## Transaction Save — Collect-then-Create Pattern (2026-02-21)

### Why Collect-then-Create

The previous per-line pattern created Pending records inside the save loop.
Combined with Django's `post_save` signal safety net, this caused **duplicate
pending records** (signal fired + explicit create = 2 per line).

The new pattern:
1. Saves all lines with `_pending_created = True` (suppresses signals)
2. Collects pending delta dicts into an array during the loop
3. After all lines are committed, creates Pending records from the array
4. Fires one `dispatch_pending_processing()` at the end

### Backend Authority

The backend is authoritative for all pending-related decisions:

| Decision | Source | NOT from |
|----------|--------|----------|
| Pending type code (SO/IN/PO/PP/WO) | `_PENDING_TYPE_MAP[model_key]` | Front-end refs |
| Is this a transfer? | `header.parent_id` + `header.parent_model` | Front-end flags |
| Quantity buckets | Derived from type + transfer status | Front-end data |
| Duplicate detection | `(invoice_line_id, order_line_id)` pair guard | None |

### Key Functions in `transaction_save.py`

| Function | Line | Purpose |
|----------|------|---------|
| `_PENDING_TYPE_MAP` | ~L52 | Maps model_key → type code |
| `_create_pending_from_deltas()` | ~L62 | Creates Pending records from collected array |
| `_update_source_lines_after_transfer()` | ~L250 | Bumps actioned/remaining on source lines |
| `save_transaction_with_lines()` | ~L487 | Main entry point — 4-phase save |

### Line Number Assignment

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

### Pending Data Structure

Each Pending record's `data` JSON contains:

```python
{
    "type_id": "IN",                    # SO, PO, PP, IN, WO
    "item_id": 243,
    "item_num": "WIDGET-A",
    "doc_id": "INV-1001",
    "doc_pk": 38,
    "line_id": 8,                       # the new line PK
    "line_num": 10,                      # line_number (scalar, auto-assigned)
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

### Duplicate Prevention

Three layers:

1. **In-memory `seen_pairs`** — skips duplicate `(invoice_line_id, order_line_id)` in the same batch
2. **DB-level guard** — queries `Pending.objects.filter(data__invoice_line_id=X, data__order_line_id=Y, dt_processed=0)` before creating
3. **Signal suppression** — `_pending_created = True` on every saved line prevents `post_save` signal from creating a second Pending

### Transfer Flow (Order → Invoice)

When R25 creates an invoice from an order:

1. R25 calls `saveTransactionWithLines("invoice", payload)` → `POST /wcapi/transaction/save/`
2. Header has `parent_id` (order PK) and `parent_model: "order"`
3. Each invoice line has `refs.source.order_line_id` pointing to the source order line
4. **One Pending per invoice line** captures:
   - `on_in = +qty` (invoice add)
   - `on_so = -qty` (release SO commitment)
   - `on_hand = -qty` (deduct on-hand)
5. R25 then calls `saveRecord(order, {id, is_active: false})` → `POST /wcapi/save/` to deactivate the order (no lines, no pending)
6. Source order lines are updated in Phase 3: actioned bumped, remaining decremented, status set to "transferred"

---

## Generic Save Path (`/wcapi/save/`)

Used for non-transaction saves and the second call in a transfer flow.

- Line processing in `save_view.py` `post()` ~L770-845
- Sets `_pending_created = True` before `.save()`
- Calls `LineItemService._create_pending_for_new_line()` per line
- One `dispatch_pending_processing()` after all lines

This is the older per-line pattern. It works correctly because it sets
the flag BEFORE save, then creates the Pending explicitly.

---

## Signal Safety Net

`apps/transactions/signals.py` registers `post_save` handlers for all 5 line
types. These are a **fallback** for code paths that bypass explicit pending
creation (e.g. DRF views, shell, tests).

The handler checks `getattr(instance, '_pending_created', False)` — if True,
it returns immediately. This prevents duplication when the explicit path has
already created the Pending.

---

## Dispatch & Processing

`dispatch_pending_processing()` in `apps/products/dispatch_pending.py`:

1. Checks for a live Celery worker (cached 60s in Redis)
2. If alive → `apply_async()` with 2s countdown
3. If no worker → processes inline synchronously

Celery Beat also kicks the processor every 30s as a safety net.

The processor (`process_line_item_pending()`) groups Pending by item_id,
aggregates deltas, locks the Item row, applies to `item.data.quantity`,
and marks records as processed (`dt_processed = now_ms`).
