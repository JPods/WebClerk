# Flight Simulator Training Series — Plan

## What Flight Simulators Are

Interactive Console windows where users step through real business processes
and watch data change at every stage. Not documentation — doing. The user
performs each action and sees the transposed grid grow column by column.

**Bill's term:** Flight simulators. Like learning to fly — you do it in the
simulator before you do it for real.

## Console Window Architecture

### Layout: Two Panels

**Left panel — Step Navigator:**
- Numbered step cards (not db.list — these are scripted, not model records)
- Each card shows: step number, action name, what to do, "Run Step" button
- Current step highlighted, completed steps checked
- Replaces SelectModel — no model selection needed

**Right panel — Transposed Grid:**
- Rows = field names, grouped by category (Inventory, GL, Pending, Cash, etc.)
- Columns = steps (grow left-to-right as user advances)
- Changed values highlighted with delta badge (+9, -4)
- Empty cells = no change at that step
- Horizontal scroll as steps accumulate
- Row groups collapse/expand — user focuses on what they care about

### Why Transposed

Standard tables (rows=records, columns=fields) fail here because:
- Each step affects different fields — columns would be non-uniform
- The learning is in watching ONE field change across MANY steps
- Grouped rows let different simulators show different categories

### Architecture Path: Custom React Component

Not a form layout (too rigid for interactive stepping) or detail layout (not model records).
Custom component with backend service returning scenario definition + computed
state per step.

### Backend Pattern

Each simulator has a service in `apps/*/services/`:
```python
def get_scenario():
    """Return step definitions + expected values at each step."""
    return {
        "name": "...",
        "description": "...",
        "config": { ... },  # rates, accounts, starting values
        "steps": [
            {
                "step": 1,
                "action": "...",
                "description": "...",
                "state": {
                    "inventory": { "on_hand": 100, ... },
                    "gl": { ... },
                    "pending": { ... },
                }
            },
            ...
        ],
        "row_groups": [
            { "name": "Inventory", "rows": ["on_hand", "on_so", "on_po", "available"] },
            { "name": "GL", "rows": ["AR", "Revenue", "COGS", ...] },
        ]
    }
```

### Two Modes (All Simulators)

1. **Scripted** — Canned scenario with known good values. User steps through
   and watches. Used for training and onboarding.
2. **Live** — User selects a real record. Grid shows actual current state.
   Used for debugging and auditing real data.

---

## Flight Simulator Series

### FS-01: Transaction Lifecycle (exists — upgrade to Console)
**Route:** `/flight-sim-inventory`
**Teaches:** How inventory quantities, pending records, and GL entries change
at every stage from proposal through payment settlement.

Current: 9-step version in `inventory_flight_sim.py`.
Target: 12-step version (from flowchart) with reverse flow, aging, and orphan cleanup.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — starting inventory | Inventory |
| 2 | Proposal (15 units) | Inventory |
| 3 | Partial convert to Order (11) | Inventory, Pending |
| 4 | Post to Purchase (11) | Inventory, Pending |
| 5 | Partial receive (9) | Inventory, GL, Pending |
| 6 | Partial invoice (7) | Inventory, GL, Pending |
| 7 | Statement (15 days) | Aging |
| 8 | Late notice (30 days) | Aging, Actions |
| 9 | Late fee (6 weeks) | GL, AR |
| 10 | Payment (with discount + write-off) | GL, Cash |
| 11 | Process GLs | GL (all accounts) |
| 12 | Return 1 unit | Inventory, GL, Credit |
| 13 | Scrap returned item | Inventory, GL |
| 14 | Refund customer | GL, Cash |
| 15 | Clean up orphans (cancel proposal remainder, close SO/PO) | Inventory, Pending |

**Margin waterfall at end:** Revenue → COGS → Gross → Commission → Discount →
Bad Debt → Late Fee → Net. This is why Alice tracks erosion.

---

