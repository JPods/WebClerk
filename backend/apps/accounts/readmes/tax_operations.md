# Tax Calculation — Operations Guide
**Built:** 2026-07-04 | **Source:** WC2 TaxCalcLine, TaxWebService mining

---

## Overview

Line-level tax calculation with jurisdiction lookup, customer exemptions, and optional external API. US sales tax focus — VAT deferred for JPods later.

---

## How Tax Is Calculated

```
Item not taxable?     → 0 (e.g., food, medicine)
Customer exempt?      → 0 (non-empty exempt code, unless 'DoTax')
                      ↓
Jurisdiction lookup by customer's financial.tax.jurisdiction_id
                      ↓
External API configured?  → try Avalara/TaxJar/TaxCloud
  API fails?              → fall back to local rate
                      ↓
Local: ext_price × tax_rate_sales / 100
```

---

## Customer Tax Fields (real fields on OrgBase)

```
OrgBase
  ├── tax_jurisdiction FK  → TaxJurisdiction (drives the rate on all transactions)
  └── tax_exempt_code      → CharField: empty=taxable, certificate#=exempt, 'DoTax'=force taxable
```

- `tax_jurisdiction` — FK to TaxJurisdiction. When a proposal/order/invoice is created for this customer, the tax calc uses this jurisdiction's rate.
- `tax_exempt_code` — empty = taxable, any value = exempt certificate number. Special: `'DoTax'` forces taxable even when code is non-empty (for resellers buying for own use).
- Both are real indexed fields, visible in DataBrowser, filterable.

**Propagation:** Customer → Order/Invoice header → each line taxed at that rate. The `calculate_transaction_tax` service pulls `tax_jurisdiction_id` and `tax_exempt_code` from the customer org automatically.

**Line-level override:** Users can override tax on any individual line. The customer jurisdiction is the default, but special circumstances (different delivery location, tax-exempt specific item, negotiated arrangement) require line-level control. The line's `tax` JSON can carry its own `jurisdiction_id`, `rate`, or `exempt` flag that overrides the header. We cannot guess every special circumstance — provide the tool, let the user decide.

---

## TaxJurisdiction Model

```
TaxJurisdiction
  ├── tax_jurisdiction      → code/name (e.g., 'OK', 'OK-TULSA')
  ├── tax_rate_sales        → sales tax rate (e.g., 8.517)
  ├── tax_rate_cost         → cost-based tax rate (rare)
  ├── tax_rate_on_shipping  → shipping tax rate (some states tax shipping)
  ├── gl_account_payable    → GL account for tax payable
  ├── service_provider      → 'avalara', 'taxjar', 'taxcloud', or blank (local)
  └── scripts               → JSON for precision, custom rules
```

---

## Three Modes

| Mode | How It Works | Cost |
|---|---|---|
| **Local** (default) | Rate from TaxJurisdiction table | Free |
| **External API** | Avalara, TaxJar, or TaxCloud REST call | $19-500/mo |
| **Ingrid** (future) | Aggregated jurisdiction data from the network | Via WCHQ |

External API is configured per jurisdiction via `service_provider` field. Falls back to local rate if API fails. API credentials in Setting.

---

## Tax on Transactions

`calculate_transaction_tax(transaction_id, model_name)` — walks all lines, applies tax per line, updates line.tax JSON, returns total.

Each line's tax JSON:
```json
{
  "sales_rate": 8.517,
  "sales": 4.26,
  "cost_rate": null,
  "cost": null
}
```

---

## Tax Reporting

`tax_summary_by_period(year, month, months=3)` — quarterly sales tax filing:

```
Jurisdiction    Invoices    Tax Collected
Oklahoma           42         $1,234.56
Texas              15           $456.78
Total              57         $1,691.34
```

Print via TaxReportPrintDocument with company header, EIN, certification block, signature lines.

---

## Files

| File | Purpose |
|------|---------|
| `apps/accounts/services/tax_calculation.py` | Line + transaction tax calc |
| `apps/accounts/models/tax_jurisdiction.py` | TaxJurisdiction model |
| `apps/accounts/services/journalize.py` | tax_summary_by_period() |
