# Ledger System & Financial Data Management

## Overview

The ledger system provides real-time tracking of customer, vendor, manufacturer, rep, and employee financial data. It uses a **hybrid approach** combining real-time pending records for operational data with batch processing for aggregate metrics.

## Implementation Files

### Django (webClerk3)
- `apps/accounts/models/ledger.py` - Ledger model
- `apps/accounts/services/terms_ledger.py` - Term schedule calculation and ledger creation
- `apps/accounts/services/ledger_balance.py` - Real-time balance updates
- `apps/accounts/management/commands/reconcile_financials.py` - Nightly batch reconciliation

### 4D (WebClerk19)
- `Ledger_InvSave.4dm` - Invoice ledger creation
- `Ledger_PaySave.4dm` - Payment ledger creation
- `Ledger_TallyBal.4dm` - Balance calculation
- `Ledger_CheckCustomers.4dm` - Validation

---

## Hybrid Approach

### Real-Time (Pending Records)
These metrics update immediately when transactions are saved:

| Metric | Trigger | Reason |
|--------|---------|--------|
| Credit available | Invoice/Payment save | Prevents over-limit orders |
| Balance due | Invoice/Payment save | Operational decision-making |
| Hold status | Manual or threshold | Blocks transactions |
| COD flag | Credit events | Payment requirement |
| Aging buckets | Ledger date comparison | Collection priority |

### Batch (Nightly)
These metrics are recalculated during scheduled processing:

| Metric | Frequency | Reason |
|--------|-----------|--------|
| YTD sales/purchases | Daily | Informational only |
| Margin % | Daily | Historical calculation |
| High credit mark | Daily | Tracking metric |
| Reconciliation totals | Daily | Data integrity check |

### Why Hybrid?

1. **Credit/balance data is operationally critical** — day-old balance could allow bad orders or wrongly block good customers
2. **Aggregates are informational** — users don't make blocking decisions based on YTD sales
3. **Pending records are complex** — limit complexity to where it matters
4. **Nightly batch serves as reconciliation** — catches any drift in pending calculations

---

## Ledger Record System

### Invoice Aging via Ledger Records

When an invoice is saved, **one or more ledger records are created** based on the payment terms configuration:

| Term Setting | Purpose |
|--------------|---------|
| `period_count` | Number of ledger records to create (payment installments) |
| `days_due` | Days until payment due (single payment terms) |
| `days_in_period` | Days between due dates for each period |
| `dt_begin` | Fixed start date (overrides invoice date when set) |
| `discount_rate` | Early payment discount percentage |
| `days_discount` | Days within which discount applies |

#### Example: Net 30 Terms
- `period_count = 1` → Single ledger record
- Due date = Invoice date + 30 days

#### Example: 3-Pay Terms (90 days split)
- `period_count = 3` → Three ledger records created
- `days_in_period = 30` → Each 30 days apart
- Invoice total split across three records with staggered due dates

#### Example: Fixed Date Term ("Due Dec 15")
- `dt_begin = 2025-12-15` → Schedule starts from this date, NOT invoice date
- `period_count = 1, days_due = 0` → Due exactly on Dec 15
- Use case: Seasonal billing, trade show terms, contract milestones

#### Example: Fixed Date Multi-Pay ("3 payments starting Dec 12")
- `dt_begin = 2025-12-12, period_count = 3, days_in_period = 30`
- Due dates: Jan 11, Feb 10, Mar 12 (regardless of invoice date)

### Ledger Record Structure

```
Ledger
├── customerID      → Links to org
├── idForeign       → Links to source document (Invoice/Payment ID)
├── tableName       → "Invoice" or "Payment"
├── tableNum        → 26 (Invoice) or 28 (Payment)
├── docRefid        → Document reference number
├── dateDue         → When this amount is due
├── dateDocument    → Original document date
├── unAppliedValue  → Current unapplied balance (+ for invoices, - for payments)
├── origValue       → Original amount
├── discntPotential → Potential early payment discount
├── expireDate      → Discount expiration date
└── terms           → Payment terms code
```

### Aging Bucket Calculation

Ledger records are aged by comparing `dateDue` to current date:

```
Future:     dateDue > currentDate + 30 days
Current:    dateDue > currentDate (not past due)
Period 1:   currentDate - 30 < dateDue ≤ currentDate (1-30 days past)
Period 2:   currentDate - 60 < dateDue ≤ currentDate - 30 (31-60 days past)
Period 3:   dateDue ≤ currentDate - 60 (over 60 days past)
```

Customer balance fields updated:
- `futureDue` — Future amounts
- `balanceCurrent` — Not past due
- `balPastPeriod1` — 1-30 days past due
- `balPastPeriod2` — 31-60 days past due
- `balPastPeriod3` — Over 60 days past due
- `balanceDue` — Total of all buckets

---

## 4D Method Reference

### Core Ledger Methods

