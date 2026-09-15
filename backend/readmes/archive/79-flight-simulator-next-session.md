# Flight Simulator — Next Session (2026-08-19)

**Priority**: Fix the line save → Pending creation gap, then build the clean line transfer procedure.

---

## The Bug

Proposal line saves in the flight simulator but `_create_pending_for_new_line` doesn't fire.

**What happens**: User adds a line item to a proposal in the flight simulator, clicks Save. The line persists to the database. But no Pending record is created, so `try_apply()` never runs, `item.quantity` doesn't update, and the left panel doesn't show the new rows.

**Where to look**: Two save paths exist and only one creates pending records:

| Path | Creates Pending? | Used by |
|------|-----------------|---------|
| `save_view.py` → `_create_pending_for_new_line` (line 945-946) | Yes | `/wcapi/save/` with line data |
| `line_views.py` → `_create_pending_for_new_line` (multiple places) | Yes | Direct line API calls |
| `saveRecord()` from React without line FK resolution | **No** | Flight simulator? |

The flight simulator's `handleSave` in `TransactionDetail.tsx` calls either `saveTransactionWithLines()` (if dirty lines exist) or `saveRecord()`. Check which path the flight sim line add takes and whether it reaches the pending creation code.

**Additional bug**: Adding an item via +Item clears the customer/company information from the form. The `handleLinesChange` callback does `setEditData(prev => { ...prev, lines })` which should preserve other fields, but something in the re-render cycle is losing the customer data. Investigate whether `editData` is being reset by `fetchData()` or a stale closure.

**Key files**:
- `webClerk3/apps/core/views/save_view.py` — line 945: `service._create_pending_for_new_line()`
- `webClerk3/apps/transactions/services/line_item_service.py` — `_create_pending_for_new_line()` at line 1109
- `webClerk3/apps/transactions/views/line_views.py` — multiple call sites
- `React2025/src/apps/transactions/components/TransactionDetail.tsx` — `handleSave` at line 213
- `React2025/src/pages/admin/FlightSimConsole.tsx` — the flight sim component

---

## The Bigger Issue: Clean Line Transfer Procedure

Bill wants one clean procedure for transferring line behaviors between transaction types. Currently the code has multiple paths that are inconsistent. The flight simulator exposes this because it walks the full lifecycle:

```
Proposal → Order → Invoice → Purchase → Receive
```

Each transition needs:
1. **Line save** → creates the line record
2. **Pending created** → records what will change (on_p +15, on_so +9, etc.)
3. **Pending.try_apply()** → applies to item.quantity immediately (or queues for celery if locked)
4. **Left panel updates** → shows the three-row pattern: transaction_line, pending, item state

The procedure must be the same for every transaction type. No special cases.

---

## What Was Built This Session

### Pending.try_apply() — Universal Auto-Apply

Every `Pending` record tries to apply itself on `save()`. This is the universal behavior for ALL pending types, not just inventory.

- `Pending.save()` → `try_apply()` → dispatches by `model_name`/`purpose`
- For inventory: `_apply_inventory()` uses `select_for_update(nowait=True)`
- If item row-locked: `OperationalError` caught, stays `dt_processed=0`, celery picks up
- Future handlers add branches to `try_apply()` (ledger_sync, denorm_refs, etc.)

**File**: `webClerk3/apps/core/models/pending.py`

### PendingInventoryAdjustment Removed

The parallel inventory pending system is gone. One model (`Pending`), one path.

**Deleted**: `inventory_pending.py`, `inventory_adjustment_processor.py`, `pending_inventory_adjustment.py` schema

**Rerouted** (13+ files): `order_production.py`, `conversion.py`, `manage_view.py`, `inventory_adjustment_views.py`, `pending_archive.py`, `inventory_metrics.py`, `products/signals.py`, `products/tasks.py`, management commands, 5 test files.

### Flight Simulator UI

- **Left panel**: Renders three-row pattern (transaction_line → pending → item state)
- **Pending colors**: Red = unapplied, Gold = applied
- **Right panel**: Retains saved record (doesn't create new one after save)
- **Click = fresh start**, Shift-click = resume last session
- **Workflow conversion**: Right panel switches to new record (order_id, invoice_id)
- **Simplified ida**: No more `qq-fs-proposal-mszejein` — server auto-generates

### Bugs Fixed

- `conversion.py` `refs.source: None` — `setdefault("source", {})` returns existing `None`. Fixed with explicit `if not get(): assign`.
- `get_flight_ledger` renamed to `get_flight_transactions` (ledger is a specific model)
- Celery processor read from `config` but data is in `changes` — fixed
- Derived `on_hand` from `on_in`/`on_r` removed — explicit deltas are authoritative

---

## Item 244 (qqBB200) State

Reset to clean: `on_hand=100`, everything else 0. No pending records, no test transactions. Ready for a clean flight simulator run.

---

## Key Architecture Decision

**Bill**: "Pending records should try to apply themselves when they are saved. If they cannot, item record is locked, they are added to the celery cycle. This should be the same for every use of pending."

This is not an inventory feature. It is the Pending model's universal behavior.
