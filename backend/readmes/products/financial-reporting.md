# Financial Reporting — Budgeting, Not Accounting

## The Divide

Accounting answers to regulators. It must comply with GAAP, IFRS, tax codes,
audit standards — rules that change by jurisdiction, by year, by entity type.
That is a specialized discipline with its own tools, its own professionals,
and its own obligations.

WebClerk answers to the business owner. It tracks what the business is
actually doing — selling, buying, making, spending — and projects what's
coming. That is operations.

WebClerk does not do accounting. WebClerk does not comply with regulations.
WebClerk produces the data that accountants need to comply with regulations,
and consumes the budgets that accountants produce. Two sovereign domains,
clean interface, neither one trying to be the other.

## The Budget as Baton

Accountants already produce forward-looking budgets — a dollar amount by
GL account code by period. They do it every year for every client. It is
informed by history, tax planning, and regulatory requirements.

That budget is a baton.

The accountant hands it to WebClerk. WebClerk doesn't question the
accountant's numbers — they reflect obligations and assumptions that
operations has no business second-guessing. What WebClerk does is combine
those numbers with live operational data that the accountant cannot see.

The accountant's budget says "we expect $50K in revenue in October."
WebClerk knows there are $32K in open proposals at 60% probability and
$18K in committed orders with net-30 terms. The accountant's number is
a guess informed by history. WebClerk's number is informed by what is
actually in the pipeline right now.

At the end of the period, WebClerk produces a Budget vs Actual report —
what the budget said would happen vs what the GL journals say did happen.
That report is a baton passed back. The accountant uses it to produce a
better budget for the next period. The loop closes.

This process elevates the budget from a point of interest into an
operationally accountable baton passed between accounting and operations.
The budget is no longer a static document filed and forgotten. It is a
living instrument that gets tested against reality every period and
improves because of it.

## What Crosses the Boundary

| Direction | What | Format | Purpose |
|-----------|------|--------|---------|
| WC3 → Accountant | GL journals | GL export (QuickBooks, Xero, Sage, CSV) | What happened — raw material for compliant financial statements |
| Accountant → WC3 | Budget | CSV import → Budget model | Dollar by account by period — the accountant's forward projection |
| WC3 → Accountant | Budget vs Actual | Report (JSON/CSV) | How the budget performed — input to the next budget cycle |

## What WebClerk Adds to the Budget

The accountant's budget is the baseline. WebClerk's forecast is the
baseline plus operational intelligence:

| What the accountant can't see | Where WebClerk gets it |
|------|------|
| Which proposals are likely to close | Proposal model × probability field |
| When orders will actually collect | Order model + payment terms (days) |
| What purchases are committed and when they pay | Purchase lines + vendor payment terms |
| Whether the forecast was right last month | Budget vs Actual comparison (Alice) |

## What WebClerk Produces

WebClerk produces *trial* financial statements — operational, not regulatory:

| Report | What it shows | Action |
|--------|--------------|--------|
| **Trial Balance** | All GL accounts with period debit/credit totals | Verify the books balance |
| **P&L (Income Statement)** | Revenue minus expenses by category | See if the business is profitable |
| **Balance Sheet** | Assets = Liabilities + Equity at a point in time | See what the business owns and owes |
| **AP Aging** | Vendor payables by aging bucket | Manage cash outflow |
| **Cash Forecast** | Projected inflows and outflows by month | Plan ahead |
| **Budget vs Actual** | Budget entries vs GL journals per account per period | Grade the forecast, improve the next one |

These reports are good enough to run the business. They are not good enough
to file taxes. That is on purpose. The accountant produces compliant
statements from the GL export. WebClerk produces operational statements
from the same data plus the budget plus live pipeline. Different audiences,
different requirements, clean boundary.

## The Budget Model

One record per GL account per period. No complexity, no formulas,
no what-if scenarios. Users do all of that in their spreadsheets.
When they hand it to WebClerk, it is a simple number.

```
period          account         debit       credit      description
2026-10         6100-SALARY     12500.00    0.00        Salaried staff
2026-10         6300-RENT       4500.00     0.00        Office lease
2026-10         6500-DEPREC     833.00      0.00        Equipment depreciation
2026-10         1500-EQUIP      0.00        833.00      Accumulated depreciation
```

- **period** — user-defined label (2026-10, w41_2026, q3_2026)
- **dt_period_start / dt_period_end** — epoch ms boundaries for range queries
- **account** — GL account ida, same codes used in GlJournal
- **debit / credit** — proper double-entry, same as GlJournal
- **dt_journaled** — locks past periods (0 = editable, non-zero = locked)
- **purchase FK** — links depreciation entries to capital asset Purchases
- **bundle FK** — audit trail back to the import event

Periods can be any granularity. Monthly for standard businesses. Weekly
for construction companies (JPods). Quarterly for long-cycle planning.
The dt_period_start and dt_period_end fields are the real boundaries;
the period label is for display.

## Import Path

1. Accountant produces budget in their spreadsheet
2. User uploads CSV via Connection/Bundle import
3. Bundle record captures the import event (audit trail)
4. Budget records are created for future periods
5. Past locked periods are not modified
6. Forecast engine picks up the new budget data immediately

## The Alice Loop

Alice compares Budget vs Actual at period close:

1. **Budget says** $12,500 salary expense in October
2. **GL journals say** $13,000 actually posted (overtime)
3. **Variance** is $500 unfavorable
4. **Alice flags** the pattern: salary has exceeded budget 3 of last 4 months
5. **Next budget cycle** the accountant adjusts — or the owner addresses the overtime

This is not reporting. This is operational learning. The budget stops being
a document that sits in a drawer. It becomes a measurement instrument that
tells the business where its assumptions are wrong.

## What WebClerk Does Not Do

- Tax calculations or filings
- GAAP/IFRS compliance
- Depreciation schedule computation (the accountant provides the numbers)
- Payroll processing (the budget contains the expected payroll amounts)
- Bank reconciliation
- Audit workpapers
- Multi-entity consolidation for regulatory purposes

These are accounting functions. They belong in accounting tools operated
by accountants. WebClerk feeds them data and consumes their output.
The boundary is the GL export outbound and the Budget import inbound.

## API Actions

All via `POST /wcapi/manage/`:

```json
{"action": "get_trial_balance", "params": {"start": "2026-01-01", "end": "2026-09-30"}}
{"action": "get_income_statement", "params": {"start": "2026-01-01", "end": "2026-09-30"}}
{"action": "get_balance_sheet", "params": {"as_of": "2026-09-30"}}
{"action": "get_aged_payables", "params": {"as_of": "2026-09-30"}}
{"action": "get_cash_forecast", "params": {"months": 6}}
{"action": "get_budget_vs_actual", "params": {"period": "2026-09"}}
```

## Related

- `readmes/products/forecasting.md` — original forecast formula design
- `apps/accounts/services/financial_statements.py` — Trial Balance, P&L, Balance Sheet
- `apps/accounts/services/forecast.py` — Cash Forecast + Budget vs Actual
- `apps/accounts/services/aged_payables.py` — AP Aging
- `apps/accounts/services/gl_export.py` — GL export to accounting programs
- `apps/accounts/samples/` — example CSV files for budget import
