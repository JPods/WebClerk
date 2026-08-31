# Flight Simulators -- Interactive Training for WebClerk

## What They Are

Flight simulators are step-by-step training windows where users perform real
actions and watch data change at each stage. They teach how the system works
by doing, not reading.

The name comes from aviation: you don't learn to fly by reading the manual.
You learn by sitting in the simulator, making inputs, and watching the
instruments respond. Same principle applied to commerce.

---

## Architecture Rules

Three architectural rules established during the line-save pipeline build
(2026-08-19). These apply to all WC3 transaction handling.

### 1. Front End Sends Data, Backend Manages Data and Relationships

React sends plain numbers inside JSON envelopes. Never Django FK descriptor names
(`item_fk`) or internal column names (`item_fk_id`). The server reads IDs from
envelopes and sets FK columns.

```
React sends:  { item: { item_id: 421, description: "..." }, quantity: { active: 15 } }
Server does:  line_obj.item = envelope_data  (JSONField)
              line_obj.item_fk_id = envelope_data['item_id']  (FK column)
```

**Root cause this fixed:** `setattr(line_obj, 'item_fk', 421)` throws `ValueError`
because Django FK descriptors reject raw integers. Exception was silently caught --
lines never persisted, server returned "success".

### 2. Each Transaction Model Owns One Inventory Bucket

| Model | Owns | Conversion releases |
|-------|------|-------------------|
| Proposal | on_p | on_p -= qty |
| Order | on_so | on_so -= qty |
| Purchase | on_po | (none from sell-side) |
| Invoice | on_hand, on_in | (none -- source handles on_so) |

Conversion pending only releases the source bucket. The target line save handles
the target bucket. No cross-bucket adjustments anywhere.

**Root cause this fixed:** on_so double-counted (30 instead of 15) because both
the conversion pending and the line save pending adjusted on_so.

### 3. Users Edit Arrays, Not Database Records

The database is for persistence, not editing. Users edit arrays in memory.
The database gets touched only at the moment of save, locks for the shortest
possible time, then releases.

- Conversion creates header only, returns line data array to React
- User reviews lines, adjusts quantities
- On Save: server creates line records, fires pending for each
- Lock window = the save loop only

### The Linear Flow

```
Conversion: copy line data -> return array to React
                |
User: review -> adjust qty -> Save
                |
save_view: create target line -> fire target pending (own bucket)
                |
Target line tells source line -> save source line -> fire source pending (own bucket)
                |
Done
```

Each step triggers exactly one thing. Each pending is a consequence of one save.

### Sell-Side vs Buy-Side

| Conversion | Type | Customer transfers | Source adjustment | Price source |
|---|---|---|---|---|
| Proposal -> Order | Sell | Yes | Release on_p | Copy from proposal |
| Order -> Invoice | Sell | Yes | Release on_so | Copy from order |
| Proposal -> Invoice | Sell | Yes | Release on_p | Copy from proposal |
| Order -> Purchase | Buy | No | None | Item record |
| Order -> Work Order | Buy | No | None | Item record |

Purchase and work order are buy-side -- a convenience so users don't re-enter item data.
They have zero impact on sell-side buckets. Customer data does not transfer.
If users want to track a purchase relative to a customer, add the customer
into `.refs.links.customer[]` with order reference in `.refs.links.order[]`.

### Scars Paid

1. **CoreModel.data -> config rename** -- `proposal_to_order.py` and `order_to_invoice.py`
   still used `data=` in `Pending.objects.create()`. Silent data loss for months.
   Rule: field renames require repo-wide grep.

2. **Single-bucket violation** -- conversion pending and line save pending both adjusted
   on_so. Invisible until the flight simulator walked the full lifecycle.
   Rule: each model owns one bucket, no exceptions.

3. **FK descriptor ValueError** -- `setattr(line_obj, 'item_fk', 421)` silently failed
   inside `except Exception`. Invisible because the header save succeeded.
   Rule: front end sends data, backend manages relationships.

---

## Available Flight Simulators

### Flight Simulator: Inventory (`/flight-sim-inventory`)

Teaches how inventory quantities, pending records, and GL entries change as
transactions flow through the system. Nine steps:

