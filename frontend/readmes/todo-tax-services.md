# External Tax Service Integration — Build Prompt

Established 2026-08-05. Use this document to brief a future session on building
Avalara and TaxJar integrations for WebClerk 3.0.

---

## What Already Exists

The built-in tax system is complete. This is what a future session can rely on:

### Backend (Python/Django)

| Component | File | What it does |
|-----------|------|-------------|
| **totals.py** | `apps/transactions/services/totals.py` | Core tax engine. Recalculates all line + header totals. Tax priority: line `sales_rate` override > line `sales` amount > header rate. Exempt customers get zero tax. Item-level `tax_code` EXEMPT skips that line. |
| **Tax audit trail** | Same file | Every `recalculate_totals()` call writes `metadata.tax_decisions` with timestamp, exempt flag, header_rate, jurisdiction, and per-line entries (rate, taxable, tax, source). Sources: `header_rate`, `line_override`, `line_amount`, `item_exempt`. |
| **TaxJurisdiction model** | `apps/accounts/models/tax_jurisdiction.py` | `tax_jurisdiction`, `tax_name`, `tax_rate_sales`, `tax_rate_cost`, `tax_rate_on_shipping`, `service_provider`, `service_id`, `scripts`, `gl_account_payable`, `is_active`. |
| **Service provider choices** | `apps/accounts/choices.py` | `TAX_SERVICE_PROVIDER_CHOICES`: `""`, `avalara`, `taxjar`, `vertex`, `custom`. Already on TaxJurisdiction model. |
| **Seed command** | `apps/accounts/management/commands/seed_tax_jurisdictions.py` | 50 states + DC. Idempotent. `--force` to update. |
| **Customer defaults flow** | `applyCustomerDefaults.ts` | When customer is selected on a transaction, fetches their TaxJurisdiction and writes `finance.sales_tax_rate` + `tax.sales_rate/cost_rate/shipping` to the header. |

### Frontend (React/TypeScript)

| Component | File | What it does |
|-----------|------|-------------|
| **LineTax type** | `apps/transactions/types/transactionTypes.ts` | `sales_rate`, `sales`, `cost_rate`, `cost`, `shipping`, `tax_service_id`. |
| **Tax% column** | `hooks/useLineCard.ts` | Editable `tax_rate` column on sell-side lines. Bulk-editable. Updates `tax.sales_rate`. |
| **Line type toggle** | `apps/transactions/components/detail/LineCardRenderer.tsx` | Ship/Tax/Disc buttons in footer bar. Toggle line_type between product/shipping/tax/discount. |
| **Tax exemption display** | `apps/orgs/components/OrgFinancialsPanel.tsx` | Shows tax_exempt_id, expiration (with amber warning if expired), verified_by/dt. |
| **Tax report** | `apps/transactions/components/print/TaxReportPrintDocument.tsx` | Summary by jurisdiction + period via universal print renderer. |
| **Tax decisions in metadata** | `apps/transactions/types/transactionTypes.ts` | `TransactionMetadata.tax_decisions` type defined. |

---

## What Needs to Be Built

### 1. Avalara Integration

**Connection record (Setting):**
- Create a Setting record with key `tax_service_avalara` containing:
  ```json
  {
    "provider": "avalara",
    "account_id": "",
    "license_key": "",
    "environment": "sandbox",
    "company_code": "",
    "enabled": false
  }
  ```
- Seed via management command (same pattern as `seed_print_layouts`).
- User enters their own keys in DataBrowser Settings view.

