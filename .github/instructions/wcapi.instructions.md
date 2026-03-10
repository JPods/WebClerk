# WCAPI Instructions — Transaction Save & Pending System

These instructions supplement `copilot.instructions.md` with details specific
to the WCAPI save endpoints, the transfer pipeline, and the Pending inventory
system.

---

## Two Save Endpoints

| Endpoint | View | Service | Purpose |
|----------|------|---------|---------|
| `POST /wcapi/save/` | `SaveWcapiView.post()` in `apps/core/views/save_view.py` L282 | Per-line pending via `LineItemService` (L825) | Generic create/update for any model. Used for order deactivation after transfer, non-transaction saves. |
| `POST /wcapi/transaction/save/` | `WCAPITransactionSaveView.post()` in `apps/transactions/views/wcapi.py` L126 | `save_transaction_with_lines()` in `apps/transactions/services/transaction_save.py` L780 | Transaction saves with lines. R25 uses `saveTransactionWithLines()` for all transaction saves. |

---

## Universal Remaining Formula

All quantity updates across the codebase use the **same** formula:

```
remaining = active − children_active["sum"]
```

When a line has no children, `children_active` is absent and `remaining = active`.

**Field roles**:

| Field | Meaning | Who sets it |
|-------|---------|-------------|
| `staged` | Quantity received from parent (frozen after creation) | Transfer code |
| `active` | The user's working quantity — **never modified by the system** | User / R25 |
| `remaining` | Quantity still available for child transfers | Computed: `active − children_active.sum` |
| `children_active` | Denormalized tracker: `{"sum": N, "lines": [{"id": X, "active": Y}, ...]}` | Transfer code on parent line |

---

## Transfer Code Paths

Four code paths create child transactions from a parent. All maintain
the `children_active` tracker on the source (parent) line.

| Path | File | Entry Point | Trigger |
|------|------|-------------|---------|
| Transfer dropdown | `transaction_save.py` L495 | `_update_source_lines_after_transfer()` | R25 `TransactionDetailBase` Transfer menu → `saveTransactionWithLines()` |
| Convert to Order | `proposal_to_order.py` | `transfer_proposal_to_order()` | R25 `ProposalDetail` Convert button → `POST /tx/proposals/{id}/convert-to-order/` |
| Order to Invoice | `order_to_invoice.py` | `transfer_order_to_invoice()` | R25 Order→Invoice flow → `POST /tx/orders/{id}/convert-to-invoice/` |
| Unified engine | `transfer.py` | `execute_transfer()` | `POST /tx/transfers/execute/` (supports clone, convert, cross-type) |

All four update the parent line's `children_active` and recompute
`remaining = active − children_active.sum`.

### Child active qty changes

When a child line's `active` qty is edited (not a new transfer, but a qty
update on an existing child), `_update_parent_children_active()` in
`transaction_save.py` L403 finds the parent line and updates the matching
entry in `children_active.lines`, then recomputes remaining.

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
6. Source order lines are updated via `_update_source_lines_after_transfer()`:
   children_active tracker built, remaining recomputed, status set to "transferred" when remaining ≤ 0

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

---

## Pending as Compensating Transactions (Cross-Domain)

The inventory pending pattern above is one instance of a broader architectural
pattern: **Pending as compensating transactions**. The same `Pending` model is
used for ledger sync (`purpose='ledger_sync'`) and will be adopted for other
domains where record contention or transient failures can cause data drift.

Key rules for all Pending domains:
- Happy path creates AND processes the Pending in the same request cycle
- Failure leaves `dt_processed=0` for Celery to retry
- Processors must be idempotent (running twice = same result)
- Stamp the source record with sync metadata when possible (e.g. `invoice.metadata.ledger.dt_sync`)
- Never delete processed Pendings — they serve as audit trail

See `readmes/topics/architecture/pending-compensating-transactions.md` for the
full pattern and instructions on adding new Pending domains.

---

## User Action Awareness & Dashboard Tools

AI agents (Copilot and Alice) should observe user actions and usage patterns to offer dashboard tools and shortcuts that help users work more efficiently.

- Monitor which records, models, or actions are most frequently accessed or modified by the user.
- Suggest relevant dashboard widgets, analytics, or shortcuts based on user context.
- For every user, surface a dashboard graph showing the percentage completed of their "inprocess" action records, and estimate hours remaining or spent.
- Use the ActionsMixin and related models to compute and visualize user progress and bottlenecks.
- Offer actionable insights, such as links to resume in-process work, reminders for overdue actions, or summaries of recent activity.
- Provide quick links or buttons for common next steps directly in the dashboard when possible.

**Example:**
- Show a progress bar or pie chart for each user representing the % of their "inprocess" actions completed.
- Display an estimated hours metric based on historical completion times for similar actions.

These dashboard tools should be context-aware and update as the user's actions and data change.