| Step | Action | Qty Changes | GL Impact |
|------|--------|-------------|-----------|
| 1 | Starting inventory (on_hand=100) | -- | -- |
| 2 | Proposal for 15 units | on_p: 0->15 | None (quote only) |
| 3 | Convert 9 to Order | on_p: 15->6, on_so: 0->9 | None (commitment only) |
| 4 | Invoice 4 units | on_hand: 100->96, on_so: 9->5 | AR $42 / Revenue $40 / Tax $2 / COGS $24 / Inventory $24 / Commission $2 |
| 5 | Purchase 14 units | on_po: 0->14 | None (until received) |
| 6 | Receive 11 units | on_hand: 96->107, on_po: 14->3 | Inventory $66 / AP $66 |
| 7 | Partial payment $30 | -- | Cash $30 / AR $30 |
| 8 | Discount $10 | -- | Discount Exp $10 / AR $10 |
| 9 | Write-off $2 | -- | Bad Debt $2 / AR $2 |

**What users learn:**
- Which transactions move inventory and which don't
- Why pending records exist (they track the movement between stages)
- When GL entries are created vs. when they aren't
- How a $42 invoice settles: $30 cash + $10 discount + $2 write-off
- Margin erosion: 40% gross -> 5% net after commission, discount, and bad debt
- Why Alice tracks erosion (because this happens constantly)

**Config:** 5% tax, 5% commission. Easy mental math so the learner focuses
on concepts, not arithmetic.

### Sales Pipeline (`/sales-pipeline`)

Funnel dashboard: Actions -> Proposals -> Orders -> Revenue.

Uses the impact assessment loop (see below) to connect selling actions
to outcomes. Users choose an `action_type` (call, email, visit, meeting,
demo, marketing, referral, social, event, follow_up, other) and rate
predicted impact. Alice auto-fills actual impact later.

### Cash Conversion (`/cash-conversion`)

Teaches where money stalls in the pipeline:

Order -> Invoice -> Payment -> GL -> Period Close

Each stage shows average days and stalled records. Users learn that a
healthy business has short, predictable stage durations. The journal
audit dashboard (`/journal-audit`) opens from here for GL exceptions.

### Journal Audit (`/journal-audit`)

Three-panel GL posting review:

| Panel | What it shows | User action |
|-------|--------------|-------------|
| Queue | Transactions ready to post | Click "Post Journals" to batch-post |
| Exceptions | Out-of-balance -- can't post | Fix source or ForceToBalance |
| Skipped | Hold, consigned, zero-amount | Informational -- change status to unblock |

**ForceToBalance:** When a journal is out of balance (e.g., FX rounding on a
low-cost item), the user clicks "Force to Balance," writes a statement explaining
why (minimum 10 characters), and the system posts an adjusting line. The statement
is stored in three places: the GL line's note, the GL line's metadata, and the
source transaction's `metadata.gl_accounts.force_balance[]`.

**FX auto-absorption:** Foreign currency residuals under $2 are automatically
absorbed into the FX rounding account (WC2 GL2 rule). No user action needed.

**JournalBatch model:** Every posting run creates a `JournalBatch` header (like
Order -> OrderLine). Stores totals, exception count, absorption count, who ran it,
and when. The batch is the flight recorder for every GL posting event.

### Inventory Velocity (`/inventory-velocity`)

Teaches where capital is working vs. parked:

PO Exposure -> Receipt -> On Hand (ABC) -> Sales -> Reorder

Users learn the difference between stars (high margin, high velocity)
and dead capital (sitting on the shelf, costing money).

---

## The Impact Assessment Loop

Every selling action carries an `impact` object:

```json
{
  "predicted": 4,
  "actual": 2,
  "refs": {
    "transactions": [
      {"model": "order", "id": 1234, "ida": "SO-1234", "value": 450.00}
    ],
    "explanation": "Customer was comparison shopping"
  }
}
```

**The loop:**

1. **User creates action** -- sets `predicted` (2 seconds, gut feel)
2. **Time passes** -- customer buys or doesn't
3. **Alice scans** -- periodic task finds transactions for that customer,
   auto-fills `actual` and `refs.transactions`
4. **User reviews** -- confirms (0 seconds) or corrects (2 seconds)
5. **Alice learns** -- adjusts future guesses based on corrections
6. **Admin time drops** -- Alice's auto-fill accuracy improves over time

**Not precision, but retrospection.** The numbers are waffly on purpose.
The value is in coming back, seeing the gap, and asking why. The score
is just the hook that forces the retrospection.

**Calibration metrics:**
- `avg_gap`: predicted minus actual, averaged across all retrospected actions.
  Positive = over-optimistic. Negative = under-estimating. Zero = perfect.
- `correction_rate`: how often users change Alice's guess. 40% = still
  learning. 10% = calibrated. 2% = users trust the auto-fill.

---

## Setup Script: Transaction Lifecycle Walkthrough

**Purpose:** Every new user runs this once. Two screens open side by side.