### FS-02: Bill of Materials (BOM)
**Route:** `/flight-sim-bom`
**Teaches:** How a BOM explodes into components, how component availability
affects buildable quantity, and how costs roll up.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — finished good + 4 components | BOM tree |
| 2 | Check component availability | Inventory per component |
| 3 | Calculate buildable quantity (min constraint) | Buildable, Constraining component |
| 4 | Create work order (10 assemblies) | Inventory (components reserved) |
| 5 | Issue components to floor | Inventory (on_hand down, on_wo up) |
| 6 | Complete 8 of 10 (partial) | Inventory (FG up, components consumed) |
| 7 | Scrap 1 assembly (yield loss) | Inventory, GL (scrap expense) |
| 8 | Complete remaining 1 | Inventory |
| 9 | Cost rollup — actual vs standard | GL (variance accounts) |
| 10 | Close work order | Pending, GL |

**Key insight:** The constraining component determines buildable quantity.
Users learn why "available to build" differs from "components on hand."

---

### FS-03: GL Audit Trail
**Route:** `/flight-sim-gl-audit`
**Teaches:** How every business event creates balanced journal entries,
how to trace any GL balance back to its source transactions.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — chart of accounts, opening balances | GL balances |
| 2 | Sale (invoice) — AR / Revenue / Tax / COGS / Inv | GL, Source docs |
| 3 | Receipt of goods — Inventory / AP | GL, Source docs |
| 4 | Payment received — Cash / AR | GL, Source docs |
| 5 | Payment sent — AP / Cash | GL, Source docs |
| 6 | Adjusting entry — manual journal | GL, Audit trail |
| 7 | Period close — check trial balance | GL (must balance) |
| 8 | ForceToBalance — user statement required | GL, Exceptions |
| 9 | Post journals — create JournalBatch | GL, Batch record |
| 10 | Drill from GL balance → source transactions | Audit trail |

**Key insight:** Every dollar in every account has a source document.
The audit trail is not a report — it's the structure of the data.

---

### FS-04: Cash Flow Tracking
**Route:** `/flight-sim-cash`
**Teaches:** How cash moves through the system — from customer payment
through bank reconciliation and cash position reporting.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — bank account, opening cash balance | Cash, GL |
| 2 | Invoice customer ($500) | AR, no cash yet |
| 3 | Customer pays ($485 — took 3% discount) | Cash, AR, Discount |
| 4 | Receive vendor bill ($300) | AP, no cash yet |
| 5 | Pay vendor ($294 — earned 2% discount) | Cash, AP, Discount |
| 6 | Payroll run ($1000) | Cash, Expense |
| 7 | Bank reconciliation — match 3 items | Reconciled vs unreconciled |
| 8 | Outstanding check ages past 30 days | Stale check alert |
| 9 | Cash position report | Cash in, cash out, net |

**Key insight:** Revenue ≠ cash. Profit ≠ cash. Cash position is the
only number that tells you if you can make payroll Friday.

---

### FS-05: Currency Variations
**Route:** `/flight-sim-currency`
**Teaches:** How multi-currency transactions create exchange rate gains/losses,
how revaluation works, and why FX residuals need absorption rules.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — USD base, EUR customer, JPY vendor | Rates, GL |
| 2 | Invoice in EUR (€1000 @ 1.08 = $1,080) | AR (USD + EUR), GL |
| 3 | Rate changes to 1.10 | Unrealized gain shown |
| 4 | Customer pays €1000 (@ 1.10 = $1,100) | Cash, AR, Realized FX gain $20 |
| 5 | Purchase in JPY (¥50,000 @ 0.0067 = $335) | AP (USD + JPY), GL |
| 6 | Rate changes to 0.0070 | Unrealized loss shown |
| 7 | Pay vendor ¥50,000 (@ 0.0070 = $350) | Cash, AP, Realized FX loss $15 |
| 8 | Period-end revaluation of open items | Unrealized FX GL entries |
| 9 | FX residual < $2 — auto-absorbed | Absorption rule, GL |

**Key insight:** The invoice amount and the payment amount are in different
dollars. The difference is not an error — it's the cost of doing business
internationally. Alice's auto-absorption handles the dust.

---

