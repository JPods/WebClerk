# Onboarding Checklist — New User Exercises

> **Last updated**: 2026-08-20
> **Owner**: Alice
> **Flight Simulator**: `/flight-simulator`
> **Principle**: Feature not done until trail is packed (ski company doctrine)

---

## How to Use This Checklist

Each exercise is a real action in a live (or training) WC3 instance. The user
does the work — the flight simulator watches and shows what changed. No slides,
no videos, no passive watching. You learn commerce by doing commerce.

**Shift-click** any flight sim card to resume where you left off.
**Click** to start fresh (resets training data).

---

## Phase 1 — Foundation

_Must complete before any transaction work. These create the data that all
later exercises depend on._

| # | Exercise | What you learn | How | Time |
|---|----------|---------------|-----|------|
| 1.1 | **Your First Contact** | Contacts are people. Every user, customer rep, vendor rep, and employee is a Contact. The Contact IS the login. | Flight Sim: "Your First Customer" step 1 | 3 min |
| 1.2 | **Your First Customer** | Orgs represent companies. A Customer org has financial data (credit limit, terms, aging). Contacts belong to orgs. | Flight Sim: "Your First Customer" steps 2-3 | 5 min |
| 1.3 | **Your First Item** | Items are what you sell and buy. Price, cost, GL accounts, quantity buckets (on_hand, on_so, on_po, available). | Flight Sim: "Your First Item" | 5 min |
| 1.4 | **Navigate the DataBrowser** | Two-pane layout. Click = select. Shift-click = alternate action. Column widths are yours to set. | Open `/databrowser`, explore Contact, Item, Customer | 5 min |

**Checkpoint**: You have a contact, a customer org, and an item with opening
inventory. You can find all three in the DataBrowser.

---

## Phase 2 — Sell Side (the main loop)

_The core transaction cycle. Every commerce business runs this loop._

| # | Exercise | What you learn | How | Time |
|---|----------|---------------|-----|------|
| 2.1 | **Your First Sale** | Proposal → Order. Proposals are quotes (no commitment). Orders are commitments (on_so increases). The conversion copies lines. | Flight Sim: "Your First Sale" | 5 min |
| 2.2 | **Inventory Tracking** | Full lifecycle: Proposal → Order → Invoice → Purchase → Receive. Watch on_hand, on_so, on_po, available change at each step. Pending records are the mechanism. | Flight Sim: "Inventory Quantity Tracking" | 15 min |
| 2.3 | **Payment Lifecycle** | Order → partial Invoice → accept Payment → apply part to invoice → journal. The four payment fields: amount, available, tendered, change. | Flight Sim: "Payment Lifecycle" | 10 min |
| 2.4 | **Cash Flow** | Invoice → Payment → Discount → Write-off. How AR decreases. How discounts and write-offs are separate Payment records, each with their own GL. | Flight Sim: "Cash Flow Tracking" | 10 min |

**Checkpoint**: You can create a sale from quote to cash. You understand that
proposals don't commit inventory, orders do, invoices move it, and payments
settle the financial side.

---

## Phase 3 — Buy Side

_Purchasing, receiving, and vendor payment._

| # | Exercise | What you learn | How | Time |
|---|----------|---------------|-----|------|
| 3.1 | **Purchase-to-Pay** | Requisition → PO → Receive → Three-way match → Pay vendor. on_po tracks what's expected. Receipt is the financial event (Inventory/AP). | Flight Sim: "Purchase-to-Pay" | 15 min |
| 3.2 | **Bill of Materials** | BOM explosion, component availability, buildable quantity, cost rollup. Work orders consume components and produce finished goods. | Flight Sim: "Bill of Materials" | 10 min |

**Checkpoint**: You can buy inventory, receive it, and pay the vendor. You
understand that POs don't create financial events — receipts do.

---

## Phase 4 — Accounting

_GL, commissions, costing. These build on Phase 2 and 3._

| # | Exercise | What you learn | How | Time |
|---|----------|---------------|-----|------|
| 4.1 | **GL Audit Trail** | Every business event creates balanced journal entries. DR always = CR. Trace any balance to its source document. | Flight Sim: "GL Audit Trail" | 10 min |
| 4.2 | **Commissions** | Accrual at sale, split commissions, adjustments at payment, period-end reconciliation. Commission is an expense at sale time, not payment time. | Flight Sim: "Commissions" | 10 min |
| 4.3 | **Costing Methods** | Same transactions, three different profit numbers. FIFO vs LIFO vs weighted average. Why the choice matters for taxes and reporting. | Flight Sim: "Costing Methods" | 10 min |
| 4.4 | **Currency Variations** | Multi-currency transactions, exchange rate gains/losses, period-end revaluation. | Flight Sim: "Currency Variations" | 10 min |

**Checkpoint**: You can read a GL journal and trace entries back to source.
You understand that revenue recognition and cash collection are different events.

---

## Phase 5 — Operations

_Projects, reporting, and inter-system communication._

| # | Exercise | What you learn | How | Time |
|---|----------|---------------|-----|------|
| 5.1 | **Create a Project** | Projects organize work. Actions track tasks with who/what/why/when/next. assigned_to is a roster (vendors, customers, employees). | DataBrowser: create Project, add 3 Actions | 5 min |
| 5.2 | **Print an Invoice** | SVG template workflow. JSON drives the layout — not a print design tool. Print CSS is minimal. | Open any invoice → Print | 3 min |
| 5.3 | **Create a Sync Connection** | How two WC3 instances exchange data. Bundles carry records. Field maps handle schema differences. Conflict resolution: newest wins. | DataBrowser: create Connection | 10 min |
| 5.4 | **Review Aging Report** | Customer aging buckets (current, 1-30, 31-60, 60+). available_payments. total_exposure = balance_due + open_orders - available_payments. | DataBrowser: open Customer → financial tab | 5 min |

**Checkpoint**: You can organize work, produce output, connect to other
systems, and read the financial health of a customer.

---

## Completion Criteria

A user is onboarded when they can:

- [ ] Create a contact and customer org from scratch
- [ ] Create an item with price, cost, and opening inventory
- [ ] Run a full sell cycle: Proposal → Order → Invoice → Payment → Journal
- [ ] Run a full buy cycle: PO → Receive → Pay vendor
- [ ] Read a GL journal and trace an entry to its source document
- [ ] Find any record in the DataBrowser
- [ ] Explain what `available` means on a Payment record
- [ ] Explain why a Proposal doesn't affect inventory but an Order does

---

## For Alice

Alice watches for bramble bushes — places where users get stuck, confused, or
make errors. Each flight sim step that takes more than 2× expected time, or
produces an error, is a signal. Alice logs these as observations and
recommends improvements to the onboarding sequence.

Track completion per user via `metadata.onboarding` on their Contact record:
```json
{
  "onboarding": {
    "phase_1_complete": "2026-08-20T14:30:00Z",
    "phase_2_complete": null,
    "exercises_completed": ["1.1", "1.2", "1.3", "1.4", "2.1"],
    "time_spent_minutes": 23,
    "bramble_bushes": ["1.3 — confused by GL account codes"]
  }
}
```

---

## Total Estimated Time

| Phase | Minutes |
|-------|---------|
| 1 — Foundation | 18 |
| 2 — Sell Side | 40 |
| 3 — Buy Side | 25 |
| 4 — Accounting | 40 |
| 5 — Operations | 23 |
| **Total** | **~2.5 hours** |

Not all at once. Phase 1 + 2.1 in the first session (30 min). The rest over
the first week. Alice paces based on the user's role — a bookkeeper starts
Phase 4 earlier; a warehouse worker may skip it entirely.
