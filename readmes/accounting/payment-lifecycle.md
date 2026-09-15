# Payment Lifecycle

> **Last updated**: 2026-08-19
> **Owner**: Alice
> **Flight Simulator**: `/flight-simulator` → "Payment Lifecycle"
> **Flowchart**: `readmes/flowcharts/wc3-payment-lifecycle.dot`
> **Backend**: `apps/transactions/models/payment.py`, `apps/transactions/services/payment_pending.py`
> **Models**: `Payment`, `PendingPaymentApplication`, `Invoice`, `Ledger`
> **WC2 heritage**: `Make_Payment`, `PaymentCreate`, `ApplyPayments`, `Ledger_PaySave`, `Ledger_TallyBal`

---

## Core Concepts

### Payment = a record of money movement

A Payment record captures a single money event: a check received, a wire sent,
a credit card charge, a credit memo, or a shortage carried forward. Payments are
**not** invoices and **not** line items. They are the cash side of the ledger.

### Two fields define a payment's identity

| Field | What it means |
|-------|---------------|
| `parent_id` / `parent_model` | **Where** the payment was entered — the document context |
| `invoice_id` | **Where** the payment is applied — the invoice it reduces |

These are independent. A payment entered on an order (`parent_model='order'`)
may later be applied to an invoice created from that order. A payment entered
at the customer level (`parent_model='customer'`) is a general deposit available
to any document for that customer.

`parent_id`/`parent_model` is the **origin**, not a constraint.

### Payment parent_model values

| parent_model | Meaning | When to use |
|-------------|---------|-------------|
| `customer` | General deposit or prepayment | Entered from the customer record; not tied to a specific order |
| `order` | Payment against a specific order | Entered from the order; focused on that order but available elsewhere |
| `invoice` | Payment against a specific invoice | Entered from the invoice; typically applied immediately |
| `purchase` | Disbursement against a purchase order | AP side — money out |

### Conversion: order → invoice

When an order is converted to an invoice, all payments with
`parent_model='order', parent_id=order.id` are automatically forwarded:
- `invoice_id` is set to the new invoice
- `refs.invoice_ids` is updated
- Invoice `totals.received` and `balance` are recalculated

The payment's `parent_model`/`parent_id` remain unchanged — they record
where the payment was originally entered, not where it ended up.

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

### The `available` field

`available` = how much of this payment remains to be applied.

- **Positive available**: money we're holding — deposit, overpayment, credit memo
- **Negative available**: money the customer owes us from a prior shortfall
- **Zero**: fully applied, nothing left

**Commercial rule: show all payments where `available != 0`.**

Retail interfaces filter to `available > 0` because consumers don't work with
credits and shortfalls. WebClerk is commercial — the user's judgment dominates.
There are many reasons for a negative payment amount that gets applied to an
invoice alongside another payment.

### Shortfall example

Customer owed $400 on Invoice A, paid $350. Payment has `available = -$50`.
Instead of chasing the $50 separately, both parties agree to liquidate it
with the next transaction.

Next Invoice B is $300. Customer sends $350.

Available payments panel shows:
```
Reference    Source       Available    Original
PMT-old      Inv #A       -$50.00     $350.00
PMT-new      Order #B     $350.00     $350.00
```

User applies both to Invoice B: $350 + (-$50) = $300. Invoice paid in full.
Both payments go to `available = 0`. The shortage is liquidated.

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

## Available Payments Panel

When opening the Enter Payment dialog on any order or invoice, the panel
shows **all payments for that customer** where `available != 0`:

- Customer-level payments (general deposits)
- Payments entered on other orders (partially applied or unused)
- Payments with negative available (shortfalls to liquidate)

The **Source** column labels the origin:
- "Customer" — general, not tied to a specific document
- "Order #84" — entered on that order (highlighted if you're on that order)
- "Inv #101" — entered on that invoice

This lets the user see the full picture and apply judgment about how to
allocate cash across documents.

---

## Dismiss Balance

The "Dismiss balance — too little value to chase" checkbox creates a
**separate write-off payment** with `method='write_off'`. This is a
distinct payment record with its own GL account, not a discount.

Discounts are line-level adjustments on the invoice — they reduce the
invoice total by adding a negative line. Discounts are entered on the
invoice directly, not in the payment dialog.

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

### GL Journalizing Summary

**Sales Journal (invoice):**
For each invoice line: AR debit, Revenue credit, COGS debit, Inventory credit.

**Cash Journal (payment):**
- Positive amount (received): Cash debit, AR credit
- Negative amount (disbursed): Expense debit, Cash credit

**Write-off:**
Dismiss creates a write-off payment → journalized as:
Write-Off Expense debit, AR credit.

**Batch Journalize:**
`batch_journalize()` finds all un-journalized invoices, payments, and
purchases. Creates a JournalBatch header with totals, exception count,
and processing status. FX rounding < $2 is auto-absorbed.

---

## Key Models

| Model | Table | Purpose |
|-------|-------|---------|
| Payment | `transactions_payment` | Money movement record |
| PaymentApplication | `payment_applications` | Junction: payment ↔ invoice (amount applied) |
| PendingPaymentApplication | `pending_payment_applications` | Queued applications (locked invoices) |
| Pending | `core_pending` | One-path application via `purpose='payment_application'` |
| GlJournal | `gl_journals` | GL entries created by journalizing |
| JournalBatch | `journal_batches` | Batch header for journalize runs |
| Ledger | `ledger` | AR/AP aging records |

## Key Fields on Payment

| Field | Type | Purpose |
|-------|------|---------|
| `parent_id` | BigInteger | PK of the document where entered |
| `parent_model` | CharField | `order`, `invoice`, `customer`, `purchase` |
| `invoice_id` | FK | Invoice this payment is applied to (null until applied) |
| `amount` | Decimal | Signed: positive=received, negative=disbursed |
| `available` | Decimal | Remaining to apply. Starts=amount, decrements on application |
| `tendered` | Decimal | What the customer physically handed over (POS) |
| `change` | Decimal | Computed: tendered - amount |
| `type` | CharField | `received` or `expense` |
| `method` | CharField | `check`, `cash`, `visa`, `wire`, `ach`, `write_off`, etc. |
| `status` | CharField | `pending`, `completed`, `failed`, `cancelled` |
| `dt_journaled` | BigInteger | 0=editable, non-zero=locked to GL |

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
