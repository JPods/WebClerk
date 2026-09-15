# Tax Calculation — WebClerk 3.0

Established 2026-08-05.

## Architecture

Tax calculation is **server-side authoritative** (backend is source of truth).
The frontend reads and displays results; users can override per-line rates.

### Data Flow

```
Customer record
  ├── tax_exempt_code → if non-empty, entire transaction is exempt
  └── tax_jurisdiction_id → TaxJurisdiction record
        ├── tax_rate_sales → transaction.finance.sales_tax_rate
        ├── tax_rate_cost → transaction.tax.cost_rate
        └── tax_rate_on_shipping → transaction.tax.shipping

applyCustomerDefaults.ts (frontend)
  → writes finance + tax envelopes on transaction header
  → backend recalculates via totals.py on save

totals.py: recalculate_totals()
  → iterates lines, applies tax based on priority chain
  → writes metadata.tax_decisions audit trail
  → persists totals + metadata
```

### Tax Priority Chain (per product line)

Priority order — first match wins:

1. **Line `sales_rate` override** — user entered a per-line tax rate
2. **Line `sales` amount** — explicit tax dollar amount on line
3. **Header rate** — from jurisdiction, applied to taxable amount
4. **Item exempt** — `cost.tax_code` in (EXEMPT, NONTAXABLE) → zero tax
5. **Customer exempt** — `tax.exempt_code` non-empty → all lines zero

Lines with `line_type` of `tax`, `shipping`, or `discount` skip the tax
calculation entirely — they route to their own accumulators.

### Line Types

| line_type | Accumulator | Taxed? |
|-----------|------------|--------|
| `product` | subtotal | Yes (per priority chain) |
| `tax` | tax_total | No (environmental fees, recycling, etc.) |
| `shipping` | shipping_total | Separate rate (tax_rate_on_shipping) |
| `discount` | subtracted from subtotal | No |

### Tax on Shipping

Jurisdictions where shipping is taxable have `tax_rate_on_shipping > 0`.
Applied to `shipping_total` after all shipping lines are summed.
Stored as: `tax_envelope.shipping` or `finance.tax_on_shipping_rate`.

### Rate Normalization

All rates stored as decimals (0.0825 = 8.25%). If a value > 1 arrives,
totals.py normalizes it: `rate / 100`. This handles both decimal and
percentage input.

---

## Audit Trail

Every `recalculate_totals()` call writes `header.metadata.tax_decisions`:

```json
{
  "dt": "2026-08-05T14:30:00+00:00",
  "exempt": false,
  "header_rate": 0.0625,
  "jurisdiction": "Texas Sales Tax",
  "lines": [
    {
      "line_id": 42,
      "rate": 0.0625,
      "taxable": 199.95,
      "tax": 12.50,
      "source": "header_rate",
      "jurisdiction": "Texas Sales Tax"
    },
    {
      "line_id": 43,
      "rate": 0.08,
      "taxable": 50.00,
      "tax": 4.00,
      "source": "line_override",
      "jurisdiction": "Texas Sales Tax"
    },
    {
      "line_id": 44,
      "rate": 0,
      "taxable": 0,
      "tax": 0,
      "source": "item_exempt",
      "jurisdiction": "Texas Sales Tax"
    }
  ]
}
```

**Sources:**
- `header_rate` — calculated from jurisdiction rate
- `line_override` — user set per-line `sales_rate`
- `line_amount` — user set per-line `sales` dollar amount
- `item_exempt` — item's `cost.tax_code` is EXEMPT/NONTAXABLE
- `avalara` / `taxjar` — future external service (see `readmes/todo-tax-services.md`)

---

## Tax Exemption

Stored on org (customer/vendor) in `financial.common.settings`:

| Field | Type | Purpose |
|-------|------|---------|
| `tax_exempt` | boolean | Master exempt flag |
| `tax_exempt_id` | string | Certificate number/reference |
| `tax_exempt_exp` | date | Certificate expiration date |
| `tax_exempt_verified_by` | string | Who verified the certificate |
| `tax_exempt_verified_dt` | date | When it was verified |

OrgFinancialsPanel shows these with an amber warning when the cert is expired.

When exempt: `applyCustomerDefaults` sets `tax.exempt_code` on the transaction,
and `totals.py` skips all line tax calculations.

---

## Jurisdiction Seed Data

Management command: `python manage.py seed_tax_jurisdictions`

- 50 US states + DC
- State-level rates only (local/city rates vary — users add those)
- Includes tax-on-shipping flags per state
- Idempotent; `--force` to overwrite existing
- Default GL account: `2100-SalesTaxPayable`

Jurisdiction IDs follow pattern `US_XX` (e.g., `US_TX`, `US_CA`).

---

## Frontend Components

| Component | File | Role |
|-----------|------|------|
| `LineCardRenderer` | `components/detail/LineCardRenderer.tsx` | Line type toggle buttons (Ship/Tax/Disc) in footer bar |
| `useLineCard` | `hooks/useLineCard.ts` | `tax%` column, `tax_rate` field behavior, bulk edit support |
| `applyCustomerDefaults` | `utils/applyCustomerDefaults.ts` | Customer → jurisdiction → rate flow |
| `OrgFinancialsPanel` | `apps/orgs/components/OrgFinancialsPanel.tsx` | Tax exemption cert display |
| `TaxReportPrintDocument` | `components/print/TaxReportPrintDocument.tsx` | Tax summary by jurisdiction/period |

### Line Type Toggle

In LineCardRenderer footer bar, when a line is selected and editing is active:
- **Ship** (blue) — marks line as shipping
- **Tax** (amber) — marks line as tax
- **Disc** (red) — marks line as discount
- Click same button again to revert to `product`

### Tax Rate Column

Sell-side lines show a `tax%` column. Editable per line. Bulk-editable via
header click (sets all selected lines to the same rate). The per-line
`sales_rate` takes priority over the header rate in `totals.py`.

---

## Backend Files

| File | Role |
|------|------|
| `apps/transactions/services/totals.py` | Core tax engine + audit trail |
| `apps/accounts/models/tax_jurisdiction.py` | TaxJurisdiction model |
| `apps/accounts/choices.py` | `TAX_SERVICE_PROVIDER_CHOICES` |
| `apps/accounts/management/commands/seed_tax_jurisdictions.py` | US state seed data |

---

## External Tax Services

Avalara and TaxJar integrations are deferred. Full build prompt at
`readmes/todo-tax-services.md`. The `service_provider` field on
TaxJurisdiction and the `tax_service_id` field on LineTax are the
integration hooks — already in place, waiting for service code.
