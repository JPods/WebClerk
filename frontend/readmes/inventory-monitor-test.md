# Inventory Monitor & Proposal Flow Test

How to use the floating Inventory Monitor window to observe real-time
inventory bucket changes during the transaction lifecycle.

---

## Inventory Monitor Window

### What It Does

A small draggable floating panel that polls a single Item's quantity buckets
every 10 seconds and displays them live. Use it to verify that inventory
deltas are applied correctly as you create, convert, and invoice transactions.

### Launching

1. Look at the top title bar (MacTopBar), right side near the signed-in user
2. Click the **box icon** (green crate) button — it sits between the
   Task Manager indicator and the user avatar
3. The floating window appears in the upper-right corner

### Controls

| Control | Action |
|---------|--------|
| **Item ID** input | Enter any item primary key |
| **Go** button | Load that item and start polling |
| **Refresh** icon (circular arrows) | Force an immediate fetch |
| **Title bar drag** | Reposition the window anywhere on screen |
| **X** button | Close the monitor |

The window auto-refreshes every 10 seconds. The timestamp at the bottom
shows when the last poll completed.

### Displayed Buckets

| Bucket | Meaning |
|--------|---------|
| **On Hand** | Physical inventory in stock |
| **Available** | Computed: on_hand − allocated |
| **Allocated** | Reserved for specific orders |
| **On SO** | Committed to sales orders |
| **On PO** | On open purchase orders |
| **On WO** | On open work orders |
| **On IN** | Invoiced (shipped out) |
| **On P** | On proposals (forecast × probability) |

---

## Test Scenario: Proposal → Order → Invoice

### Prerequisites

Reset item 243 to a known baseline:

```bash
python manage.py reset_item_quantities --item-id 243
```

Verify:

```bash
python manage.py reset_item_quantities --show --item-id 243
```

Expected output:

```
Item #243 (BB401):
  on_hand=100, available=100, allocated=0
  on_so=0, on_po=0, on_wo=0, on_in=0, on_p=0
```

### Setup

1. Open the Inventory Monitor (box icon in MacTopBar)
2. Set **Item ID = 243**, click **Go**
3. Confirm all buckets show the reset baseline above

---

### Step 1 — Create Proposal

| Field | Value |
|-------|-------|
| Transaction type | Proposal |
| Customer ID | 82 |
| Line item | Item 243 (BB401) |
| Quantity | 3 |
| Probability | 100% (default) |

**Action:** Save the proposal with 1 line (Item 243, qty 3).

**Expected inventory change on Item 243:**

| Bucket | Before | Delta | After |
|--------|--------|-------|-------|
| on_p | 0 | +3 | **3** |
| on_hand | 100 | — | 100 |
| on_so | 0 | — | 0 |
| available | 100 | — | 100 |
| _all others_ | 0 | — | 0 |

**What to watch:** Within 10 seconds the Inventory Monitor should show
`On P = 3`. All other buckets remain unchanged.

> If the proposal's probability were set to 50%, `on_p` would be
> `3 × 0.5 = 1.5` instead.

**Outcome:** ☐ Pass / ☐ Fail — `on_p` = ____

---

### Step 2 — Convert Proposal to Order

**Action:** Use the proposal-to-order conversion (or manually create an
Order for Customer 82 with the same line: Item 243, qty 3).

**Expected inventory change on Item 243:**

| Bucket | Before | Delta | After |
|--------|--------|-------|-------|
| on_so | 0 | +3 | **3** |
| on_p | 3 | −3 * | **0** * |
| on_hand | 100 | — | 100 |
| available | 100 | — | 100 |

> \* `on_p` release depends on whether the proposal lines are deleted
> during conversion. If `preserve_proposal=false` and the lines are
> removed, the `post_delete` signal reverses the `on_p` delta. Watch the
> monitor to confirm.

**Outcome:** ☐ Pass / ☐ Fail — `on_so` = ____, `on_p` = ____

---

### Step 3 — Create Invoice from Order

**Action:** Convert the order to an invoice (or manually create an Invoice
for Customer 82 with Item 243, qty 3, linked to the order).

**Expected inventory change on Item 243:**

| Bucket | Before | Delta | After |
|--------|--------|-------|-------|
| on_in | 0 | +3 | **3** |
| on_so | 3 | −3 | **0** |
| on_hand | 100 | −3 | **97** |
| available | 97 | — | **97** |
| on_p | 0 | — | 0 |

**What to watch:** The Inventory Monitor should show `On Hand` drop from
100 → 97, `On SO` return to 0, and `On IN` rise to 3.

**Outcome:** ☐ Pass / ☐ Fail — `on_hand` = ____, `on_so` = ____, `on_in` = ____

---

## Summary Table

| Step | Action | on_hand | on_so | on_in | on_p | available |
|------|--------|---------|-------|-------|------|-----------|
| 0 | Reset | 100 | 0 | 0 | 0 | 100 |
| 1 | Create Proposal (qty 3) | 100 | 0 | 0 | **3** | 100 |
| 2 | Convert to Order | 100 | **3** | 0 | **0** | 100 |
| 3 | Create Invoice | **97** | **0** | **3** | 0 | **97** |

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Buckets don't change after save | Is `process_pending_inventory` running? Check for pending records. |
| `on_p` doesn't change | Verify the proposal line saved with `pending_type='PP'`. Check `PendingInventory` table. |
| Monitor shows "Item not found" | Confirm Item 243 exists: `python manage.py reset_item_quantities --show --item-id 243` |
| Monitor not polling | Check browser console for API errors. The `/wcapi/get/?model_name=item&id=243` endpoint must be reachable. |

---

## Related Files

| File | Purpose |
|------|---------|
| `src/components/header/InventoryMonitor.tsx` | Floating monitor component |
| `src/layout/MacTopBar.tsx` | Top bar with launch button |
| `apps/products/management/commands/reset_item_quantities.py` | Reset script |
| `apps/transactions/services/line_item_service.py` | Pending inventory creation |
| `apps/transactions/services/pending_inventory_processor.py` | Applies deltas to Item.quantity |
| `apps/transactions/services/proposal_to_order.py` | Proposal → Order conversion |
| `readmes/topics/inventory/inventory_deltas.md` | Delta bucket reference |