| Method | Purpose |
|--------|---------|
| `Ledger_InvSave` | Creates ledger records when invoice is saved. Splits by `period_count`, calculates due dates, handles discounts. |
| `Ledger_PaySave` | Creates negative ledger record when payment is saved. Handles late payment fees. |
| `Ledger_RayInit` | Array management for batch ledger creation. Pass count to initialize, -3 to save records. |
| `Ledger_TallyBal` | Recalculates all aging buckets for a customer from their ledger records. |
| `Ledger_ThisCustomer` | Rebuilds all ledgers for a single customer (drops and recreates from invoices/payments). |

### Validation & Maintenance

| Method | Purpose |
|--------|---------|
| `Ledger_CheckCustomers` | Validates ledger totals match invoice - payment totals for all customers. Flags mismatches. |
| `Ledger_CustomersSelect` | Batch reledger for a selection of customers with progress tracking. |
| `Ledger_InvSet` | Regenerates ledgers for all invoices in current selection. |
| `LedgerScrub` | Finds payments without matching ledger records or with mismatched amounts. |

---

## Implementation in webClerk3

### Ledger Model (existing)

```python
# apps/accounts/models/ledger.py
class Ledger(BaseModel):
    discount_potential = models.FloatField(blank=True, null=True)
    dt_discount_due = models.DateTimeField(blank=True, null=True)
    dt_due = models.DateTimeField(blank=True, null=True)
    dt_posted = models.DateTimeField(blank=True, null=True)
    dt_recorded = models.DateTimeField(blank=True, null=True)
    dt_settled = models.DateTimeField(blank=True, null=True)
    is_settled = models.BooleanField(default=False)
    source = models.CharField(max_length=255, choices=LEDGER_SOURCE_CHOICES)
    model_name = models.CharField(max_length=255, choices=LEDGER_MODEL_CHOICES)
    parent_id = models.BigIntegerField(db_index=True)  # Source document ID
    invoice_id = models.ForeignKey('transactions.Invoice', on_delete=models.SET_NULL)
    term_id = models.ForeignKey('accounts.Term', on_delete=models.SET_NULL)
    value_available = models.FloatField()  # Current unapplied balance
    value_original = models.FloatField()   # Original amount
```

### Service Functions

```python
# apps/accounts/services/ledger_balance.py

# Real-time: Called after invoice/payment save
def on_invoice_save(invoice, replace_ledgers=True):
    """Create ledger records and update org balances."""
    
def on_payment_save(payment):
    """Create payment ledger and update org balances."""

def update_org_balances(org, save=True):
    """Recalculate aging buckets and update org.financial."""

# Batch: Called during nightly reconciliation
def reconcile_org(org):
    """Full validation and recalculation for an org."""
    
def rebuild_org_ledgers(org):
    """Delete and recreate all ledgers from source documents."""
```

### Management Command

```bash
# Nightly reconciliation
python manage.py reconcile_financials

# Single org
python manage.py reconcile_financials --org-id=<id>

# Rebuild all ledgers (destructive)
python manage.py reconcile_financials --rebuild

# Check without changes
python manage.py reconcile_financials --dry-run

# Include YTD recalculation
python manage.py reconcile_financials --update-ytd
```

---

## Data Flow

```
Invoice Saved
    │
    ├─► Delete existing ledger records for invoice
    │
    ├─► Look up payment terms
    │       │
    │       └─► Get period_count, days_in_period, discount settings
    │
    ├─► Create ledger record(s)
    │       │
    │       ├─► Split total by period_count
    │       ├─► Calculate due dates (staggered by days_in_period)
    │       ├─► Apply partial payments to earliest periods first
    │       └─► Set discount potential and expiration
    │
    └─► Update org financial fields
            │
            ├─► Sum ledger unapplied_value by aging bucket
            ├─► Update balance_due, balance_current
            ├─► Update aging period fields
            └─► Check/update credit available
```

---

## Validation Rules

1. **Ledger Sum = Invoice Balance - Payment Available**
   - `Ledger_CheckCustomers` validates this for all orgs
   - Mismatches indicate data corruption or missed updates

2. **Every Invoice/Payment has Ledger Records**
   - Exception: Paid invoices older than 120 days (configurable)
   - Exception: Incomplete journal entries (linked-only mode)

3. **Aging Buckets Sum to Balance Due**
   - `future + current + period1 + period2 + period3 = balance_due`

---

## Configuration

### Payment Terms Array (4D)
```
<>aTerms[]           — Term codes (e.g., "Net30", "2/10Net30")
<>aTermPrdCnt[]      — Period count per term
<>aTermPrdLen[]      — Days per period
<>aTermDctRt[]       — Discount rate percentage
<>aTermDctDay[]      — Days for discount eligibility
```

### Django Settings
```python
LEDGER_SETTINGS = {
    'KEEP_PAID_DAYS': 120,      # Days to keep ledgers for paid invoices
    'LINKED_ONLY': False,        # Only process journal-linked documents
    'DEFAULT_PERIODS': 30,       # Default days per aging period
}
```

### Term Model Fields

The `Term` model (`apps/accounts/models/term.py`) configures payment schedules:

