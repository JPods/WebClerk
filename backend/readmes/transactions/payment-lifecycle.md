# Payment Lifecycle

> **Last updated**: 2026-08-19
> **Owner**: Alice
> **Flight Simulator**: `/flight-simulator` → "Payment Lifecycle"
> **Flowchart**: `readmes/flowcharts/wc3-payment-lifecycle.dot`
> **Backend**: `apps/transactions/models/payment.py`, `apps/transactions/services/payment_pending.py`
> **Models**: `Payment`, `PendingPaymentApplication`, `Invoice`, `Ledger`
> **WC2 heritage**: `Make_Payment`, `PaymentCreate`, `ApplyPayments`, `Ledger_PaySave`, `Ledger_TallyBal`

---

## The Four Payment Fields

| Field | Type | Set when | Changes after | WC2 equivalent |
|-------|------|----------|---------------|----------------|
| `amount` | Immutable | Created | Never | `[Payment]amount` |
| `available` | Working | Created (= amount) | Decremented on apply, incremented on unapply | `[Payment]amountAvailable` |
| `tendered` | Immutable | Created (= amount or POS value) | Never | `[Payment]tendered` |
| `change` | Computed | Created (= tendered - amount) | Never | `[Payment]change` |

`amount` is what the customer is paying. `tendered` is what they physically hand over
(cash scenarios — may exceed amount). `change` is the difference. `available` is the
working field that tracks how much of the payment has been allocated to invoices.

---

## The Lifecycle

```
Order (commitment, no GL)
  ↓ partial ship
Invoice (financial event — AR, Revenue, Tax, COGS, Inventory)
  ↓ customer pays
Payment created (amount, available, tendered, change)
  ↓ allocate
Apply $X to Invoice (PendingPaymentApplication)
  → Payment.available decremented
  → Invoice.totals.received increased
  → Invoice.totals.balance decreased
  → Ledger.value_available updated
  ↓ user action
Journal (post GL entries — DR Cash, CR AR)
  → Payment locked
  ↓ remaining
$Y on account (available_payments on org)
```

---

## How `available` Flows

### On Creation (`Payment.save()`)

```python
if not self.pk:
    if not self.available:
        self.available = self.amount
    if not self.tendered:
        self.tendered = self.amount
if self.tendered > abs(self.amount):
    self.change = self.tendered - abs(self.amount)
```

### On Application (`payment_pending._apply_one()`)

```python
payment.available = max(Decimal('0'), payment.available - amount)
payment.save(update_fields=['available', 'dt_modified', 'version'])
```

### On Unapply (`payment_application.unapply_payment_from_invoice()`)

```python
payment.available = payment.available + unapply_amount
```

### On Validation (`PaymentApplication.clean()`)

```python
if self.amount > self.payment.available:
    raise ValidationError("exceeds payment available")
```

---

## Ledger Integration

The ledger tracks `available`, not `amount`. This matches WC2:

```
WC2:  aLdgValue{1} := -ent.amountAvailable
      aLdgOrig{1}  := -ent.amount

WC3:  value_available = -payment.available  (changes with applications)
      value_original  = -payment.amount     (immutable)
```

### `on_payment_save()` (signal → `ledger_balance.py`)

1. Delete existing ledger records for this payment (idempotent)
2. Create new ledger with `value_available = -available`, `value_original = -amount`
3. Update org aging balances

### `update_org_balances()` (ledger → org.financial)

Computes from ledger records:
- `balance_due` — sum of all ledger value_available (invoices positive, payments negative)
- `available_payments` — sum of `Payment.available` where > 0
- `total_exposure` — balance_due + open_orders - available_payments
- `high_credit` — peak balance ever reached
- `days_avg_paid` — mean days from invoice date to payment date

WC2 equivalent: `Ledger_TallyBal` computed the same fields on Customer.

---

## GL Integration

GL entries are **staged** on `Payment.metadata.gl_accounts` when the payment is saved.
They are **posted** when the user explicitly journals the payment (`post_staged_gl_entries()`).

```
Payment received ($80):
  DR  ASSET-CASH-000          $80   (cash in the bank)
  CR  ASSET-AR-000            $80   (reduce AR)

Payment disbursed (vendor pay):
  DR  LIAB-ACCTSPAY-000       $66   (clear AP)
  CR  ASSET-CASH-000          $66   (cash out)
```

GL posts the **full payment amount**, not the applied amount. The journal captures
the cash event. The application captures the allocation. These are separate:
- **Cash event**: "Customer gave us $80" → GL
- **Allocation**: "We applied $50 to Invoice #X" → PaymentApplication

---

## Serializer

`PaymentSerializer` exposes all four fields:
- `available` — **read-only** (backend is source of truth)
- `change` — **read-only** (computed)
- `tendered` — **writable** (POS sends what customer handed over)
- `amount` — **writable** (the payment amount)

---

## Flight Simulator Scenario

The "Payment Lifecycle" flight sim at `/flight-simulator` walks through 8 steps:

| Step | Action | Payment.available | Invoice.balance |
|------|--------|-------------------|-----------------|
| 1 | Create Order 10 × $10 | — | — |
| 2 | Invoice 6 of 10 = $63 | — | $63 |
| 3 | Accept $80 (tendered $100) | $80 | $63 |
| 4 | Apply $50 to invoice | $30 | $13 |
| 5 | Journal payment | $30 (GL posted) | $13 |
| 6 | Check ledger | $30 | $13 |
| 7 | Apply $13 — invoice paid | $17 | $0 |
| 8 | Summary | $17 on account | Paid |

---

## Reconciliation

`reconcile_org()` validates:
```
Σ(ledger.value_available) == Σ(invoice.balance_due) - Σ(payment.available)
```

If this fails, `rebuild_org_ledgers()` recreates all ledger records from source
invoices and payments — using `available` not `amount`.

---

## WC2 → WC3 Method Map

| WC2 Method | WC3 Equivalent | What it does |
|------------|---------------|-------------|
| `Make_Payment` / `PaymentCreate` | `PaymentSerializer.create()` | Create payment, set amount/available/tendered/change |
| `ApplyPayments` (dialog) | `payment_pending.apply_payment_to_invoice()` | Apply payment to invoice via PendingPaymentApplication |
| `Pay_ApplyBefore` | `payment_pending._apply_one()` | The actual application logic |
| `Ledger_PaySave` | `ledger_balance.on_payment_save()` | Create negative ledger, update org |
| `Ledger_InvSave` | `ledger_balance.on_invoice_save()` | Create positive ledger(s), update org |
| `Ledger_TallyBal` | `ledger_balance.update_org_balances()` | Compute aging, available_payments, exposure |
| `Ledger_RayInit(-3)` | `terms_ledger.record_payment()` | Create the actual Ledger record |
| `LedgerScrub` | `ledger_balance.reconcile_org()` | Validate and report discrepancies |
