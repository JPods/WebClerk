"""
Terms Ledger Service
====================

AUDIT DOCUMENTATION
-------------------
This module handles payment schedule calculation and ledger record creation.
It translates payment terms (Net 30, 2/10 Net 30, etc.) into concrete ledger
records with specific due dates and discount opportunities.

KEY CONCEPTS:

1. PAYMENT TERMS → SCHEDULE → LEDGER RECORDS
   - Term defines: period_count, days_due, days_in_period, discount
   - Schedule splits invoice into dated installments
   - Ledger records track each installment's due amount and status

2. LEDGER VALUE CONVENTION
   - Invoice ledgers: POSITIVE values (money owed to company)
   - Payment ledgers: NEGATIVE values (money received from customer)
   - Net sum = Current receivables balance

3. MULTI-INSTALLMENT HANDLING
   - period_count > 1 splits invoice into equal parts
   - days_in_period staggers due dates
   - Rounding adjustment applied to last installment

4. EARLY PAYMENT DISCOUNT
   - discount_rate: Percentage discount (e.g., 0.02 = 2%)
   - days_discount: Days from invoice date discount is valid
   - Only applied to first installment of multi-pay terms

AUDIT TRAIL:
- Each ledger links to source invoice via invoice_id FK and parent_id
- Each ledger links to term via term_id FK
- value_original captures initial amount (never changes)
- value_available tracks current unpaid balance (decreases with payments)
- refs JSON captures additional relationship metadata

FINANCIAL COMPLIANCE:
- All monetary calculations use Decimal for precision
- Schedule shares must sum to exactly 1.0 (100%)
- Rounding differences go to last installment
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional


@dataclass
class ScheduleEntry:
    """
    A single installment in a payment schedule.
    
    AUDIT: This represents one ledger record to be created.
    - due: When this installment is due
    - share: Fraction of total (0-1), must sum to 1.0 across all entries
    - discount_due: Optional discount expiration date
    - discount_rate: Optional discount percentage (e.g., 0.02 = 2%)
    """
    due: datetime
    share: Decimal  # fraction of total (0-1)
    discount_due: Optional[datetime] = None
    discount_rate: Optional[Decimal] = None  # 0.02 for 2%


def compute_schedule(invoice_dt: datetime, total: Decimal, term) -> List[ScheduleEntry]:
    """
    Compute a payment schedule from a Term.
    
    AUDIT: This is the SCHEDULE CALCULATION function.
    It determines HOW MANY ledger records to create and WHEN each is due.
    
    BASE DATE SELECTION:
    - Default: Uses invoice_dt as the base for due date calculations
    - Override: If term.dt_begin is set, uses that fixed date instead
    - Use case: Terms like "Due Dec 8" or "3 payments starting Dec 12"
    
    CALCULATION RULES:
    
    1. SINGLE PAYMENT (period_count <= 1):
       - One entry with share=1.0
       - Due date = base_dt + days_due
       - discount if days_discount and discount_rate are set
       
    2. MULTI-INSTALLMENT (period_count > 1):
       - N entries, each with share = 1/N
       - Due dates staggered by days_in_period
       - Discount only on first installment
       - Last share adjusted for rounding
    
    EXAMPLE: Net 30
    - period_count=1, days_due=30
    - Result: [ScheduleEntry(due=invoice_dt+30d, share=1.0)]
    
    EXAMPLE: 2/10 Net 30
    - period_count=1, days_due=30, days_discount=10, discount_rate=0.02
    - Result: [ScheduleEntry(due=invoice_dt+30d, share=1.0, 
                             discount_due=invoice_dt+10d, discount_rate=0.02)]
    
    EXAMPLE: 3-Pay Net 90
    - period_count=3, days_in_period=30
    - Result: [
        ScheduleEntry(due=invoice_dt+30d, share=0.3333),
        ScheduleEntry(due=invoice_dt+60d, share=0.3333),
        ScheduleEntry(due=invoice_dt+90d, share=0.3334)  # rounding adjustment
      ]
    
    EXAMPLE: Fixed date term (dt_begin=2008-12-12, period_count=3, days_in_period=30)
    - Result: [
        ScheduleEntry(due=2009-01-11, share=0.3333),
        ScheduleEntry(due=2009-02-10, share=0.3333),
        ScheduleEntry(due=2009-03-12, share=0.3334)
      ]
    
    Args:
        invoice_dt: Invoice date (fallback start of payment period)
        total: Invoice total (for documentation, not used in calculation)
        term: Term object with period_count, days_due, days_in_period, dt_begin, etc.
    
    Returns:
        List of ScheduleEntry objects defining the payment schedule
    """
    # Normalize dt to aware UTC; accept epoch seconds/ms as int/float
    if isinstance(invoice_dt, (int, float)):
        # Assume epoch milliseconds if large, else seconds
        try:
            num = float(invoice_dt)
            sec = (num / 1000.0) if num > 10_000_000 else num
            invoice_dt = datetime.fromtimestamp(sec, tz=timezone.utc)
        except Exception:
            invoice_dt = datetime.now(timezone.utc)
    # If naive datetime provided, force UTC
    if isinstance(invoice_dt, datetime) and invoice_dt.tzinfo is None:
        invoice_dt = invoice_dt.replace(tzinfo=timezone.utc)

    # AUDIT: Check for term-specific start date (dt_begin)
    # If term has dt_begin set, use it instead of invoice date for schedule calculation
    # This supports fixed-date terms like "Due Dec 8" or "3 payments starting Dec 12"
    base_dt = invoice_dt
    dt_begin = getattr(term, 'dt_begin', None)
    if dt_begin is not None:
        # Convert date to datetime at midnight UTC
        if isinstance(dt_begin, date) and not isinstance(dt_begin, datetime):
            base_dt = datetime.combine(dt_begin, datetime.min.time(), tzinfo=timezone.utc)
        else:
            base_dt = dt_begin
            if base_dt.tzinfo is None:
                base_dt = base_dt.replace(tzinfo=timezone.utc)

    period_count = getattr(term, 'period_count', None) or 1
    days_due = getattr(term, 'days_due', None) or 0
    days_in_period = getattr(term, 'days_in_period', None) or days_due or 30
    days_discount = getattr(term, 'days_discount', None)
    discount_rate = getattr(term, 'discount_rate', None)

    entries: List[ScheduleEntry] = []

    if period_count <= 1:
        due = base_dt + timedelta(days=days_due)
        disc_due = None
        disc_rate = None
        if days_discount and discount_rate:
            disc_due = base_dt + timedelta(days=days_discount)
            disc_rate = Decimal(str(discount_rate))
        entries.append(ScheduleEntry(due=due, share=Decimal('1'), discount_due=disc_due, discount_rate=disc_rate))
        return entries

    # Multi-installment
    share = (Decimal('1') / Decimal(str(period_count))).quantize(Decimal('0.0001'))
    for i in range(period_count):
        due = base_dt + timedelta(days=days_in_period * (i + 1))
        disc_due = None
        disc_rate = None
        if i == 0 and days_discount and discount_rate:
            disc_due = base_dt + timedelta(days=days_discount)
            disc_rate = Decimal(str(discount_rate))
        entries.append(ScheduleEntry(due=due, share=share, discount_due=disc_due, discount_rate=disc_rate))
    # Adjust last share to absorb rounding
    total_share = sum((e.share for e in entries), Decimal('0'))
    if total_share != Decimal('1'):
        diff = Decimal('1') - total_share
        entries[-1].share = (entries[-1].share + diff)
    return entries


def create_ledger_records(invoice_id, total: Decimal, term_id, strategy: str = 'records'):
    """
    Create ledgers for an invoice based on a term.
    
    AUDIT: This is the LEDGER CREATION function for invoices.
    It materializes a payment schedule into actual database records.
    
    WHAT GETS CREATED (strategy='records'):
    For each ScheduleEntry from compute_schedule():
    - One Ledger record with:
      - dt_due: When payment is due
      - dt_discount_due: When discount expires (if applicable)
      - discount_potential: Discount rate (e.g., 0.02)
      - value_original: Entry's share of total (immutable)
      - value_available: Same initially (decreases with payments)
      - parent_id: Invoice ID for audit trail
      - invoice_id: FK to Invoice for joins
      - term_id: FK to Term for audit trail
      - model_name: 'invoice' for type identification
      - source: 'AR' (Accounts Receivable)
      - refs: JSON with link metadata
    
    STRATEGY OPTIONS:
    - 'records': Create actual Ledger database records (default)
    - 'metadata': Store schedule in invoice.metadata only (no records)
    
    CONCURRENCY NOTE:
    This function does NOT handle concurrent access or payments.
    Caller should wrap in a transaction if needed.
    
    Args:
        invoice_id: Invoice instance to create ledgers for
        total: Invoice total in Decimal
        term_id: Term instance defining payment schedule
        strategy: 'records' to create Ledgers, 'metadata' to store in JSON
    
    Returns:
        List of created Ledger instances (empty if strategy='metadata')
    """
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')

    # AUDIT: Calculate invoice date from invoice or use current time
    # Accept epoch ms from API calls; normalize to UTC datetime
    inv_dt = getattr(invoice_id, 'dt_created', None)
    schedule = compute_schedule(inv_dt if inv_dt is not None else datetime.now(timezone.utc), total, term_id)
    created = []
    
    if strategy == 'metadata':
        # AUDIT: Alternative strategy - store schedule in invoice metadata
        # This avoids creating ledger records but loses aging tracking
        meta = getattr(invoice, 'metadata', {}) or {}
        terms_meta = meta.get('terms') or {}
        terms_meta['schedule'] = [
            {
                'due': int(e.due.timestamp()),
                'share': str(e.share),
                'discount_due': int(e.discount_due.timestamp()) if e.discount_due else None,
                'discount_rate': str(e.discount_rate) if e.discount_rate is not None else None,
            }
            for e in schedule
        ]
        meta['terms'] = terms_meta
        invoice_id.metadata = meta
        invoice_id.save(update_fields=['metadata'])
        return created

    # ==========================================================================
    # STRATEGY: 'records' - Create actual Ledger database records
    # ==========================================================================
    # AUDIT: Each schedule entry becomes one Ledger record
    # The refs JSON provides additional audit linkage
    for e in schedule:
        # AUDIT: Calculate this installment's value
        # value = total × share (e.g., $1000 × 0.3333 = $333.30)
        value = (total * e.share)
        
        # AUDIT: refs JSON captures relationship metadata for queries
        refs = {
            'links': {
                'parent': {'model': 'invoice', 'id': getattr(invoice_id, 'id')}
            }
        }
        
        # AUDIT: Create ledger with full audit trail
        obj = Ledger(
            dt_due=e.due,                          # When payment is due
            dt_discount_due=e.discount_due,        # When discount expires
            discount_potential=float(e.discount_rate) if e.discount_rate is not None else None,
            model_name='invoice',                  # Source document type
            source='AR',                           # Accounts Receivable
            parent_id=getattr(invoice_id, 'id'),   # Source document ID
            invoice_id=invoice_id,                 # FK for joins
            term_id=term_id,                       # FK for audit trail
            value_original=float(value),           # Initial amount (immutable)
            value_available=float(value),          # Current unpaid (mutable)
            refs=refs,                             # Additional metadata
        )
        obj.save()
        created.append(obj)
    return created


def apply_terms_for_invoice(invoice, total: Optional[Decimal] = None, term=None, strategy: str = 'records', replace: bool = False):
    """
    Idempotent helper to materialize ledgers when terms are present or applied.
    
    AUDIT: This is the HIGH-LEVEL API for invoice ledger creation.
    It handles term resolution, total calculation, and optional cleanup.
    
    IDEMPOTENCY:
    - If replace=True, deletes existing ledgers before creating new ones
    - Safe to call multiple times with replace=True
    
    TERM RESOLUTION (if term not provided):
    1. Check invoice.prefs.payment_terms.id → lookup Term by ID
    2. Check invoice.prefs.payment_terms.name → lookup Term by description
    3. If neither, returns empty list (no ledgers created)
    
    TOTAL RESOLUTION (if total not provided):
    1. Check invoice.total.total or invoice.total.amount
    2. Fallback: Aggregate invoice lines
    3. If still zero/negative, returns empty list
    
    Args:
        invoice: Invoice instance to process
        total: Optional Decimal total (calculated if not provided)
        term: Optional Term instance (resolved from invoice if not provided)
        strategy: 'records' or 'metadata' (passed to create_ledger_records)
        replace: If True, delete existing ledgers first
    
    Returns:
        List of created Ledger instances (may be empty)
    """
    from django.apps import apps as dj_apps
    from decimal import Decimal as D
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Term = dj_apps.get_model('accounts', 'Term')

    # AUDIT: Resolve payment term from invoice preferences if not provided
    if term is None:
        spec = (getattr(invoice, 'prefs', {}) or {}).get('payment_terms') or {}
        if isinstance(spec, dict):
            term_id = spec.get('id')
            term_name = spec.get('name')
            if term_id:
                term = Term.objects.filter(id=term_id).first()
            if term is None and term_name:
                term = Term.objects.filter(description__iexact=term_name).first()
    if term is None:
        return []

    # Resolve total
    if total is None:
        total_map = getattr(invoice, 'total', {}) or {}
        total_val = total_map.get('total') or total_map.get('amount') or 0
        try:
            total = D(str(total_val))
        except Exception:
            total = D('0')
        if total <= 0:
            from apps.transactions.aggregation import compute_line_aggregate
            agg = compute_line_aggregate(parent_id=getattr(invoice, 'id'), model_key='invoice-line')
            total = D(agg.get('total_price_extended', '0'))
            if total <= 0:
                return []

    # AUDIT: replace=True provides idempotency by clearing existing ledgers
    if replace:
        Ledger.objects.filter(invoice_id=getattr(invoice, 'id')).delete()

    return create_ledger_records(invoice_id=invoice, total=total, term_id=term, strategy=strategy)


def record_payment(invoice, amount: Decimal, dt_paid, payment=None, gl_account_id=None, source: str = 'AR'):
    """
    Create a payment ledger with NEGATIVE value to offset invoice ledgers.
    
    AUDIT: This creates the CounterbalancING side of the A/R ledger.
    
    ACCOUNTING PRINCIPLE:
    - Invoice ledgers have POSITIVE values (money owed TO us)
    - Payment ledgers have NEGATIVE values (money received FROM customer)
    - Sum of all ledgers = Current A/R balance
    
    Example:
    - Invoice for $1,000: Ledger.value_original = +1000
    - Payment of $600:    Ledger.value_original = -600
    - Balance =           +400 (still owed)
    
    WHY NEGATIVE VALUES:
    The sign convention allows simple aggregation:
    - SUM(value_available) = Current balance
    - No need for separate "debit" vs "credit" fields
    - Easy to validate: invoice total = -payment total when fully paid
    
    LINKAGE:
    - parent_id → Payment record ID
    - invoice_id → Invoice being paid (FK for allocation)
    - model_name → 'payment' for type identification
    
    Args:
        invoice: Invoice instance being paid
        amount: Positive Decimal amount paid (stored as negative)
        dt_paid: Datetime of payment receipt
        payment: Optional Payment instance for audit linkage
        gl_account_id: Optional GL account for FX variance posting
        source: 'AR' for Accounts Receivable (default)
    
    Returns:
        Created Ledger instance with negative value
    """
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    
    # AUDIT: Extract payment ID for linkage
    pid = getattr(payment, 'id', None)
    
    # AUDIT: refs JSON provides alternative query path for payment lookups
    refs = {
        'links': {
            'parent': {'model': 'payment', 'id': pid}
        }
    }
    
    # AUDIT: Ensure Decimal type for precision
    val = (amount if isinstance(amount, Decimal) else Decimal(str(amount)))
    
    # AUDIT: Create payment ledger with NEGATIVE value
    # -abs(val) ensures negative regardless of input sign
    obj = Ledger(
        dt_recorded=dt_paid,                       # When payment was recorded
        dt_posted=dt_paid,                         # When payment was posted (same initially)
        is_settled=False,                          # Not yet allocated to invoice ledgers
        model_name='payment',                      # Source document type
        source=source,                             # Usually 'AR'
        parent_id=pid,                             # Payment record ID
        invoice_id=invoice,                        # FK to Invoice for allocation
        term_id=None,                              # Payments don't have terms
        value_original=float(-abs(val)),           # Original amount (NEGATIVE, immutable)
        value_available=float(-abs(val)),          # Current unallocated (NEGATIVE)
        refs=refs,                                 # Additional metadata
        gl_account_id=gl_account_id,               # GL account for FX variance
    )
    obj.save()
    return obj
