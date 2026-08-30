# Payment Lifecycle — WebClerk3

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

## Payment parent_model values

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

## GL Journalizing

### Sales Journal (invoice)
For each invoice line: AR debit, Revenue credit, COGS debit, Inventory credit.

### Cash Journal (payment)
- Positive amount (received): Cash debit, AR credit
- Negative amount (disbursed): Expense debit, Cash credit

### Write-off
Dismiss creates a write-off payment → journalized as:
Write-Off Expense debit, AR credit.

### Batch Journalize
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
| `type` | CharField | `received` or `expense` |
| `method` | CharField | `check`, `cash`, `visa`, `wire`, `ach`, `write_off`, etc. |
| `status` | CharField | `pending`, `completed`, `failed`, `cancelled` |
| `dt_journaled` | BigInteger | 0=editable, non-zero=locked to GL |
