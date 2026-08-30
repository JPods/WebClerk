# Flight Simulator — Next Session Steps

**Status:** Prototype working. Save chain complete. Transaction display and pending processing need rework.

---

## Step 1: Rework the Transaction Display (`get_flight_transactions`)

**File:** `webClerk3/apps/products/services/inventory_flight_sim.py`

The left panel shows **impact at every transaction** — not a summary. Three rows per event: the transaction line (cause), the pending record (mechanism), and the item state (effect).

**Three row types:**
- **transaction_line** — the line that was saved (proposal_line, order_line, etc.). Shows what the user did.
- **pending** — the pending record created by the line save. Shows the deltas (+15, -9).
- **item** — item.quantity after pending applied. Shows absolute values — the new truth.

**Full lifecycle example:**

| Row | Type | ida | on_hand | on_p | on_so | on_po | GL | Description |
|-----|------|-----|---------|------|-------|-------|----|-------------|
| 1 | item | qqBB200 | 100 | 0 | 0 | 0 | — | starting state |
| 2 | proposal_line | DEV-772 | — | 15 qty | — | — | — | line saved: 15 units of qqBB200 |
| 3 | pending | DEV-772 | — | +15 | — | — | — | on_p +15 |
| 4 | item | qqBB200 | 100 | 15 | 0 | 0 | — | state after proposal |
| 5 | order_line | DEV-xxx | — | 9 qty | — | — | — | 9 units converted from proposal |
| 6 | pending | DEV-xxx | — | -9 | +9 | — | — | on_p -9, on_so +9 |
| 7 | item | qqBB200 | 100 | 6 | 9 | 0 | — | state after order |
| 8 | invoice_line | DEV-xxx | — | 4 qty | — | — | yes | ship 4 units — first financial event |
| 9 | pending | DEV-xxx | -4 | — | -4 | — | AR↑ Rev↑ COGS↑ Inv↓ | on_hand -4, on_so -4 |
| 10 | item | qqBB200 | 96 | 6 | 5 | 0 | — | state after invoice |
| 11 | purchase_line | DEV-xxx | — | — | — | 14 qty | — | purchase 14 units at cost |
| 12 | pending | DEV-xxx | — | — | — | +14 | — | on_po +14 |
| 13 | item | qqBB200 | 96 | 6 | 5 | 14 | — | state after purchase |
| 14 | receive_line | DEV-xxx | +11 | — | — | -11 | yes | receive 11 of 14 ordered |
| 15 | pending | DEV-xxx | +11 | — | — | -11 | Inv↑ AP↑ | on_hand +11, on_po -11 |
| 16 | item | qqBB200 | 107 | 6 | 5 | 3 | — | state after receive |

**Changes needed:**
- Walk events chronologically — three rows per event
- Transaction line row: shows what the user did (type, qty, item)
- Pending row: shows deltas (+15, -9) and GL impact where applicable
- Item row: shows absolute values — running totals after pending applied

---

## Step 2: Fix Pending Auto-Processing

**Problem:** `apply_pending_for_item()` in `apps/products/services/inventory_pending.py` returns `applied_count: 0` because it expects `changes` as a list of `[{field, old, new}]` but `LineItemService` creates a flat dict `{on_p: 15.0, on_so: 0, ...}`.

**Fix options:**
1. Update `apply_pending_for_item` to handle the flat dict format
2. Or update `LineItemService._create_pending_record` to write `[{field, old, new}]` format

Option 1 is better — the flat dict format is richer (includes doc_id, item_num, line_id, etc.) and is what's actually in the database.

**After fix:** Celery task `process_pending_inventory_task` should pick up unprocessed pending records and apply them to `item.quantity` automatically.

---

## Step 3: Extend Through Full Lifecycle

Each step needs:
- Right panel: correct transaction form (proposal/order/invoice/purchase)
- Save: creates line + pending
- Pending auto-applied to item.quantity
- Left panel: shows the new rows (pending + updated item state)

### 3a: Proposal (done)
- User adds 15 units of qqBB200 to proposal
- on_p goes from 0 to 15
- No GL impact

### 3b: Order (from proposal)
- Use Workflow > "To Order" to convert 9 of 15 units
- on_p goes from 15 to 6 (9 moved)
- on_so goes from 0 to 9
- No GL impact — order is a commitment, not a financial event

### 3c: Invoice (from order)
- Create invoice for 4 of 9 ordered units
- on_so goes from 9 to 5
- on_hand goes from 100 to 96 (shipped)
- GL: AR debit, Revenue credit, Tax credit, COGS debit, Inventory credit, Commission
- **This is the financial event** — first time GL entries appear

### 3d: Purchase
- Create purchase for 14 units at cost
- on_po goes from 0 to 14
- No GL impact — PO is a commitment

### 3e: Receive (from purchase)
- Receive 11 of 14 ordered units
- on_po goes from 14 to 3
- on_hand goes from 96 to 107
- GL: Inventory debit, AP credit

### 3f: Payment, Discount, Write-off
- Partial payment $30 of $42 invoice
- $10 discount on remaining
- $2 write-off
- All purely financial — no inventory change, only GL

---

## Step 4: Wire the Simulation Flow

**File:** `React2025/src/pages/admin/FlightSimConsole.tsx`

When user completes proposal step and clicks "To Order" in Workflow dropdown:
1. The order is created (server-side workflow)
2. Right panel switches to show the new order
3. Left panel refreshes to show the new pending + item state rows
4. User adds items to order, saves, watches quantities change

The `onAfterSave` callback already refreshes the left panel. Need to handle workflow transitions that create new records.

---

## Step 5: Clean Up

- Delete item 421 (qqbb200-DELETED) — hard delete or leave as-is
- Clean up qq-fs-proposal-* test records (proposals 84-98)
- Reset qqBB200 quantity to on_hand=100, all others zero
- Clean up orphan pending records for item 244
- Fix AI Assistant z-index overlay on Add button

---

## Key Files

| File | What it does |
|------|-------------|
| `inventory_flight_sim.py` | Backend: `get_flight_transactions`, `get_item_flight_state`, `get_flight_scenario`, `get_item_by_ida` |
| `FlightSimConsole.tsx` | Frontend: select list, item summary, transaction array, form panel |
| `FlightSimConsole.css` | Styles using --db-* CSS variables |
| `save_view.py` | Save endpoint: FK normalization, negative ID handling, record merge, line processing |
| `line_item_service.py` | Creates pending records when lines are saved |
| `signals.py` | `_resolve_item_id` — finds item from line's `item_fk_id` |
| `inventory_pending.py` | Processes pending records into item.quantity (NEEDS FIX) |
| `TransactionDetail.tsx` | Transaction form with `onAfterSave` callback |

---

## What's Working

- `/flight-simulator` renders select list with 8 simulation types
- Clicking a sim loads qqBB200 item summary + creates blank proposal
- Customer search (Riverside Sports) works
- Item search (qqBB200) works, Add button adds line to grid
- Save persists header + line items + creates pending record
- Left panel auto-refreshes after save via `onAfterSave`
- All 5 transaction models have full layout sections (header + line_card + tabs) in both App and Admin

## What's Not Working

- Pending records don't auto-apply to item.quantity (processor format mismatch)
- Left panel doesn't show row-by-row impact pattern yet (shows raw events)
- AI Assistant overlay intercepts Add button clicks (workaround: use JS click)
- Only proposal step implemented — order/invoice/purchase/receive not wired
