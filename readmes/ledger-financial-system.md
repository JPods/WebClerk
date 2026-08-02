# Ledger System & Financial Data Management

> **Pending Policy:** All cash/payment balance changes and GL postings create a
> Pending record — always, even if the record is unlocked. See `readmes/pending-policy.md` Rule 1.

## Overview

The ledger system provides real-time tracking of customer, vendor, manufacturer, rep, and employee financial data. It uses a **hybrid approach** combining real-time pending records for operational data with batch processing for aggregate metrics.

## Profit And Loss Category For Unhappiness Cost

We will create a Profit and Loss category for agent unhappiness cost.

The reporting payload should be stored as a JSONB object so the system can preserve a comparable core while allowing the defect evidence and rubric details to evolve over time.

Purpose:
- give Alice a standard accounting bucket for happiness reporting by agent
- let unhappiness appear as a visible operating cost in monthly review
- keep the `$1,000` per point gap rule attached to a clear financial category
- avoid freezing the reporting shape too early when the agents are still learning how to describe their own defects

Expected fields for each reporting item:
- `category = profit_and_loss`
- `subcategory = unhappiness_cost`
- `agent`
- `group`
- `period`
- `happiness`
- `unhappiness_gap`
- `cost_method = agent_estimate | proxy_scale`
- `estimated_unhappiness_cost_monthly_usd`
- `scaled_defect_cost_monthly_usd`
- `unhappiness_cost_monthly_usd`
- `background`
- `rubric_version`

Recommended storage rule:
- stable reporting keys stay queryable at the top level of the JSONB object
- background evidence remains as arrays/objects inside JSONB
- group-specific extensions are allowed without requiring new columns for each new lesson learned

If the agent can estimate its own monthly dollar impact credibly, preserve that estimate as the primary cost.

If it cannot, use the fallback scaled defect cost:

$$
scaled\_defect\_cost\_monthly\_usd = (10 - happiness) \times 1000
$$

This follows the same management logic as Small Stings: a defect still deserves a scale even when exact dollars are not yet known.

This does not claim GAAP precision. It is a management accounting signal for the cost of recurring friction and low happiness across agents.

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

### Status: WIRED & TESTED (March 2026)

The ledger pipeline is fully wired into the save chain:

| Trigger | Entry Point | File |
|---------|-------------|------|
| Invoice save | Phase 5 of `save_transaction_with_lines()` | `apps/transactions/services/transaction_save.py` |
| Payment save | `post_save` signal `create_payment_ledger` | `apps/transactions/signals.py` |

### Ledger Model (current)

```python
# apps/accounts/models/ledger.py
class Ledger(BaseModel):
    discount_potential = models.DecimalField(max_digits=10, decimal_places=4)
    dt_discount_due = models.DateTimeField()
    dt_due = models.DateTimeField()
    dt_posted = models.DateTimeField()
    dt_recorded = models.DateTimeField()
    dt_settled = models.DateTimeField()
    is_settled = models.BooleanField(default=False)
    is_cleared = models.BooleanField(default=False)
    is_void = models.BooleanField(default=False)
    source = models.CharField(choices=LEDGER_SOURCE_CHOICES)
    model_name = models.CharField(choices=LEDGER_MODEL_CHOICES)
    parent_id = models.BigIntegerField(db_index=True)
    org = models.ForeignKey('orgs.OrgBase', on_delete=SET_NULL)      # ← NEW: indexed FK
    invoice = models.ForeignKey('transactions.Invoice', on_delete=SET_NULL)
    term = models.ForeignKey('accounts.Term', on_delete=SET_NULL)
    gl_account = models.ForeignKey('accounts.GlAccount', on_delete=SET_NULL)
    value_available = models.DecimalField(max_digits=12, decimal_places=2)  # ← was FloatField
    value_original = models.DecimalField(max_digits=12, decimal_places=2)   # ← was FloatField
```

**Composite indexes** for fast aging:
- `idx_ledger_org_model` → `(org, model_name)`
- `idx_ledger_org_due` → `(org, dt_due)`

**Migration**: `0004_add_org_fk_and_decimal_fields_to_ledger`

### Pipeline Wiring

#### Invoice → Ledger (Phase 5 in transaction_save.py)

```python
# After Phase 4 (pending dispatch), guarded by model_key == 'invoice':
from apps.accounts.services.ledger_balance import on_invoice_save
on_invoice_save(header_obj, replace_ledgers=True)
```

`on_invoice_save()` now follows a **5-step pipeline with Pending-based sync**:

