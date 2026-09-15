# Payment Application

> **Last updated**: 2026-08-09
> **Owner**: Alice
> **Backend**: `apps/transactions/services/payment_pending.py`
> **Models**: `Payment`, `PendingPaymentApplication`, `Invoice`
> **WC2 heritage**: Apply Payment dialog, `Ledger_TallyBal`, `DCash`

---

## How Payments Work

Every payment application flows through `PendingPaymentApplication`. If the
invoice is unlocked, it applies immediately. If locked, it queues for later.
One path, one audit trail.

**Ask Alice:** "Apply payment to invoice" or "What's the balance on invoice #42?"

---

## The One Rule

**Every dollar gets its own Payment record.** No silent adjustments to totals.
Cash, discounts, and write-offs are all Payment records — each with its own
GL posting, its own audit trail, its own `payment_method`.

---

## Payment Types

| Type | `payment_method` | Reference | When |
|------|-----------------|-----------|------|
| Cash / check / card | `check`, `credit_card`, `ach`, etc. | User enters | Normal payment |
| Early payment discount | `discount` | `EPD-{invoice_id}` | Payment within terms discount window |
| Write-off difference | `write_off` | `WO-{invoice_id}` | Small balance not worth collecting |

---

## Early Payment Discount

Terms like "2/10 Net 30" mean: 2% discount if paid within 10 days.

**How it works:**
1. Invoice created with `finance.discount_rate = 2` and `finance.discount_days = 10`
   (set from the Terms model via `terms_ledger.py`)
2. Customer sends $980 for a $1,000 invoice, within 10 days
3. User applies the $980 payment
4. System checks: `payment_date <= invoice_date + 10 days`? Yes.
5. System creates **two Payment records**:
   - Payment #1: $980 (cash received)
   - Payment #2: $20 (early payment discount → discount GL account)
6. Both apply to the invoice → balance = $0 → status = `paid`

**Fields on invoice.finance:**
- `discount_rate` — percentage (e.g., 2)
- `discount_days` — window in days (e.g., 10)
- `discount_gl_account` — GL account for discount expense
- `discount_taken` — amount taken (set after application, prevents double)
- `discount_payment_id` — links to the discount Payment record

The discount is automatic when within the window. One-time — `discount_taken`
flag prevents double application.

---

## Write-Off Difference

Customer pays $99.50 on a $100.00 invoice. The $0.50 isn't worth a phone call.

**How it works:**
1. User applies the $99.50 payment with `write_off_difference = True`
   (checkbox in the UI — "Write off difference")
2. System applies the $99.50 normally
3. Remaining balance = $0.50
4. System creates a write-off Payment: $0.50, `payment_method = 'write_off'`
5. Write-off Payment applies to the invoice → balance = $0 → status = `paid`

**Fields on invoice.finance:**
- `write_off_gl_account` — GL account for write-off expense

---

## Unapplied Payments

A customer sends $5,000 with no invoice number. The payment exists but isn't
applied to any specific invoice.

- Payment record created with full amount
- `customer.financial.payments_available` tracks unapplied total
- Reduces `balanceDue` for credit check purposes
- Does NOT move invoices out of past-due aging buckets
- User (or Alice) applies to specific invoices later

---

## Apply Payment API

```python
from apps.transactions.services.payment_pending import apply_payment_to_invoice

result = apply_payment_to_invoice(
    payment_id=42,
    invoice_id=100,
    amount=980.00,
    reason='Check #1234',
    write_off_difference=True,   # write off any remaining balance
)
# Returns: {pending_id, state, amount, applied, write_off}
```

---

## AR Aging (Alice Nightly)

Alice runs full aging recalculation nightly:
- **Future** — due date > 30 days from now (e.g., Christmas season terms)
- **Current** — not yet past due
- **Past 30** — 1-30 days past due
- **Past 60** — 31-60 days past due
- **Past 90** — 61+ days past due

Plus: `avgDaysPaid`, `invoiceCount`, `highCredit` watermark, `totalExposure`
(open orders + balance due).

Fixed buckets — no configuration needed. WC2 used the same boundaries for
20+ years without a customer requesting different ones.

---

## Customer Balance Updates

| When | What updates | How |
|------|-------------|-----|
| Payment applied | `balance_due`, `credit.used` | On save — lightweight |
| Alice periodic (4-6 hr) | Reconciliation check | Flag discrepancies |
| Alice nightly | Full aging buckets, avgDaysPaid, highCredit | Batch recalc |

---

## Files

| File | What it does |
|------|-------------|
| `apps/transactions/services/payment_pending.py` | One-path payment application, early discount, write-off |
| `apps/transactions/services/payment_application.py` | Legacy path (deprecated — use payment_pending) |
| `apps/transactions/models/payment.py` | Payment model |
| `apps/transactions/models/pending_payment.py` | PendingPaymentApplication model |
| `apps/accounts/services/terms_ledger.py` | Terms → schedule → ledger records |
| `apps/transactions/services/payment_gateways.py` | PayPal, Stripe integration stubs |

---

## WC2 → WC3 Translation

| WC2 | WC3 |
|-----|-----|
| Apply Payment dialog | `apply_payment_to_invoice()` |
| Discount Difference checkbox | `write_off_difference=True` parameter |
| Early payment discount calc | Auto in `_apply_one()` — checks date window |
| `DCash` table | `Payment` + `PendingPaymentApplication` |
| `Ledger_TallyBal` | Alice nightly aging (planned) |
| `RunningBalance` | `credit_check.py` + on-save balance update |
| `unAppliedValue` on Ledger | Unapplied payment = Payment with no applications |
