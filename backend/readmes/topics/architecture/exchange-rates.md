# Exchange Rates — Setting-Based Currency Conversion

**Created:** 2026-08-10
**Service:** `apps/accounts/services/exchange_rates.py`
**Setting:** `purpose='exchange_rates'` (id=642)
**Replaced:** `ExchangeRate` model, `ExchangeTransaction` model (dropped 2026-08-10)

---

## Principle

All transactions operate in base currency — just as all datetimes are UTC.
Exchange rates are a display/output concern, not a storage concern.

When sharing data with a foreign-currency trading partner, the rate
captured at transaction time is applied. At settlement, the difference
between the captured rate and the current bank rate creates a balancing
payment record journalized to an FX gain/loss GL account.

---

## Setting Record

One Setting record holds all exchange rates as JSON:

```json
{
  "base_currency": "USD",
  "precision_convert": 4,
  "precision_display": 2,
  "rates": {
    "EUR": { "rate": 0.92, "dt_updated": 1723334400000, "source": "manual" },
    "GBP": { "rate": 0.79, "dt_updated": 1723334400000, "source": "manual" },
    "CAD": { "rate": 1.36, "dt_updated": 1723334400000, "source": "api" }
  },
  "dt_updated": 1723334400000,
  "source": "manual"
}
```

- `precision_convert` (4) — extra decimal places during math to prevent rounding error (wc2 pattern)
- `precision_display` (2) — what the user sees on screen and print
- `source` — `manual` or a Connection name/id for auto-update

---

## Flow

```
Transaction Created (Order/Invoice)
    │
    ├─ All amounts stored in base currency (USD)
    │
    ├─ capture_rate('EUR', invoice)
    │     └─ Stamps sell.exchange_rate, sell.exchange_currency, sell.exchange_dt
    │
    ├─ Print / Share with trading partner
    │     └─ convert(amount, 'EUR') using captured rate
    │
    ├─ Payment received
    │     └─ settle_fx_difference(invoice_id, payment_id)
    │           ├─ Compares captured rate vs current bank rate
    │           ├─ Creates balancing Ledger record (source='FX')
    │           └─ Journalized to FX gain/loss GL account
    │
    └─ Done — base currency is always the source of truth
```

---

## Service API

### get_rate(currency_code) → Decimal

Returns the current rate for base → foreign. Returns `1` if same as base,
`None` if not configured.

### convert(amount, currency_code, to_base=False, rate_override=None) → Decimal

Convert between base and foreign. `to_base=True` converts foreign → base.
Uses `precision_convert` for rounding.

### set_rate(currency_code, rate, source='manual')

Set or update a rate. Called manually or by a Connection to an exchange
rate API.

### capture_rate(currency_code, transaction) → float

Stamp the current rate onto a transaction's `sell` envelope. Call this
when creating an order/invoice for a foreign-currency customer.

### settle_fx_difference(invoice_id, payment_id) → dict

After payment, create a balancing Ledger record for the FX gain or loss.
Returns `{fx_amount, direction, fx_ledger_id, captured_rate, current_rate}`.

### format_display(amount, currency_code='') → str

Format for display using `precision_display`.

---

## WC2 Heritage

WC2 used two precision levels (`viExDisPrec` for display, `viExConPrec`
for conversion with +4 extra places) and stored original values in
parallel arrays for reversion. WC3 simplifies:

- No parallel arrays — base currency is always stored, conversion is
  at the boundary
- Two precisions carried forward in the Setting (convert=4, display=2)
- FX gain/loss at settlement replaces WC2's toggle model

---

## Connection for Auto-Update

A Connection record (type=api) to an exchange rate provider can call
`set_rate()` to update the Setting on the customer's schedule.

```python
# Example: Connection calls this after fetching rates
from apps.accounts.services.exchange_rates import set_rate

set_rate('EUR', 0.93, source='conn-exchange-api')
set_rate('GBP', 0.80, source='conn-exchange-api')
```

No Connection exists yet — created when a customer needs it.

---

## What Was Dropped

| Model | Table | Why |
|-------|-------|-----|
| `ExchangeRate` | `acct_exchange_rates` | Over-engineered. Time-windowed rates, unique constraints on date ranges, separate table for what fits in one Setting JSON. |
| `ExchangeTransaction` | `acct_exchanges` | Nearly identical to ExchangeRate. No transaction logic was ever implemented. |

Migration `0018_drop_exchange_rate_and_exchange_transaction` dropped both tables.
All references removed from admin, model registry, resolver, databrowser seed,
restore, and alice seed.
