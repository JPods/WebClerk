# Currency & Exchange Rate Architecture

**Decision date:** 2026-08-25
**Status:** Wired — capture, journalize, GL settlement, erosion, org metrics all connected
**Industry gap:** #1 from industry-comparison.md

## Design Principle

Simple and user-controlled. The system captures rates and calculates differences. The user owns the rate on their transaction. The GL accounts for deviations at settlement.

## How It Works

### 1. Rate Capture

When a transaction is created for a foreign-currency customer, `capture_rate()` stamps the current exchange rate onto the transaction's `sell` envelope:

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

As a transaction moves from proposal → order → invoice → payment, the user may renegotiate the exchange rate. The user is responsible for updating `sell.exchange_rate` on the record. The system does not auto-update rates — the captured rate is the agreed rate.

### 3. FX Settlement at Journalize

When a payment is journalized against a foreign-currency invoice, the system:

1. Reads the captured rate from `invoice.sell.exchange_rate`
2. Gets the current rate from the exchange rate Setting
3. Calculates the difference on the payment amount
4. Posts a GL journal entry to `OTHER-FXGAINLOSS-000`:
   - **FX gain** (current rate more favorable): credit FX gain/loss account
   - **FX loss** (current rate less favorable): debit FX gain/loss account
5. Documents the FX details in `payment.sell.fx`:
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
7. Updates the customer org's `financial.fx.gain_loss_mtd/ytd/alltime`

### 4. FX Rounding Absorption

Small FX variances (< $2.00) from rounding during journalization are auto-absorbed into `MISC-FXROUNDING-000` per WC2 GL2 rule. This prevents out-of-balance journals from penny-level FX math.

## Commission Parallel

Commissions follow the same pattern but at the **line level**, not the transaction level:

- Rate captured per line (different items may have different commission rates or reps)
- User adjusts if renegotiated
- Accrued at invoice journalize time via `accrue_commission()`
- Already wired in `journalize_invoice()` post-posting block

Both currency and commission share the principle: **capture at the moment, user-adjustable, settled at journalize.**

## Where Everything Lives

| Component | File | Function/Field |
|-----------|------|----------------|
| Currency model | `apps/accounts/models/currency.py` | `Currency` (code, name, symbol, precision) |
| Exchange rate Setting | `apps/accounts/services/exchange_rates.py` | `_get_config()` → Setting `wc:exchange_rates` |
| Get current rate | `exchange_rates.py` | `get_rate(currency_code)` |
| Convert amount | `exchange_rates.py` | `convert(amount, currency, to_base, rate_override)` |
| Capture rate on transaction | `exchange_rates.py` | `capture_rate(currency_code, transaction)` |
| Set/update rate | `exchange_rates.py` | `set_rate(currency_code, rate, source)` |
| FX settlement at payment | `journalize.py` | Inside `journalize_payment()` |
| FX GL account | `journalize.py` | `DEFAULTS['fx_gain_loss']` = `OTHER-FXGAINLOSS-000` |
| FX rounding absorption | `journalize.py` | `_check_balance()` with `FX_ABSORPTION_ACCOUNT` |
| FX erosion auto-detect | `journalize.py` | Creates `Erosion(category='fx_loss')` on loss |
| Org FX metrics | `journalize.py` | `_update_org_fx_metrics()` → `financial.fx.*` |
| Erosion model | `apps/accounts/models/erosion.py` | `fx_loss` category |
| Org FX structure | `apps/orgs/models/constants.py` | `financial.fx.gain_loss_mtd/ytd/alltime` |

## GL Accounts

| Account | Purpose |
|---------|---------|
| `OTHER-FXGAINLOSS-000` | FX gain/loss from rate changes between capture and settlement |
| `MISC-FXROUNDING-000` | Auto-absorbed FX rounding differences < $2.00 |

## What's NOT Built

- **External rate API** — rates are manually entered via `set_rate()`. An API caller could be added to pull daily rates from a provider.
- **Period-end revaluation** — open invoices/orders not yet settled are not revalued at month-end. This is a future enhancement if accounting compliance requires it.
- **Multi-currency GL** — all GL entries are in base currency. Dual-amount (functional + transaction currency) GL posting is not implemented.
