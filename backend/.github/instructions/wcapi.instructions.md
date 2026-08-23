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

### Effective Transfer Quantity (Critical)

For transfer validation and Pending deltas in `save_transaction_with_lines()`,
the backend resolves the line quantity using this precedence:

```
active -> staged -> placed -> actioned
```

Why:
- `active` is the user's current edited value and is authoritative for pending math.
- `staged` is typically the transferred snapshot from the source line.
- `placed` / `actioned` remain as compatibility fallbacks for legacy payloads.

Example:
- Source order line transferred with `staged=7`
- User edits invoice line to `active=4` before save
- Pending uses `qty=4` (not `7`) for `on_in`, `on_so`, and `on_hand` deltas.

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

## Label Policy (Copilot + Alice)

For debugging consistency in all generated/admin UI outputs:

- Use exact schema names and exact case for all scalar labels.
- For object/JSON-derived labels, use `.exact_name` format with leading dot.
- Do not capitalize, title-case, prettify, or humanize labels.
- Apply this rule everywhere (list headers, detail labels, exports, and generated config).

## Readme Action Header Policy (Copilot + Alice)

When creating or updating operational readmes/playbooks in this domain, include this block at the top (right under the title):

```text
Action:
Function:
Frequency:
Process:
```

Keep each value short and execution-oriented.

- `Function:` should name the concrete callable when one exists, such as a function, service method, management command, task, endpoint, or script.
- If no single callable exists, `Function:` should name the owning subsystem or process owner.

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
