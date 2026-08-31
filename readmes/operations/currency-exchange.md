# Currency & Exchange Rate Architecture

**Created:** 2026-08-10 (service), 2026-08-25 (GL settlement wired)
**Status:** Wired — capture, journalize, GL settlement, erosion, org metrics all connected
**Industry gap:** #1 from industry-comparison.md

---

## Design Principle

All transactions operate in base currency — just as all datetimes are UTC.
Exchange rates are a display/output concern, not a storage concern.

When sharing data with a foreign-currency trading partner, the rate captured at
transaction time is applied. At settlement, the difference between the captured
rate and the current bank rate creates a balancing payment record journalized to
an FX gain/loss GL account.

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
  }
}
```

- `precision_convert` (4) — extra decimal places during math to prevent rounding error (wc2 pattern)
- `precision_display` (2) — what the user sees on screen and print
- `source` — `manual` or a Connection name/id for auto-update

**Replaced:** `ExchangeRate` model and `ExchangeTransaction` model (dropped 2026-08-10).
Both were over-engineered — time-windowed rates, unique constraints on date ranges,
separate table for what fits in one Setting JSON.

---

## Service API

**File:** `apps/accounts/services/exchange_rates.py`
**Setting:** `purpose='exchange_rates'`

| Function | Purpose |
|----------|---------|
| `get_rate(currency_code)` | Current rate for base -> foreign. Returns `1` if same as base, `None` if not configured |
| `convert(amount, currency_code, to_base, rate_override)` | Convert between base and foreign. Uses `precision_convert` |
| `set_rate(currency_code, rate, source)` | Set or update a rate. Called manually or by Connection |
| `capture_rate(currency_code, transaction)` | Stamp current rate onto transaction's `sell` envelope |
| `settle_fx_difference(invoice_id, payment_id)` | After payment, create balancing Ledger record for FX gain/loss |
| `format_display(amount, currency_code)` | Format for display using `precision_display` |

---

## Flow

### 1. Rate Capture

When a transaction is created for a foreign-currency customer, `capture_rate()` stamps:

```json
{
  "sell": {
    "exchange_rate": 0.92,
    "exchange_currency": "EUR",
    "exchange_dt": 1724601600000
  }
}
```

The rate is frozen at that moment. It flows with the transaction through its lifecycle.

### 2. User Adjusts Rate (if needed)

As a transaction moves from proposal -> order -> invoice -> payment, the user may
renegotiate. The user owns `sell.exchange_rate`. The system does not auto-update.

### 3. FX Settlement at Journalize

When a payment is journalized against a foreign-currency invoice:

1. Reads captured rate from `invoice.sell.exchange_rate`
2. Gets current rate from the exchange rate Setting
3. Calculates difference on the payment amount
4. Posts GL journal entry to `OTHER-FXGAINLOSS-000`
5. Documents FX details in `payment.sell.fx`:
   ```json
   {
     "fx": {
       "captured_rate": 0.92,
       "current_rate": 0.89,
       "currency": "EUR",
       "direction": "loss",
       "amount": -3.37,
       "invoice_id": 1234
     }
   }
   ```
6. If FX loss: auto-creates an Erosion record (`category=fx_loss`)
7. Updates customer org's `financial.fx.gain_loss_mtd/ytd/alltime`

### 4. FX Rounding Absorption

Small FX variances (< $2.00) from rounding during journalization are auto-absorbed
into `MISC-FXROUNDING-000` per WC2 GL2 rule.

---

## Commission Parallel

Commissions follow the same pattern at the **line level**:
- Rate captured per line (different items may have different rates or reps)
- User adjusts if renegotiated
- Accrued at invoice journalize time via `accrue_commission()`

Both currency and commission share: **capture at the moment, user-adjustable, settled at journalize.**

---

## WC2 Heritage

WC2 used two precision levels (`viExDisPrec` for display, `viExConPrec` for conversion
with +4 extra places) and stored original values in parallel arrays for reversion.
WC3 simplifies:
- No parallel arrays — base currency is always stored, conversion is at the boundary
- Two precisions carried forward in the Setting (convert=4, display=2)
- FX gain/loss at settlement replaces WC2's toggle model

---

## Connection for Auto-Update

A Connection record (type=api) to an exchange rate provider can call `set_rate()`
on the customer's schedule. No Connection exists yet — created when a customer needs it.

---

## GL Accounts

| Account | Purpose |
|---------|---------|
| `OTHER-FXGAINLOSS-000` | FX gain/loss from rate changes between capture and settlement |
| `MISC-FXROUNDING-000` | Auto-absorbed FX rounding differences < $2.00 |

---

## Where Everything Lives

| Component | File | Function/Field |
|-----------|------|----------------|
| Currency model | `apps/accounts/models/currency.py` | `Currency` (code, name, symbol, precision) |
| Exchange rate Setting | `apps/accounts/services/exchange_rates.py` | `_get_config()` |
| FX settlement at payment | `journalize.py` | Inside `journalize_payment()` |
| FX GL account | `journalize.py` | `DEFAULTS['fx_gain_loss']` |
| FX rounding absorption | `journalize.py` | `_check_balance()` with `FX_ABSORPTION_ACCOUNT` |
| FX erosion auto-detect | `journalize.py` | Creates `Erosion(category='fx_loss')` |
| Org FX metrics | `journalize.py` | `_update_org_fx_metrics()` |
| Org FX structure | `apps/orgs/models/constants.py` | `financial.fx.gain_loss_mtd/ytd/alltime` |

---

## What's NOT Built

- **External rate API** — rates are manually entered. An API caller could pull daily rates.
- **Period-end revaluation** — open invoices/orders not revalued at month-end.
- **Multi-currency GL** — all GL entries in base currency. Dual-amount posting not implemented.