### FS-06: Commission Tracking
**Route:** `/flight-sim-commissions`
**Teaches:** How commissions accrue at sale, adjust at payment, and reconcile
at period end. How split commissions and override commissions work.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — 2 reps, split rule, override rule | Rep setup, rates |
| 2 | Sale ($1000, 5% commission) | Commission accrual ($50) |
| 3 | Split: Rep A 60% / Rep B 40% | Per-rep accrual ($30/$20) |
| 4 | Override: Manager gets 1% on Rep A's sales | Override accrual ($10) |
| 5 | Customer takes 3% discount | Commission adjusts on net, not gross |
| 6 | Partial return ($200) | Commission reversal ($10) |
| 7 | Commission statement — period end | Per-rep totals, adjustments |
| 8 | Commission payment run | Cash, Commission Payable, GL |

**Key insight:** Commissions are on net revenue after discounts and returns,
not on invoice face value. Paying on gross creates margin erosion that
Alice tracks but most systems ignore.

---

### FS-07: Inventory Costing Methods
**Route:** `/flight-sim-costing`
**Teaches:** How FIFO, LIFO, and weighted average produce different COGS
and inventory valuations from the same transactions.

| Step | Action | FIFO | LIFO | Weighted Avg |
|------|--------|------|------|-------------|
| 1 | Setup — 10 units @ $5 | $50 | $50 | $50 |
| 2 | Buy 10 @ $7 | $50+$70 | $50+$70 | $120 (20@$6) |
| 3 | Sell 5 | COGS $25 (oldest) | COGS $35 (newest) | COGS $30 |
| 4 | Buy 5 @ $8 | layers shown | layers shown | new avg |
| 5 | Sell 12 | COGS from layers | COGS from layers | COGS at avg |
| 6 | Period-end valuation | remaining layers | remaining layers | remaining @ avg |

**Key insight:** Same transactions, three different profit numbers.
The method choice is a business decision, not an accounting detail.

---

### FS-08: Purchase-to-Pay Cycle
**Route:** `/flight-sim-p2p`
**Teaches:** The full procurement cycle from requisition through payment,
including three-way matching and receiving discrepancies.

| Step | Action | Categories Shown |
|------|--------|-----------------|
| 1 | Setup — vendor, item, pricing agreement | Vendor, Pricing |
| 2 | Requisition (internal request) | Requisition, no inventory/GL |
| 3 | Convert to Purchase Order | PO, on_po increases |
| 4 | Receive goods (8 of 10 — short ship) | Inventory, Pending, Receiving |
| 5 | Receive remaining 2 | Inventory, PO closed |
| 6 | Vendor invoice arrives | AP, three-way match check |
| 7 | Price discrepancy ($0.50/unit) | Exception, variance GL |
| 8 | Approve variance | AP posted |
| 9 | Pay vendor (2% early pay discount) | Cash, AP, Discount |

**Key insight:** Three-way match (PO qty × price vs receipt qty vs invoice amount)
is the control that prevents paying for what you didn't order or didn't receive.

---

## Implementation Priority

| Priority | Simulator | Why |
|----------|-----------|-----|
| 1 | FS-01 Transaction Lifecycle | Already exists — upgrade to Console format |
| 2 | FS-03 GL Audit Trail | Users don't understand balanced entries |
| 3 | FS-04 Cash Flow | Cash vs profit confusion is universal |
| 4 | FS-02 BOM | Critical for manufacturing users |
| 5 | FS-08 Purchase-to-Pay | Common workflow, teaches matching |
| 6 | FS-06 Commissions | Sales orgs need this immediately |
| 7 | FS-05 Currency | International users only |
| 8 | FS-07 Costing Methods | Advanced — accountants and controllers |

## Onboarding Integration

Alice assigns flight simulators as Action records in the new user's weekly project.
Sequence matches the priority order above — users complete FS-01 first, then Alice
suggests the next based on their role:

- **Sales:** FS-01 → FS-06 → FS-04
- **Purchasing:** FS-01 → FS-08 → FS-02
- **Accounting:** FS-01 → FS-03 → FS-04 → FS-05
- **Management:** FS-01 → FS-04 → FS-03

## Shared React Component

All simulators share one `FlightSimConsole.tsx` component:
- Left panel: step navigator (driven by scenario JSON)
- Right panel: transposed grid (driven by row_groups + step state)
- The scenario service provides all the data — the component is generic

Each simulator is a **route** that passes its scenario ID to the shared component.
No per-simulator React code unless the simulator needs custom interaction
(e.g., FS-07 costing methods showing three parallel columns per step).
