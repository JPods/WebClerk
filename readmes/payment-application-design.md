# Payment Application System Design

## Gateway: Spreedly (established 2026-08-05)

**WC3 uses Spreedly as a universal payment aggregator.** One backend integration, user picks their gateway (Stripe, PayPal, Braintree, Authorize.Net). WC3 never sees card data — Spreedly's client-side SDK collects it in a secure iframe.

**Token-in-a-token rule:** WC3 stores ONLY `pm_token` (reference to Spreedly's token, which is itself a reference to the card), `last4`, `brand`, `exp`, `fingerprint`. NEVER card numbers, CVVs, or replayable tokens. This is non-negotiable.

**Backend:** `apps/transactions/services/payment_gateways.py` — `SpreedlyService` class (purchase, authorize, capture, void, credit, refund). Setting #625 holds credentials.

**Square:** Not supported by Spreedly. Direct integration can be added later if needed.

## Overview

This document describes the payment application architecture from WC2 (4D) and how to implement equivalent functionality in WC3 (Django).

---

## WC2 Architecture Summary

### Key Tables (4D)

| Table | ID | Purpose |
|-------|-----|---------|
| Payment | 28 | Payment records with amounts and application status |
| Invoice | 26 | Invoice records with totals and applied amounts |
| Ledger | - | AR aging entries with document references |
| DCash | - | Transaction audit trail (TransAct) |
| Customer | - | Customer master with balance buckets |

### Ledger Entry Types

| docType | Meaning | Value Sign |
|---------|---------|------------|
| 26 | Invoice | Positive (increases AR) |
| 28 | Payment | Negative (decreases AR) |
| -28 | Late Charge | Positive (increases AR) |

### Payment Types

| typePayment | Description |
|-------------|-------------|
| (blank) | Regular payment |
| "AR Credit" | Credit memo applied as payment |
| "Late" | Finance/late charge |

---

## Core Payment Application Flow

### WC2 Flow (4D Methods)

```
PayApply → PayApplyIvc → PayApplyOneInvoice
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            Ledger_InvSave      Ledger_PaySave
                    ↓                   ↓
                    └─────────┬─────────┘
                              ↓
                      Ledger_RayInit (batch save)
                              ↓
                      TransAct_Create (audit trail)
```

### Key Algorithm: PayApplyOneInvoice

```python
# Pseudocode from WC2
def apply_payment_to_invoice(payment, invoice):
    # Only apply if same customer
    if payment.customer_id != invoice.customer_id:
        return 0
    
    # Calculate how much we can apply
    balance_due = invoice.total - invoice.applied_amount - invoice.applied_discount
    apply_amount = min(payment.amount_available, balance_due)
    
    if apply_amount <= 0:
        return 0
    
    # Update invoice
    invoice.applied_amount += apply_amount
    invoice.balance_due = invoice.total - invoice.applied_amount - invoice.applied_discount
    
    # Update payment
    payment.amount_available -= apply_amount
    
    # If invoice fully paid, calculate days to payment
    if invoice.balance_due == 0:
        invoice.paid_days = calculate_paid_days(invoice)
    
    # Create ledger entries
    create_ledger_entry_for_invoice(invoice)
    create_ledger_entry_for_payment(payment)
    
    # Create audit trail
    create_transaction_record(payment, invoice, apply_amount)
    
    return apply_amount
```

---

## Ledger Entry Structure

### Invoice Ledger Entry (docType=26)

| Field | Value | Description |
|-------|-------|-------------|
| docType | 26 | Invoice document type |
| docID | invoice.id | Invoice primary key |
| docNumber | invoice.number | Invoice number |
| dateDue | calculated | Due date from terms |
| origValue | invoice.total | Original invoice amount |
| unAppliedValue | invoice.balance_due | Remaining balance |

### Payment Ledger Entry (docType=28)

| Field | Value | Description |
|-------|-------|-------------|
| docType | 28 (or -28 for late charges) | Payment document type |
| docID | payment.id | Payment primary key |
| docNumber | payment.check_number | Check/reference number |
| dateDue | payment.date | Payment date |
| origValue | -payment.amount | Negative original amount |
| unAppliedValue | -payment.amount_available | Negative remaining amount |

### Split Payment Terms

WC2 supports splitting invoices across multiple due dates based on terms:

```python
# Example: 3-period terms (Net 30, Net 60, Net 90)
# Invoice total: $900
# Creates 3 ledger entries:
#   1. $300 due in 30 days
#   2. $300 due in 60 days  
#   3. $300 due in 90 days
```

---

## Customer Balance Calculation

### WC2: Ledger_TallyBal

Calculates aging buckets from Ledger entries:

```python
def calculate_customer_balance(customer_id):
    # Query all ledger entries with remaining balance
    entries = Ledger.query(
        customer_id=customer_id,
        unapplied_value__ne=0
    )
    
    today = date.today()
    buckets = {
        'future': 0,      # Due date in future
        'current': 0,     # Due today or within grace period
        'past_30': 0,     # 1-30 days past due
        'past_60': 0,     # 31-60 days past due
        'past_90': 0,     # 61+ days past due
    }
    
    for entry in entries:
        days_past_due = (today - entry.date_due).days
        amount = entry.unapplied_value
        
        if days_past_due < 0:
            buckets['future'] += amount
        elif days_past_due <= 0:
            buckets['current'] += amount
        elif days_past_due <= 30:
            buckets['past_30'] += amount
        elif days_past_due <= 60:
            buckets['past_60'] += amount
        else:
            buckets['past_90'] += amount
    
    return buckets
```

---

## WC3 Django Implementation

### Existing Infrastructure

WC3 already has substantial payment/ledger infrastructure:

#### 1. OrgBase.financial JSONB (apps/orgs/models/constants.py)

Customer financial data is stored in `OrgBase.financial` JSONB field:

```python
org.financial = {
    "common": {
        "currency": "USD",
        "account": { "dt_opened", "dt_last_activity", "hold", "cod_only", "inactive" },
        "rating": { "internal", "comments", "credit_score" },
        "settings": { "discount_pct", "tax_exempt", "tax_exempt_id", "terms_id", "notes" },
    },
    "customer": {
        "credit": { "limit", "high", "available" },
        "balances": { "due", "current", "open_orders", "total_exposure" },
        "aging": { "future", "period_1", "period_2", "period_3" },
        "payment": { "days_avg_paid", "days_pay", "dt_last_payment", "last_payment_amount" },
        "sales": { "mtd", "ytd", "lifetime", "dt_last_sale", "last_sale_amount" },
        "deposits": { "unapplied" },
        # ... plus margin, returns, collection, stats, complaints, small_stings
    },
}
```

**Mapping to WC2 concepts:**
| WC2 Field | WC3 Location |
|-----------|--------------|
| Customer.balanceDue | `financial.customer.balances.due` |
| Customer.creditLimit | `financial.customer.credit.limit` |
| Ledger aging buckets | `financial.customer.aging.*` |
| Payment days avg | `financial.customer.payment.days_avg_paid` |

#### 2. Payment Application Service (apps/transactions/services/payment_application.py)

**Already implemented:**
- `apply_payment_to_invoice()` - Core payment application with validation
- `unapply_payment_from_invoice()` - Reverse a payment application
- `get_invoice_payment_status()` - Get comprehensive payment status
- `PaymentApplication` model tracks each application

**Key differences from WC2:**
- Uses `invoice.totals` JSONB instead of separate fields
- Tracks applications via `PaymentApplication` junction model
- Payment has `status` field ('completed', 'fully_applied')

#### 3. Ledger Balance Service (apps/accounts/services/ledger_balance.py)

**Already implemented:**
- `calculate_aging_buckets()` - Calculates aging from Ledger records
- `update_org_balances()` - Updates `org.financial` from ledgers
- `on_invoice_save()` / `on_payment_save()` - Event handlers
- `reconcile_org()` - Validates and corrects discrepancies
- `rebuild_org_ledgers()` - Full reconstruction from source documents

**Ledger value conventions (matching WC2):**
- Invoice ledgers: POSITIVE values (money owed to us)
- Payment ledgers: NEGATIVE values (money received)

#### 4. Terms Ledger Service (apps/accounts/services/terms_ledger.py)

**Already implemented:**
- `compute_schedule()` - Calculates payment schedule from Term
- `ScheduleEntry` dataclass for installments
- Multi-period payment support (like WC2's split terms)
- Early payment discount handling

### What's Missing (Gaps vs WC2)

#### 1. Auto-Apply to Oldest Invoices

WC2's `PayApplyIvc` loops through oldest invoices. Add to `payment_application.py`:

```python
@transaction.atomic
def apply_payment_to_oldest_invoices(payment: Payment) -> List[Dict]:
    """
    Auto-apply payment to oldest unpaid invoices for the org.
    Equivalent to WC2 PayApplyIvc loop.
    """
    applications = []
    
    invoices = Invoice.objects.filter(
        org_id=payment.org_id,
        status__in=['sent', 'partially_paid', 'overdue']
    ).order_by('dt_created', 'id')
    
    remaining = Decimal(str(payment.amount))
    total_applied = sum(p.amount for p in payment.applications.all())
    remaining -= total_applied
    
    for invoice in invoices:
        if remaining <= 0:
            break
        
        result = apply_payment_to_invoice(invoice, payment)
        if result['success']:
            applications.append(result)
            remaining -= Decimal(str(result['amount_applied']))
    
    return applications
```

#### 2. AR Credits and Late Charges

WC2 supports special payment types. Consider adding:

```python
# In Payment model or as constants
PAYMENT_TYPE_CHOICES = [
    ('', 'Regular Payment'),
    ('ar_credit', 'AR Credit'),
    ('late_charge', 'Late Charge'),
]
```

#### 3. Database Changes (Completed ✅)

**Migration:** `apps/transactions/migrations/0030_payment_nullable_invoice.py`

Made `Payment.invoice_id` nullable to support order-level deposits:

```python
# Before: invoice_id was required
invoice_id = models.ForeignKey('transactions.Invoice', on_delete=models.CASCADE, ...)

# After: invoice_id is optional
invoice_id = models.ForeignKey('transactions.Invoice', on_delete=models.CASCADE, 
                                null=True, blank=True, ...)
```

**PaymentSerializer** updated to accept `invoice_id` as optional:
```python
invoice_id = serializers.IntegerField(required=False, allow_null=True)
```

**PaymentMethod** table seeded with default values:
```python
['Cash', 'Check', 'Credit Card', 'ACH', 'Wire Transfer', 'PayPal']
```

#### 4. Paid Days Calculation

WC2's `PaidDaysCalc` records days to payment when invoice fully paid:

```python
def calculate_paid_days(invoice: Invoice) -> int:
    """Calculate days from invoice date to final payment."""
    if invoice.status != 'paid':
        return 0
    
    last_application = invoice.payment_applications.order_by('-applied_at').first()
    if not last_application:
        return 0
    
    invoice_date = invoice.dt_created.date()
    paid_date = last_application.applied_at.date()
    return (paid_date - invoice_date).days
```

Then update `financial.customer.payment.days_avg_paid` on each payment.

---

## API Endpoints

### Existing Endpoints

Check `apps/transactions/urls.py` and `apps/accounts/urls.py` for current payment/invoice endpoints.

### Recommended Additions

```python
# apps/transactions/urls.py additions

urlpatterns += [
    path('payments/<int:pk>/auto-apply/', PaymentAutoApplyView.as_view()),
    path('payments/<int:pk>/applications/', PaymentApplicationsListView.as_view()),
]

# apps/orgs/urls.py additions  
urlpatterns += [
    path('orgs/<str:pk>/aging/', OrgAgingView.as_view()),
    path('orgs/<str:pk>/ledger/rebuild/', OrgLedgerRebuildView.as_view()),
]
```

---

## Special Cases

### AR Credits

AR Credits are payments that originate from credit memos rather than actual payments.
In WC3, handle via `payment_type` field or separate Credit model.

### Late Charges

Late charges increase AR balance. WC2 used `docType=-28` in Ledger.
In WC3, consider:
- Creating as Invoice with special type
- Or as Payment with negative effect (requires careful handling)

### Split Payment Terms

Already supported via `terms_ledger.py`:
- `compute_schedule()` handles `period_count > 1`
- Creates multiple `ScheduleEntry` objects with staggered due dates
- Applies early payment discount to first installment only

---

## Migration Path

### Already Completed ✅
1. ✅ `OrgBase.financial` JSONB with customer aging/balances structure
2. ✅ `Payment`, `Invoice`, `Ledger` models defined
3. ✅ `PaymentApplication` junction model for tracking
4. ✅ `payment_application.py` - Core apply/unapply functions
5. ✅ `ledger_balance.py` - Aging calculation, balance updates, reconciliation
6. ✅ `terms_ledger.py` - Payment schedule from terms
7. ✅ `Payment.invoice_id` made nullable to support order-level deposits
8. ✅ `PaymentMethod` table seeded (Cash, Check, Credit Card, ACH, Wire Transfer, PayPal)
9. ✅ Frontend: `usePaymentApplication` hook for API operations
10. ✅ Frontend: `ApplyPaymentModal` component for InvoiceDetail
11. ✅ Frontend: `ApplyPayments` page for bulk payment application
12. ✅ Frontend: `AddPaymentModal` component for OrderDetail deposits
13. ✅ InvoiceDetail "Apply Payment" button (shows when balance_due > 0)
14. ✅ OrderDetail "Add Payment" button for order-level deposits
15. ✅ Route configured: `/transactions/apply-payments`

### Remaining Work
1. **Add auto-apply function** to `payment_application.py` backend
2. **Add AR Credit / Late Charge support** if needed
3. **Add paid days calculation** and update customer metrics
4. **Verify signal connections** for ledger sync on save
5. ~~**Frontend**: Payment application UI in React~~ ✅ COMPLETED
6. **Data migration**: Import WC2 ledger data if needed

---

## Frontend Implementation ✅ COMPLETED

### 1. InvoiceDetail.tsx Enhancement ✅

**Status:** Implemented - "Apply Payment" button shows in Quick Actions when `balance_due > 0`

**Files:**
- `React2025/src/apps/transactions/models/invoice/pages/InvoiceDetail.tsx` - Added button and modal integration
- `React2025/src/apps/transactions/components/ApplyPaymentModal.tsx` - Payment selection modal
- `React2025/src/apps/transactions/hooks/usePaymentApplication.ts` - Shared API hook

Originally planned:

**Location:** [InvoiceDetail.tsx](../../React2025/src/apps/transactions/models/invoice/pages/InvoiceDetail.tsx#L349-L359)

```tsx
// Add to Quick Actions section after Print/Email buttons
{data.balance_due && data.balance_due > 0 && (
  <button 
    onClick={() => openApplyPaymentModal(data)}
    className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors flex items-center gap-2"
  >
    <FaDollarSign size={14} />
    Apply Payment
  </button>
)}
```

**Apply Payment Modal Features:** ✅ All implemented
- Show invoice details (number, total, balance due) ✅
- List available payments for this customer (amount_available > 0) ✅
- Allow selecting payment and entering amount to apply ✅
- Call `apply_payment_to_invoice` API endpoint ✅
- Refresh invoice data after successful application ✅

### 1.5 OrderDetail.tsx Add Payment ✅ NEW

**Status:** Implemented - "Add Payment" button in Quick Actions for recording order-level deposits

**Files:**
- `React2025/src/apps/transactions/models/order/pages/OrderDetail.tsx` - Added button and modal integration  
- `React2025/src/apps/transactions/components/AddPaymentModal.tsx` - Payment entry modal

**Use Case:** Customers sometimes pay at order time (deposit, prepayment). These payments are recorded against the order (`refs.order_ids`) without an invoice, then later applied when the invoice ships.

**AddPaymentModal Features:**
- Amount input (defaults to order total)
- Payment method dropdown (from PaymentMethod table)
- Payment date picker  
- Reference/check number field
- Notes field
- Creates Payment with `refs.order_ids = [orderId]` and `invoice_id = null`

### 2. ApplyPayments Page (Bulk Application) ✅

**Status:** Implemented at `React2025/src/apps/transactions/pages/ApplyPayments.tsx`

**Route:** `/transactions/apply-payments`

**Based on WC2 Form Structure:**

```
┌─────────────────────────────────────────────────────────────┐
│ Apply Payments                                    [Search]  │
├─────────────────────────────────────────────────────────────┤
│ Customer: [__________] Phone: [______] Acct: [____]         │
│ ☐ Show All (include zero balance)                           │
├─────────────────────────────────────────────────────────────┤
│ INVOICES (Unpaid)                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Invoice | Unpaid    | Total   | Days | Terms | Date    │ │
│ │ 12345   | $1,250.00 | $1,500  | 45   | N30   | 01/15   │ │
│ │ 12346   | $750.00   | $750    | 30   | N30   | 01/20   │ │
│ │ 12347   | $2,000.00 | $2,500  | 15   | N30   | 01/30   │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Selected: 2 invoices  Total: $2,000.00                      │
├─────────────────────────────────────────────────────────────┤
│ PAYMENTS (Available)                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Ref     | Available | Original | Date   | Type | Check │ │
│ │ PAY-101 | $1,500.00 | $2,000   | 02/01  | Chk  | 4567  │ │
│ │ PAY-102 | $500.00   | $500     | 02/05  | ACH  |       │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Selected: PAY-101  Available: $1,500.00                     │
├─────────────────────────────────────────────────────────────┤
│ Apply Amount: [$1,500.00]                                   │
│ Remaining:    $500.00 (invoice) / $0.00 (payment)          │
│                                                             │
│ [Apply to Selected] [Auto-Apply Oldest] [Cancel]            │
└─────────────────────────────────────────────────────────────┘
```

**WC2 Column Mapping:**

| WC2 Invoice Array | React Column | Description |
|-------------------|--------------|-------------|
| aInvoices | ida | Invoice number |
| aUnPaid | balance_due | Unpaid amount |
| aInvTotals | totals.total | Invoice total |
| aInvDays | days_overdue | Days past due |
| aInvTerms | terms | Payment terms |
| aInvDate | dt | Invoice date |
| aCustPO | po_number | Customer PO |

| WC2 Payment Array | React Column | Description |
|-------------------|--------------|-------------|
| aPayments | amount_available | Available to apply |
| aPayOrig | amount | Original amount |
| aPayDate | date | Payment date |
| aPayType | payment_type | Check/ACH/Credit |
| aPayCom | reference_number | Check number |

**Key Actions:**
1. **Apply to Selected** - Apply selected payment to selected invoice(s)
2. **Auto-Apply Oldest** - Apply payment to oldest invoices first (calls `apply_payment_to_oldest_invoices`)
3. **Quick Apply** - Double-click invoice to apply selected payment

### 3. API Endpoints Required

```typescript
// src/apps/transactions/api/paymentApi.ts

// Apply payment to specific invoice
POST /api/transactions/payments/{id}/apply/
Body: { invoice_id: number, amount?: number }

// Auto-apply to oldest invoices  
POST /api/transactions/payments/{id}/auto-apply/

// Get available payments for customer
GET /api/transactions/payments/?org_id={id}&has_available=true

// Get unpaid invoices for customer
GET /api/transactions/invoices/?org_id={id}&status=unpaid
```

### 4. Component Structure ✅ IMPLEMENTED

```
src/apps/transactions/
├── pages/
│   └── ApplyPayments.tsx          # ✅ Main bulk application page
├── components/
│   ├── ApplyPaymentModal.tsx      # ✅ Modal for single invoice application  
│   ├── AddPaymentModal.tsx        # ✅ Modal for order-level deposits
│   └── index.ts                   # ✅ Exports both modals
└── hooks/
    └── usePaymentApplication.ts   # ✅ Shared logic for applying payments
```

**Note:** `InvoiceListForPayment.tsx` and `PaymentListAvailable.tsx` were combined into `ApplyPayments.tsx` as inline components for simplicity.

---

## Reference: WC3 Existing Services

| Service | Location | Purpose |
|---------|----------|---------|
| Payment Application | `apps/transactions/services/payment_application.py` | Apply/unapply payments to invoices |
| Ledger Balance | `apps/accounts/services/ledger_balance.py` | Aging calculation, balance updates |
| Terms Ledger | `apps/accounts/services/terms_ledger.py` | Payment schedule from terms |
| OrgBase.financial | `apps/orgs/models/constants.py` | Customer financial JSONB structure |

## Reference: WC2 ApplyPayments Form

**Location:** `00WebClerk19/Project/Sources/Forms/ApplyPayments/`

**Form Layout:**
- Two listboxes: Invoices (top) and Payments (bottom)
- Customer search filters (Customer, Phone, Acct, Division)
- Checkbox to show all vs only unpaid
- Action buttons for applying payments

**Invoice Listbox Arrays:**
- `aInvoices` - Invoice number
- `aUnPaid` - Unpaid amount (balance due)
- `aInvDiscountAmounts` - Available discount
- `aInvTotals` - Invoice total
- `aInvDays` - Days since invoice
- `aInvTerms` - Payment terms
- `aInvDate` - Invoice date
- `aIvcProfile` / `aIvcProfile2` - Profile info
- `aCustPO` - Customer PO
- `aInvDisApp` - Discount applied
- `aOrders` - Related order

**Payment Listbox Arrays:**
- `aPayInvs` - Reference invoice
- `aPayments` - Amount available
- `aPayOrig` - Original amount
- `aPayDate` - Payment date
- `aPayType` - Payment type
- `aPayCom` - Comments/check number
- `aPayOrds` - Reference order
- `aPayCust` - Customer
- `aPayRecs` - Record count
- `aidPayment` - Payment ID

**Key Methods:**
- `LBInvoiceArrays.4dm` - Invoice selection handler
- `LBPaymentArrays.4dm` - Payment selection handler
- `Variable3.4dm` - Apply to selected (single or multiple)
- `Variable4.4dm` - Apply single
- `Variable19.4dm` - Refresh payments query
- `Variable20.4dm` - Refresh invoices query
- `Variable21.4dm` - Filter by customer

## Reference: WC2 Source Files

| File | Purpose |
|------|---------|
| PayApply.4dm | Opens payment application dialog |
| PayApplyIvc.4dm | Loops through payments to apply |
| PayApplyOneInvoice.4dm | Core single-invoice application logic |
| Ledger_PaySave.4dm | Creates/updates payment ledger entry |
| Ledger_InvSave.4dm | Creates/updates invoice ledger entry |
| Ledger_TallyBal.4dm | Calculates aging buckets |
| Ledger_RayInit.4dm | Array init and batch save |
| Ledger_ThisCustomer.4dm | Rebuilds customer ledger |
| TransAct_Create.4dm | Creates DCash audit records |
| Pay_Main.4dm | Main payment creation |
| PayAddCredit.4dm | Creates AR Credit payments |
| LateCharges.4dm | Creates finance charges |
| Invc_DateDue.4dm | Calculates due date from terms |
| PaidDaysCalc.4dm | Calculates days to payment |
