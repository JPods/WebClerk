# Budget Import Samples

Example CSV files for importing budget/schedule entries into WebClerk.

## Files

| File | Period type | Use case |
|------|-----------|----------|
| `budget_monthly_example.csv` | Monthly (2026-10) | Standard business — payroll, rent, depreciation |
| `budget_weekly_example.csv` | Weekly (w41_2026) | JPods construction — payroll, site lease, insurance |

## Column Reference

| Column | Required | Description |
|--------|----------|-------------|
| `period` | Yes | Period label — user-defined (2026-10, w41_2026, q4_2026) |
| `dt_period_start` | Yes | Period start, UTC epoch ms |
| `dt_period_end` | Yes | Period end, UTC epoch ms |
| `account` | Yes | GL account ida — must match a GlAccount record |
| `debit` | Yes | Debit amount (0.00 if none) |
| `credit` | Yes | Credit amount (0.00 if none) |
| `description` | No | Line description |

## Period Naming

Users define their own period labels. Convention:

- **Monthly:** `2026-10`, `2026-11`, `2026-12`
- **Weekly:** `w01_2026`, `w02_2026`, ... `w52_2026`
- **Quarterly:** `q1_2026`, `q2_2026`, `q3_2026`, `q4_2026`

The `dt_period_start` and `dt_period_end` epoch values are the real boundaries.
The label is for display and grouping.

## Double Entry

Depreciation requires both sides:
- **Debit** 6500-DEPRECIATION (expense) — hits P&L
- **Credit** 1500-EQUIPMENT (contra asset) — reduces balance sheet asset

## What Goes Here vs. What Doesn't

**In the budget spreadsheet:** expenses with no WC3 transaction — payroll, rent,
insurance, utilities, depreciation. Things the business pays that don't flow
through Purchase orders.

**NOT in the budget spreadsheet:** materials, equipment rental, permits, supplies —
anything purchased through a PO. Those are already Purchase lines in WC3 with
terms and delivery timing. The forecast engine picks them up automatically.

## Import Path

Upload via Connection/Bundle. Each import creates a Bundle record (audit trail).
Entries become Budget records. Past locked periods are not modified.
