# Flight Simulator — Next Steps (2026-08-20)

## What Works Now

The **Inventory Quantity Tracking** simulation works end-to-end:
- Reset on card click (reset_flight_simulator manage action)
- Auto-start from URL (/flight-sim/inventory)
- Proposal: add item → save → on_p pending fires
- Proposal → Order: conversion creates header + line array, user reviews, saves → on_so pending fires → proposal adjusts → on_p release fires
- Order → Invoice: same pattern → on_hand pending fires → order adjusts → on_so release fires
- Order → Purchase: buy-side, no customer transfer, no on_so impact → on_po pending fires
- Breadcrumb navigation stays in simulator panel
- Left panel shows event timeline with three-row pattern

## Architecture Rules (non-negotiable)

1. **Front end sends data, backend manages data and relationships.** React sends plain IDs in JSON envelopes. Server derives FK columns. See readmes/80-line-save-boundary.md.

2. **Each transaction model owns one inventory bucket.** Pending fires on line save, only for own bucket. Source bucket released by _adjust_source_line. No cross-bucket. See scars.md.

3. **Users edit arrays, not database records.** Conversion creates header only, returns line array. User reviews, saves. DB locks only during save loop.

## Key Files

| File | Role |
|------|------|
| `webClerk3/apps/products/services/inventory_flight_sim.py` | Server-side: reset, get_flight_transactions, get_item_by_ida, scenario steps |
| `webClerk3/apps/transactions/services/conversion.py` | _do_convert: creates header, builds line array, returns to React |
| `webClerk3/apps/core/views/save_view.py` | Line creation, FK skip, item_fk_id derivation, _adjust_source_line |
| `webClerk3/apps/transactions/services/line_item_service.py` | _create_pending_for_new_line, single-bucket pending data |
| `webClerk3/apps/core/models/pending.py` | Pending.save() → try_apply() → _apply_inventory() |
| `React2025/src/pages/admin/FlightSimConsole.tsx` | Main component: reset, convertedLines, onNavigate, auto-start |
| `React2025/src/apps/transactions/components/TransactionDetail.tsx` | initialLines prop, onNavigate passthrough |
| `React2025/src/apps/transactions/components/TransactionItemSearch.tsx` | Tab/Enter search, no spinners |
| `React2025/src/apps/transactions/components/detail/TransactionFlowIndicator.tsx` | Breadcrumb: onNavigate for simulator mode |
| `React2025/src/api/wcapi.ts` | saveTransactionWithLines: preserves refs and commission on lines |

## Remaining Simulations to Build

### Already Defined (SIMULATIONS array in FlightSimConsole.tsx)

Each simulation needs:
1. A reset function (or reuse reset_flight_simulator with the item ida)
2. Server-side scenario steps (like get_flight_scenario in inventory_flight_sim.py)
3. Left panel display appropriate to the simulation type

### Cash Flow Tracking (id: "cash")
```
Invoice → Payment → Discount → Write-off
Watch: cash, AR, bank reconciliation
```
- Starts with an invoice (not a proposal)
- GL entries are the focus, not inventory buckets
- Left panel needs GL account columns instead of quantity columns
- Payment model creates ledger entries
- Partial payment, discount, write-off are three separate save events
- Each fires its own GL pending

### GL Audit Trail (id: "gl-audit")
```
Every business event creates balanced journal entries
Trace any balance to its source
```
- Similar to cash flow but emphasizes the audit chain
- Show debit/credit columns on left panel
- Every pending that creates GL should show the journal entry
- Drill from any GL balance to the originating transaction

### Bill of Materials (id: "bom")
```
BOM explosion, component availability, buildable quantity, cost rollup
```
- Needs BOM/recipe structure on the item
- Work order creates component lines
- Each component line fires its own on_wo pending
- Receipt of finished goods adds on_hand
- Cost rollup: sum of component costs = finished good cost

### Purchase-to-Pay (id: "p2p")
```
Requisition → PO → Receive → Three-way match → Pay vendor
```
- Starts with requisition (if model exists) or purchase
- Receive goods: on_po release, on_hand increase
- Three-way match: PO qty vs receipt qty vs vendor invoice qty
- Vendor payment: AP cleared, cash outflow

### Commission Tracking (id: "commissions")
```
Accrual at sale, split commissions, adjustments at payment, period-end
```
- Commission accrues on invoice journalize
- Split commissions: multiple reps on one line
- Adjustment when payment received (early pay discount affects commission)
- Period-end reconciliation

### Currency Variations (id: "currency")
```
Multi-currency, exchange rate gains/losses, revaluation
```
- Transaction in foreign currency
- Exchange rate at time of sale vs time of payment
- Realized gain/loss on payment
- Period-end unrealized gain/loss revaluation

### Costing Methods (id: "costing")
```
Same transactions, three different profit numbers
FIFO vs LIFO vs weighted average
```
- Same sales/purchase data
- Show how COGS changes with each method
- Inventory layers visible

## How to Build a New Simulation

1. **Add scenario steps** to `inventory_flight_sim.py` (or create a new file per simulation)
2. **Add a reset function** specific to the simulation if it needs different item/data setup
3. **Add left panel columns** — FlightSimConsole currently hardcodes QUANTITY_FIELDS. Each simulation type may need different columns (GL accounts, commission amounts, currency rates)
4. **Add route** in Router.tsx: `<Route path="flight-sim/{id}" element={<S><FlightSimConsole /></S>} />`
5. **Test the linear flow** — every save fires exactly one pending for its own bucket

## Known Issues

- JSON editor in databrowser doesn't save (edits don't propagate to save payload)
- Buy-side conversions (order→purchase) should pull fresh cost/price from item record, not copy from sell-side source
- Ship_to card needs a button to switch to company receiving address
- Orphaned pending cleanup for abandoned training transactions
- Customer clearing bug on +Item (may be resolved by the customer_id_id fix — needs retest)
