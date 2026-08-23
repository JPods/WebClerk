# Currency Precision — Company → User → Display

## How It Works

Currency formatting flows from the company Setting through to every DataGrid cell:

```
Company Setting #438 .prefs.currency
  → /wcapi/bootstrap/ (one call at login, versioned)
    → Redux state.company.currency
      → useLineCard reads precision per field
        → DataGrid formats cells with beh.precision
```

## Company Setting Fields

| Field | Default | What it controls |
|-------|---------|-----------------|
| `unit_price_precision` | 2 | Unit price, discounted price display |
| `unit_cost_precision` | 5 | Unit cost display (5 decimals for raw materials) |
| `total_precision` | 2 | Extended, subtotals, totals |
| `qty_precision` | 0 | Quantity fields (whole numbers) |
| `symbol` | $ | Currency symbol (footers only, not line data) |
| `code` | USD | ISO currency code |
| `locale` | en-US | Number formatting locale |

## Line Data vs Footers

- **Line data**: numbers only, no currency symbol. `1,234.00` not `$1,234.00`
- **Footers** (deposit, backlog, total): include currency symbol. `$6,492.00`

## Future: User Pref — Suppress Decimals

For reports and dashboards showing large values, users should be able to suppress
decimal places via a user pref. When working with values in the thousands or millions,
`.00` is noise.

**Proposed pref**: `user.prefs.display.suppress_decimals`

| Value | Behavior |
|-------|----------|
| `false` (default) | Show full precision from company setting |
| `true` | Show 0 decimal places for all currency fields |
| `"auto"` | Suppress decimals when all visible values are > $100 |

**Implementation**: DataGrid checks this pref and overrides `beh.precision` to 0
when active. The underlying data retains full precision — this is display only.

**Where it applies**: DataBrowser list views, report views, dashboards.
Does NOT apply to transaction detail line cards (always full precision for data entry).

## Changing Precision

Edit Setting #438 (`company-profile`) `.prefs.currency` fields. React picks up
changes on next browser refresh (bootstrap endpoint is versioned — only re-downloads
when the Setting changes).

No code changes needed to adjust precision.
