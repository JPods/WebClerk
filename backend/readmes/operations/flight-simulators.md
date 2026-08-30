# Flight Simulators — Interactive Training for WebClerk

## What They Are

Flight simulators are step-by-step training windows where users perform real
actions and watch data change at each stage. They teach how the system works
by doing, not reading.

The name comes from aviation: you don't learn to fly by reading the manual.
You learn by sitting in the simulator, making inputs, and watching the
instruments respond. Same principle applied to commerce.

## Available Flight Simulators

### Flight Simulator: Inventory (`/flight-sim-inventory`)

Teaches how inventory quantities, pending records, and GL entries change as
transactions flow through the system. Nine steps:

| Step | Action | Qty Changes | GL Impact |
|------|--------|-------------|-----------|
| 1 | Starting inventory (on_hand=100) | — | — |
| 2 | Proposal for 15 units | on_p: 0→15 | None (quote only) |
| 3 | Convert 9 to Order | on_p: 15→6, on_so: 0→9 | None (commitment only) |
| 4 | Invoice 4 units | on_hand: 100→96, on_so: 9→5 | AR $42 / Revenue $40 / Tax $2 / COGS $24 / Inventory $24 / Commission $2 |
| 5 | Purchase 14 units | on_po: 0→14 | None (until received) |
| 6 | Receive 11 units | on_hand: 96→107, on_po: 14→3 | Inventory $66 / AP $66 |
| 7 | Partial payment $30 | — | Cash $30 / AR $30 |
| 8 | Discount $10 | — | Discount Exp $10 / AR $10 |
| 9 | Write-off $2 | — | Bad Debt $2 / AR $2 |

**What users learn:**
- Which transactions move inventory and which don't
- Why pending records exist (they track the movement between stages)
- When GL entries are created vs. when they aren't
- How a $42 invoice settles: $30 cash + $10 discount + $2 write-off
- Margin erosion: 40% gross → 5% net after commission, discount, and bad debt
- Why Alice tracks erosion (because this happens constantly)

**Config:** 5% tax, 5% commission. Easy mental math so the learner focuses
on concepts, not arithmetic.

### Sales Pipeline (`/sales-pipeline`)

Funnel dashboard: Actions → Proposals → Orders → Revenue.

Uses the impact assessment loop (see below) to connect selling actions
to outcomes. Users choose an `action_type` (call, email, visit, meeting,
demo, marketing, referral, social, event, follow_up, other) and rate
predicted impact. Alice auto-fills actual impact later.

### Cash Conversion (`/cash-conversion`)

Teaches where money stalls in the pipeline:

Order → Invoice → Payment → GL → Period Close

Each stage shows average days and stalled records. Users learn that a
healthy business has short, predictable stage durations. The journal
audit dashboard (`/journal-audit`) opens from here for GL exceptions.

### Journal Audit (`/journal-audit`)

Three-panel GL posting review:

| Panel | What it shows | User action |
|-------|--------------|-------------|
| Queue | Transactions ready to post | Click "Post Journals" to batch-post |
| Exceptions | Out-of-balance — can't post | Fix source or ForceToBalance |
| Skipped | Hold, consigned, zero-amount | Informational — change status to unblock |

**ForceToBalance:** When a journal is out of balance (e.g., FX rounding on a
low-cost item), the user clicks "Force to Balance," writes a statement explaining
why (minimum 10 characters), and the system posts an adjusting line. The statement
is stored in three places: the GL line's note, the GL line's metadata, and the
source transaction's `metadata.gl_accounts.force_balance[]`.

**FX auto-absorption:** Foreign currency residuals under $2 are automatically
absorbed into the FX rounding account (WC2 GL2 rule). No user action needed.

**JournalBatch model:** Every posting run creates a `JournalBatch` header (like
Order → OrderLine). Stores totals, exception count, absorption count, who ran it,
and when. The batch is the flight recorder for every GL posting event.

### Inventory Velocity (`/inventory-velocity`)

Teaches where capital is working vs. parked:

PO Exposure → Receipt → On Hand (ABC) → Sales → Reorder

Users learn the difference between stars (high margin, high velocity)
and dead capital (sitting on the shelf, costing money).

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

1. **User creates action** — sets `predicted` (2 seconds, gut feel)
2. **Time passes** — customer buys or doesn't
3. **Alice scans** — periodic task finds transactions for that customer,
   auto-fills `actual` and `refs.transactions`
4. **User reviews** — confirms (0 seconds) or corrects (2 seconds)
5. **Alice learns** — adjusts future guesses based on corrections
6. **Admin time drops** — Alice's auto-fill accuracy improves over time

**Not precision, but retrospection.** The numbers are waffly on purpose.
The value is in coming back, seeing the gap, and asking why. The score
is just the hook that forces the retrospection.

**Calibration metrics:**
- `avg_gap`: predicted minus actual, averaged across all retrospected actions.
  Positive = over-optimistic. Negative = under-estimating. Zero = perfect.
- `correction_rate`: how often users change Alice's guess. 40% = still
  learning. 10% = calibrated. 2% = users trust the auto-fill.

## Onboarding Integration

Flight simulators are part of onboarding. Alice assigns them as Action records
in the new user's weekly project. Soft gate — she prompts, doesn't block.

Full checklist and coaching details: `readmes/onboarding.md` (Flight Simulators section).

**The trail must be packed before it's open.** A feature not trained is a
feature not used. Flight simulators are how we pack the trail.

## Architecture

**Backend services:**
- `apps/products/services/inventory_flight_sim.py` — `get_flight_scenario()` (scripted) + `get_item_flight_state(item_id)` (live)
- `apps/transactions/services/sales_pipeline.py` — `get_sales_pipeline()`
- `apps/accounts/services/cash_conversion.py` — `get_cash_conversion()`
- `apps/products/services/inventory_velocity.py` — `get_inventory_velocity()`
- `apps/accounts/services/accounting_dashboard.py` — `get_journal_exceptions()`
- `apps/accounts/services/journalize.py` — `force_to_balance()`, `batch_journalize()`

**Models:**
- `apps/accounts/models/journal_batch.py` — `JournalBatch` (posting run header)
- `apps/core/models/action.py` — `Action.impact` (JSONField), `Action.action_type`

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