**Python service — `apps/accounts/services/tax_avalara.py`:**
- Use the [AvaTax REST API v2](https://developer.avalara.com/api-reference/avatax/rest/v2/).
- Implement:
  - `calculate_tax(transaction_header, lines)` — POST to `/api/v2/transactions/create` with `type: SalesOrder` (estimate) or `SalesInvoice` (commit).
  - `commit_transaction(transaction_id)` — POST to commit when invoice is finalized.
  - `void_transaction(transaction_id)` — POST when invoice is cancelled/credited.
  - `validate_address(address)` — POST to `/api/v2/addresses/resolve`.
- Map WC3 line items to Avalara `LineItem` objects:
  - `itemCode` = line.item.ida_item
  - `quantity` = line.quantity.active
  - `amount` = line.price.extended
  - `taxCode` = line.cost.tax_code (or default to `P0000000` for general tangible goods)
- Response handling:
  - Write per-line tax amounts back to `line.tax.sales` and `line.tax.sales_rate`.
  - Write `tax_service_id` = Avalara's `transactionId` to `line.tax.tax_service_id`.
  - Tax audit trail source = `'avalara'` (add to source enum).

**Integration point in totals.py:**
- Before the manual tax calculation loop, check if the header's jurisdiction has `service_provider = 'avalara'` and credentials are configured.
- If yes: call `calculate_tax()` instead of the manual loop. Write results the same way (tax_decisions with source `'avalara'`).
- If Avalara call fails: fall back to built-in rates. Log a FAULT. Never block a transaction because the tax service is down.

### 2. TaxJar Integration

**Connection record (Setting):**
- Same pattern: `tax_service_taxjar` Setting.
  ```json
  {
    "provider": "taxjar",
    "api_token": "",
    "environment": "sandbox",
    "enabled": false
  }
  ```

**Python service — `apps/accounts/services/tax_taxjar.py`:**
- Use the [TaxJar API v2](https://developers.taxjar.com/api/reference/).
- Implement:
  - `calculate_tax(transaction_header, lines)` — POST to `/v2/taxes`.
  - `create_transaction(transaction_header, lines)` — POST to `/v2/transactions/orders` (for reporting).
  - `refund_transaction(transaction_id)` — POST to `/v2/transactions/refunds`.
  - `validate_address(address)` — POST to `/v2/addresses/validate`.
- Map WC3 fields to TaxJar:
  - `from_*` = company address (from company Settings)
  - `to_*` = customer ship-to address
  - `line_items[].id` = line.id
  - `line_items[].quantity` = line.quantity.active
  - `line_items[].unit_price` = line.price.unit
  - `line_items[].product_tax_code` = line.cost.tax_code
- Response: same write-back pattern as Avalara.

### 3. Shared Infrastructure

**Tax service dispatcher — `apps/accounts/services/tax_dispatch.py`:**
```python
def get_tax_service(jurisdiction: TaxJurisdiction):
    """Return the appropriate tax service based on jurisdiction config."""
    provider = jurisdiction.service_provider
    if provider == 'avalara':
        from .tax_avalara import AvalaxService
        return AvalaraService(jurisdiction)
    elif provider == 'taxjar':
        from .tax_taxjar import TaxJarService
        return TaxJarService(jurisdiction)
    return None  # Use built-in
```

**Base class — `apps/accounts/services/tax_base.py`:**
```python
class TaxServiceBase:
    def __init__(self, jurisdiction):
        self.jurisdiction = jurisdiction

    def calculate_tax(self, header, lines) -> dict:
        """Return {tax_total, line_taxes: [{line_id, rate, tax, taxable}]}"""
        raise NotImplementedError

    def commit(self, header) -> None:
        """Commit/finalize the tax transaction."""
        pass

    def void(self, header) -> None:
        """Void/cancel the tax transaction."""
        pass

    def validate_address(self, address: dict) -> dict:
        """Validate and normalize an address."""
        raise NotImplementedError
```

**Credential loading pattern:**
```python
from apps.core.models.setting import Setting

def _load_credentials(provider: str) -> dict:
    setting = Setting.objects.filter(key=f'tax_service_{provider}').first()
    if not setting or not setting.value.get('enabled'):
        return {}
    return setting.value
```

### 4. Tax audit trail extension

Add `'avalara'` and `'taxjar'` to the `source` values in tax_decisions entries. The TypeScript type already has a union — extend it:

```typescript
source?: 'header_rate' | 'line_override' | 'line_amount' | 'item_exempt' | 'avalara' | 'taxjar';
```

### 5. Address validation UI

Both services offer address validation. Wire it into the ship-to address field on transactions:
- On blur of the ship-to address, if a tax service is configured, call `validate_address()`.
- Show a toast if the address was corrected. Let the user accept or reject.
- This is also useful for shipping label generation (Phase 3).

---

## Testing

- **Sandbox keys:** Both Avalara and TaxJar offer free sandbox environments. Seed the Setting with `environment: 'sandbox'` by default.
- **Fallback test:** Disconnect network, verify that transactions still calculate tax using built-in rates and log a FAULT.
- **Tax audit verification:** After a service call, check `metadata.tax_decisions.lines[].source` = `'avalara'` or `'taxjar'`.
- **Rate comparison:** For a known jurisdiction, compare service-calculated rate with seed data rate. Log any delta > 0.5% as an observation for Alice.

---

## Scope Estimate

- 1 session per service (Avalara, TaxJar)
- 1 session for shared infrastructure + address validation
- Total: 3 sessions

## Dependencies

- Phase 1 complete (done)
- Built-in tax complete (done)
- Company address in Settings (needed for `from_*` fields — verify it exists)
- Ship-to address on transactions (needed for `to_*` fields — verify field path)