**Screen 1:** Transaction processing (proposal, order, invoice, etc.)
**Screen 2:** Console - db.list collection showing:
- Item record: qqbb200 quantity fields (on_hand, on_po, on_so, available, committed)
- Each transaction as it's created
- Each pending record as it appears and resolves
- GL entries after processing

The console shows quantity at every step, TWICE:
1. After the transaction is saved (pending record exists but hasn't applied)
2. After the pending record applies (quantity changes)

This teaches what pending records do. The gap between "I saved the transaction"
and "the quantity changed" is where understanding lives.

### Setup

- Item: qqbb200
- Starting quantity: on_hand=0, on_po=0, on_so=0, available=0
- Console screen showing item.quantity fields in real-time

### Step 1: Create Proposal for 15

**Action:** New proposal, add 15x qqbb200, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | 0 |
| on_po | 0 | 0 | 0 |
| on_so | 0 | 0 | 0 |
| available | 0 | 0 | 0 |

**Console shows:** Proposal record appears. No pending record - proposals don't move inventory.
**Lesson:** Proposals are intentions. Nothing moves until conversion.

### Step 2: Convert Proposal to Order for 11 (4 remain on proposal)

**Action:** Convert proposal, quantity=11, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | 0 |
| on_po | 0 | 0 | 0 |
| on_so | 0 | 0 | **11** |
| available | 0 | 0 | **-11** |

**Console shows:** Order record appears. Pending record appears (staged). Pending applies - on_so jumps to 11.
**Lesson:** Converting creates the order AND a pending record. The pending record is what moves on_so. Available goes negative - we owe 11 we don't have.
**Also notice:** Proposal still exists with qty=4. Orphaned partials are real.

### Step 3: Post Order to Purchase for 11

**Action:** Post order to purchase, quantity=11, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | 0 |
| on_po | 0 | 0 | **11** |
| on_so | 11 | 11 | 11 |
| available | -11 | -11 | **0** |

**Console shows:** Purchase record appears. Pending record stages, then applies. on_po jumps to 11. Available returns to 0 (11 on_po covers 11 on_so).
**Lesson:** Purchasing doesn't give us inventory. It gives us a promise (on_po). Available improves because the promise offsets the commitment.

### Step 4: Receive 9 (2 remain on PO)

**Action:** Receive against purchase, quantity=9, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | **9** |
| on_po | 11 | 11 | **2** |
| on_so | 11 | 11 | 11 |
| available | 0 | 0 | **0** |

**Console shows:** Receipt record appears. Pending stages. Pending applies - on_hand jumps to 9, on_po drops to 2.
**Lesson:** Receiving converts a promise (on_po) into reality (on_hand). We received 9 of the 11 promised. 2 still on_po. Available stays 0: we have 9 in hand + 2 promised = 11, committed 11 on_so.

### Step 5: Convert Order to Invoice for 7 (4 remain on SO)

**Action:** Convert order to invoice, quantity=7, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 9 | 9 | **2** |
| on_po | 2 | 2 | 2 |
| on_so | 11 | 11 | **4** |
| available | 0 | 0 | **0** |

**Console shows:** Invoice record appears. Pending stages. Pending applies - on_hand drops by 7 (shipped), on_so drops by 7 (fulfilled).
**Lesson:** Invoicing means we shipped the goods. on_hand decreases, on_so decreases. We still owe 4 on the sales order. Available stays 0: 2 in hand + 2 on_po = 4, which matches the 4 still on_so.

### Step 6a: 15 Days Pass - Statement

**Action:** Run statements. Invoice is 15 days old.

**Console shows:** Statement generated for the customer. Lists the open invoice with balance due. No financial impact - statements are informational.
**Lesson:** A statement is a mirror, not a transaction. It shows the customer what they owe. No pending records, no GL entries, no inventory changes. It's communication.

### Step 6b: 30 Days Pass - Late Notice

**Action:** Run aging notices. Invoice is 30 days past due.

**Console shows:** Late notice generated. Touch record created (outbound communication to customer). Action created: "Follow up on past-due invoice."
**Lesson:** A late notice is still communication, not a financial event. But it creates a touch record (proof of contact) and an action (follow-up task). The system documents that you tried. This matters legally.

### Step 6c: Six Weeks Pass - Late Fee

**Action:** Run aging. Invoice is 6 weeks past due. System applies 1.2% late fee.

**Console shows:** Finance charge line added to invoice. Invoice balance increases by 1.2%. AR ledger: additional debit. New GL entry: AR debit, late fee revenue credit.
**Lesson:** Late fees increase what the customer owes without changing what was shipped. Inventory doesn't move. The fee is revenue - the company earned it by waiting. The invoice total grows; the original line items don't change. The fee is its own line with its own GL account.

### Step 7: Pay Invoice with 2% discount and $0.50 write-off

**Action:** Create payment against invoice (now including the late fee). Apply 2% early-pay discount on the original amount. Write off $0.50 as too-trivial-to-collect.

**Console shows:** Payment record appears. Invoice balance goes to 0. Pending record stages payment application. AR ledger: payment amount + discount + write-off = invoice total.
**Lesson:** Payment doesn't touch inventory. It closes the money side. The discount and write-off are separate GL entries - not price changes. The invoice total doesn't change; the payment just has three components.

### Step 8: Process GLs

**Action:** Run GL processing

**Console shows:** GL journal entries appear:
- AR debit (from invoice, step 5)
- Revenue credit (from invoice)
- AR debit (from late fee, step 6)
- Late fee revenue credit (step 6)
- Cash debit (from payment, step 7)
- AR credit (from payment)
- Discount expense debit
- Write-off expense debit

**Lesson:** GL is the accounting record of everything that already happened. It doesn't move inventory or change balances - it records them. Every transaction that touches money has a GL consequence. The discount and write-off get their own expense accounts.

### Step 9: Customer Returns 1

**Action:** Create credit memo for 1x qqbb200. Customer returns the item.

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 2 | 2 | **3** |
| on_po | 2 | 2 | 2 |
| on_so | 4 | 4 | 4 |
| available | 0 | 0 | **1** |

**Console shows:** Credit memo record appears. Pending stages return. on_hand increases by 1 (goods came back). AR ledger: credit memo reduces customer balance.
**Lesson:** Returns run the flow backwards. Quantity goes up, money reverses. Same pending mechanism, opposite direction.

### Step 10: Scrap the Returned Item

**Action:** Write off / scrap 1x qqbb200. The returned unit is damaged and cannot be resold.

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 3 | 3 | **2** |
| on_po | 2 | 2 | 2 |
| on_so | 4 | 4 | 4 |
| available | 1 | 1 | **0** |

**Console shows:** Inventory adjustment record. Pending stages the write-off. on_hand drops by 1. GL: inventory asset credit, scrap/loss expense debit.
**Lesson:** Scrapping removes inventory permanently. The cost of the item moves from asset (inventory) to expense (loss). The item came back from the customer but it's worthless - the system needs to record both the return AND the disposal as separate events. One is a customer transaction, the other is an internal decision.

### Step 11: Refund the Customer

**Action:** Issue refund payment against the credit memo from Step 9.

**Console shows:** Payment record (outbound). Credit memo balance goes to 0. Cash decreases, AR decreases (or goes negative then zeroes). GL: cash credit, AR debit.
**Lesson:** The refund is a payment in reverse - money goes out instead of in. The credit memo is the authority for the refund, just as the invoice was the authority for the original payment. No credit memo = no refund. The audit trail is: return -> credit memo -> refund payment -> GL.

### Step 12: Deal with the Orphans

**Action:** Find and cancel the 4 remaining on the original proposal. Find and close the 4 remaining on the sales order. Find and close the 2 remaining on the purchase order.

| Field | Before | After cleanup |
|-------|--------|--------------|
| on_hand | 2 | 2 |
| on_po | 2 | **0** |
| on_so | 4 | **0** |
| available | 0 | **2** |

**Lesson:** Partial conversions leave orphans. Every open quantity on a transaction is a promise someone needs to keep or explicitly cancel. Closing the orphans releases on_po and on_so back to available. The system doesn't clean these up automatically - that's a business decision, not a system decision. After cleanup, on_hand=2 and available=2 - clean books.

### What the Console Screen Shows

A db.list collection view pulling from multiple models simultaneously:

| Section | Model | Key Fields |
|---------|-------|-----------|
| **Item** | item | ida, on_hand, on_po, on_so, available, committed |
| **Transactions** | proposal, order, purchase, receipt, invoice, payment | ida, status, qty, total, balance |
| **Pending** | pending | model_name, status, qty, staged/applied |
| **GL** | ledger | account, debit, credit, source |

Each section updates live as the user works on Screen 1.

### Key Takeaways

1. **Proposals don't move anything** - they're intentions
2. **Pending records are the mechanism** - the gap between "saved" and "applied" is where the system works
3. **on_po is a promise, on_hand is reality** - receiving converts one to the other
4. **Invoicing means shipped** - on_hand goes down, on_so goes down
5. **Payment doesn't touch inventory** - it closes the money side only
6. **GL records, it doesn't cause** - journal entries document what already happened
7. **Partial conversions leave orphans** - someone has to deal with them
8. **Late fees are revenue, not price changes** - the original line items don't change; the fee is its own line with its own GL account
9. **Returns run backwards** - same pending mechanism, opposite direction
10. **Return and scrap are two events** - return is a customer transaction, scrap is an internal decision. Separate authorities, separate GL entries
11. **Refunds require a credit memo** - no credit memo, no refund. The audit trail is complete
12. **Clean up orphans to clean the books** - canceling orphaned partials releases on_po and on_so back to available

---

## Onboarding Integration

Flight simulators are part of onboarding. Alice assigns them as Action records
in the new user's weekly project. Soft gate -- she prompts, doesn't block.

Full checklist and coaching details: `readmes/onboarding.md` (Flight Simulators section).

**The trail must be packed before it's open.** A feature not trained is a
feature not used. Flight simulators are how we pack the trail.

---

## Backend Services

- `apps/products/services/inventory_flight_sim.py` -- `get_flight_scenario()` (scripted) + `get_item_flight_state(item_id)` (live) + `reset_flight_simulator()`
- `apps/transactions/services/sales_pipeline.py` -- `get_sales_pipeline()`
- `apps/accounts/services/cash_conversion.py` -- `get_cash_conversion()`
- `apps/products/services/inventory_velocity.py` -- `get_inventory_velocity()`
- `apps/accounts/services/accounting_dashboard.py` -- `get_journal_exceptions()`
- `apps/accounts/services/journalize.py` -- `force_to_balance()`, `batch_journalize()`

**Models:**
- `apps/accounts/models/journal_batch.py` -- `JournalBatch` (posting run header)
- `apps/core/models/action.py` -- `Action.impact` (JSONField), `Action.action_type`

**React dashboards** (all in `src/pages/admin/`):

| File | Route |
|------|-------|
| `InventoryFlightSim.tsx` | `/flight-sim-inventory` |
| `SalesPipelineDashboard.tsx` | `/sales-pipeline` |
| `CashConversionDashboard.tsx` | `/cash-conversion` |
| `InventoryVelocityDashboard.tsx` | `/inventory-velocity` |
| `JournalAuditDashboard.tsx` | `/journal-audit` |

**GL accounts used in training:**

| Account | What it represents |
|---------|-------------------|
| ASSET-AR-000 | What customers owe us |
| ASSET-CASH-000 | Money in the bank |
| ASSET-INVENTORY-000 | Goods on the shelf |
| REV-SALES-000 | What we earned |
| COGS-PRODUCTS-000 | Cost of what we sold |
| LIAB-ACCTSPAY-000 | What we owe vendors |
| LIAB-SALESTAX-000 | Tax owed to government |
| LIAB-COMMPAY-000 | Commission owed to reps |
| EXP-COMMISSIONS-000 | Commission expense |
| EXP-DISCOUNTS-000 | Discount expense (margin erosion) |
| EXP-BADDEBT-000 | Write-off expense (uncollectable) |

---

## Files Changed (Line Pipeline Build)

### Server (webClerk3)

| File | What changed |
|------|-------------|
| `apps/core/views/save_view.py` | FK descriptor skip in field copy loop; item_fk_id derivation from item.item_id; `_adjust_source_line` method; purchase exemption from source adjustment |
| `apps/transactions/services/line_item_service.py` | IN/RC pending only touch own bucket (removed on_so/on_po cross-adjustments) |
| `apps/transactions/services/conversion.py` | `_do_convert` returns line array (no saved lines/pending); single-bucket adjustments_map; sell/buy header field split; vendor optional for purchase |
| `apps/transactions/services/proposal_to_order.py` | Returns line array, no line saving or pending |
| `apps/transactions/services/order_to_invoice.py` | Same pattern; `data=` -> `changes=` fix |
| `apps/products/services/inventory_flight_sim.py` | `reset_flight_simulator` function |
| `apps/core/views/manage_view.py` | `reset_flight_simulator` action |

### React (React2025)

| File | What changed |
|------|-------------|
| `src/apps/transactions/components/detail/LineCardRenderer.tsx` | Removed `item_fk` and `item_fk_id` from line construction |
| `src/pages/admin/FlightSimConsole.tsx` | `convertedLines` state; `initialLines` prop; reset on simulation start |
| `src/apps/transactions/components/TransactionDetail.tsx` | `initialLines` prop -- injects converted lines for review |
| `src/api/wcapi.ts` | Preserved `refs` and `commission` on lines (removed from strip list) |

---

## Open Items

- Order->Invoice retest with single-bucket fix
- Purchase and receipt flows need testing
- Buy-side conversions should pull fresh cost/price from item record
- Customer clearing bug on +Item not yet investigated
- Orphaned pending cleanup for abandoned transactions