1. Resolve term → call `apply_terms_for_invoice()` → call `create_ledger_records()`
2. Stamp `invoice.metadata.ledger` with entries + `dt_sync=0` (not yet confirmed)
3. Create a Pending record with `purpose='ledger_sync'` (command object)
4. Attempt `update_org_balances(org)`
5. On success → stamp `dt_sync=now`, mark Pending processed
   On failure → both remain unprocessed for Celery retry

**Self-diagnosing metadata** (`invoice.metadata.ledger`):
```json
{
    "entries": [
        {"ledger_id": 42, "value_original": 500.0, "value_available": 500.0, "dt_due": 1741564800000}
    ],
    "total_original": 500.0,
    "dt_sync": 1741478400000
}
```

| `dt_sync` State | Meaning | Action |
|-----------------|---------|--------|
| `> 0` | Fully synced | None needed |
| `= 0` | Ledger records exist but org balance unconfirmed | `ledger_sync_processor` retries |
| Key absent | Ledger write itself may have failed | Full re-run via `on_invoice_save` |

**Ledger sync processor**: `apps/accounts/services/ledger_sync_processor.py` handles Celery retries.

See `readmes/topics/architecture/pending-compensating-transactions.md` for the full Pending pattern.

#### Payment → Ledger (post_save signal)

```python
# apps/transactions/signals.py
@receiver(post_save, sender=Payment)
def create_payment_ledger(sender, instance, **kwargs):
    from apps.accounts.services.ledger_balance import on_payment_save
    on_payment_save(instance)
```

`on_payment_save()` calls `record_payment()` → creates negative ledger → calls `update_org_balances()`.

### Total Resolution

`TransactionBaseModel` has two total-related fields:
- `total` — `DecimalField` (denormalized scalar for indexing)
- `totals` — `JSONField` (dict with subtotal, discount, tax, shipping, total, cost, margin)

`apply_terms_for_invoice()` resolves the total by:
1. Trying `invoice.total` (DecimalField scalar) first
2. Falling back to `invoice.totals['total']` (JSONField dict)
3. Last resort: calling `compute_line_aggregate()` to sum lines

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

---

## Test Suite

```bash
cd webClerk3
python -m pytest apps/accounts/tests/test_ledger.py -v --no-header -o "addopts="
```

15 tests across 5 classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestComputeSchedule` | 4 | Single, multi-period, discount, epoch-ms dates |
| `TestCreateLedgerRecords` | 5 | Create, multi-period split, replace, no-term, name-fallback |
| `TestPaymentLedger` | 1 | Negative-value ledger creation |
| `TestAgingBuckets` | 3 | Current bucket, past-due bucket, payment reduces balance |
| `TestOnInvoiceSave` | 2 | Full pipeline + org balance update, idempotent re-save |

---

## Implementation Changelog

### March 2026 — Wiring & Bug Fixes

**Model changes** (`ledger.py`):
- Added `org` FK to `OrgBase` for indexed aging queries (replaces JSON-path lookups)
- Converted `discount_potential`, `value_available`, `value_original` from `FloatField` → `DecimalField`
- Added `is_cleared`, `is_void` boolean fields
- Added composite indexes `idx_ledger_org_model`, `idx_ledger_org_due`
- Migration: `0004_add_org_fk_and_decimal_fields_to_ledger`
- Registered `Ledger` in `apps/accounts/models/__init__.py`

**Bug fixes** (`terms_ledger.py`):
- Fixed metadata strategy referencing undefined `invoice` instead of `invoice_id` param
- Added `org_id` population in both `create_ledger_records()` and `record_payment()`
- Fixed total resolution to handle `total` (DecimalField scalar) vs `totals` (JSONField dict)

**Bug fixes** (`ledger_balance.py`):
- Fixed org lookup: `invoice.org` → `invoice.customer` (actual FK name)
- Fixed payment field: `amount_available` → `amount` (actual field name)
- Updated aging queries to use `org_id` FK instead of JSON-path `refs__links__org__id`
- Fixed `reconcile_org` and `rebuild_org_ledgers` to use `customer_id` / `invoice__customer_id`

**Pipeline wiring**:
- Added Phase 5 to `transaction_save.py` — calls `on_invoice_save()` after invoice saves
- Added `post_save` signal on `Payment` in `signals.py` — calls `on_payment_save()`

**Tests** (`apps/accounts/tests/test_ledger.py`):
- 15 tests covering schedule computation, ledger creation, payment ledgers, aging buckets, and full pipeline