| Field | Type | Purpose |
|-------|------|---------|  
| `name` | CharField | Term code (e.g., 'N30', '2%', 'COD') |
| `description` | CharField | Human-readable name |
| `period_count` | Integer | Number of payment installments |
| `days_due` | Integer | Days until due (single payment) |
| `days_in_period` | Integer | Days between installments |
| `dt_begin` | Date | **Fixed start date** (overrides invoice date) |
| `discount_rate` | Float | Early payment discount % |
| `days_discount` | Integer | Days for discount eligibility |
| `day_cut_off_invoice` | Integer | Statement cycle invoice cutoff |
| `day_cut_off_due` | Integer | Statement cycle due date cutoff |

**Base Date Logic** (in `compute_schedule()`):
- Default: Uses invoice date as base for due date calculation
- Override: If `term.dt_begin` is set, uses that fixed date instead
- Use case: Seasonal billing, trade show terms, contract milestones

---

## Audit Guide

This section provides procedures for auditors verifying financial data integrity.

### Balance Verification Queries

```sql
-- Verify org balance matches ledger sum
SELECT 
    o.id,
    o.name,
    o.balance_due as reported_balance,
    COALESCE(SUM(l.value_available), 0) as ledger_sum,
    o.balance_due - COALESCE(SUM(l.value_available), 0) as variance
FROM org o
LEFT JOIN ledger l ON l.org_id = o.id
WHERE o.balance_due != 0
GROUP BY o.id, o.name, o.balance_due
HAVING ABS(o.balance_due - COALESCE(SUM(l.value_available), 0)) > 0.01;

-- Verify aging bucket sum equals balance_due
SELECT 
    id,
    name,
    balance_due,
    (aging_future + aging_current + aging_period_1 + aging_period_2 + aging_period_3) as bucket_sum,
    balance_due - (aging_future + aging_current + aging_period_1 + aging_period_2 + aging_period_3) as variance
FROM org
WHERE ABS(balance_due - (aging_future + aging_current + aging_period_1 + aging_period_2 + aging_period_3)) > 0.01;
```

### Discrepancy Investigation

When variances are found:

1. **Missing Ledger Records**
   - Check if invoice has corresponding ledgers: `SELECT * FROM ledger WHERE invoice_id = ?`
   - If missing, invoice may have been saved without term processing
   - Resolution: Call `apply_terms_for_invoice(invoice, replace=True)`

2. **Orphan Ledger Records**
   - Check for ledgers without valid invoice: `SELECT l.* FROM ledger l LEFT JOIN invoice i ON l.invoice_id = i.id WHERE i.id IS NULL`
   - May indicate deleted invoice without cascade
   - Resolution: Delete orphan ledger records

3. **Payment Not Applied**
   - Check payment ledgers exist: `SELECT * FROM ledger WHERE model_name='payment'`
   - Verify value_available is negative
   - Check payment settlement status

4. **Running Full Reconciliation**
   ```bash
   # Dry run to identify issues
   python manage.py reconcile_financials --dry-run
   
   # Fix discrepancies
   python manage.py reconcile_financials
   
   # Nuclear option: rebuild all ledgers from source documents
   python manage.py reconcile_financials --rebuild
   ```

### Audit Trail Fields

Every Ledger record maintains:

| Field | Purpose |
|-------|---------|
| `dt_created` | When record was created (auto) |
| `dt_modified` | Last modification (auto) |
| `dt_recorded` | Business date of transaction |
| `dt_posted` | Accounting period posting date |
| `value_original` | Initial value (immutable) |
| `value_available` | Current unpaid/unallocated |
| `parent_id` | Source document ID |
| `model_name` | Source document type |
| `invoice_id` | FK to invoice |
| `term_id` | FK to payment terms |
| `refs` | JSON with additional linkage |

### Sign Convention

Understanding the sign convention is critical for auditing:

| Transaction | value_original | Effect on Balance |
|-------------|----------------|-------------------|
| Invoice | POSITIVE | Increases A/R |
| Payment | NEGATIVE | Decreases A/R |
| Credit Memo | NEGATIVE | Decreases A/R |
| Debit Memo | POSITIVE | Increases A/R |

**Validation Rule**: For a fully paid invoice, `SUM(ledger.value_available WHERE invoice_id = X) = 0`

### Monthly Audit Checklist

- [ ] Run reconciliation: `reconcile_financials --dry-run`
- [ ] Verify no orphan ledgers
- [ ] Verify aging buckets sum to balance_due for all orgs
- [ ] Spot-check 5-10 customers: ledger sum matches balance_due
- [ ] Verify YTD totals: `reconnect_financials --update-ytd`
- [ ] Review large balance changes month-over-month
- [ ] Check for negative balance_due (credit balances) - should match prepayments

### Code Entry Points for Investigation

| Scenario | Function | File |
|----------|----------|------|
| Schedule calculation | `compute_schedule()` | `terms_ledger.py` |
| Invoice ledger creation | `create_ledger_records()` | `terms_ledger.py` |
| Payment application | `record_payment()` | `terms_ledger.py` |
| Balance update | `update_org_balances()` | `ledger_balance.py` |
| Aging calculation | `calculate_aging_buckets()` | `ledger_balance.py` |
| Full reconciliation | `reconcile_org()` | `ledger_balance.py` |
| Nightly batch | `reconcile_financials` | management command |
