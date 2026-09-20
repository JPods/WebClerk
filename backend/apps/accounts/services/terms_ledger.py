"""
Terms Ledger Service
====================

AUDIT DOCUMENTATION
-------------------
This module handles installment schedule calculation and ledger record creation.
It translates cash terms (Net 30, 2/10 Net 30, etc.) into concrete ledger
records with specific due dates and discount opportunities.

KEY CONCEPTS:

1. CASH TERMS → SCHEDULE → LEDGER RECORDS
   - Term defines: period_count, days_due, days_in_period, discount
   - Schedule splits invoice into dated installments
   - Ledger records track each installment's due amount and status

2. LEDGER VALUE CONVENTION
   - Invoice ledgers: POSITIVE values (money owed to company)
   - Cash ledgers: NEGATIVE values (money received from customer)
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
- value_available tracks current unpaid balance (decreases with cash)
- refs JSON captures additional relationship metadata

FINANCIAL COMPLIANCE:
- All monetary calculations use Decimal for precision
- Schedule shares must sum to exactly 1.0 (100%)
- Rounding differences go to last installment
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduleEntry:
    """
    A single installment in a installment schedule.
    
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
    Compute a installment schedule from a Term.
    
    AUDIT: This is the SCHEDULE CALCULATION function.
    It determines HOW MANY ledger records to create and WHEN each is due.
    
    BASE DATE SELECTION:
    - Default: Uses invoice_dt as the base for due date calculations
    - Override: If term.dt_begin is set, uses that fixed date instead
    - Use case: Terms like "Due Dec 8" or "3 cash_entries starting Dec 12"
    
    CALCULATION RULES:
    
    1. SINGLE INSTALLMENT (period_count <= 1):
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
        invoice_dt: Invoice date (fallback start of cash period)
        total: Invoice total (for documentation, not used in calculation)
        term: Term object with period_count, days_due, days_in_period, dt_begin, etc.
    
    Returns:
        List of ScheduleEntry objects defining the installment schedule
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
    # This supports fixed-date terms like "Due Dec 8" or "3 cash_entries starting Dec 12"
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
    day_cut_off_invoice = getattr(term, 'day_cut_off_invoice', None)
    day_cut_off_due = getattr(term, 'day_cut_off_due', None)

    entries: List[ScheduleEntry] = []

    if period_count <= 1:
        if day_cut_off_invoice and day_cut_off_due:
            # Cut-off day logic (wc2 pattern):
            # If invoice date is on or before the cut-off day, due on the
            # cut-off due day of the same month. If after, due on the
            # cut-off due day of the following month. No grace period.
            inv_day = base_dt.day
            inv_year = base_dt.year
            inv_month = base_dt.month
            if inv_day <= day_cut_off_invoice:
                due_month = inv_month
                due_year = inv_year
            else:
                due_month = inv_month + 1
                due_year = inv_year
                if due_month > 12:
                    due_month = 1
                    due_year += 1
            # Clamp due day to last day of target month
            import calendar
            last_day = calendar.monthrange(due_year, due_month)[1]
            due_day = min(day_cut_off_due, last_day)
            due = datetime(due_year, due_month, due_day, tzinfo=base_dt.tzinfo)
        else:
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
    It materializes a installment schedule into actual database records.
    
    WHAT GETS CREATED (strategy='records'):
    For each ScheduleEntry from compute_schedule():
    - One Ledger record with:
      - dt_due: When cash is due
      - dt_discount_due: When discount expires (if applicable)
      - discount_potential: Discount rate (e.g., 0.02)
      - value_original: Entry's share of total (immutable)
      - value_available: Same initially (decreases with cash)
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
    This function does NOT handle concurrent access or cash_entries.
    Caller should wrap in a transaction if needed.
    
    Args:
        invoice_id: Invoice instance to create ledgers for
        total: Invoice total in Decimal
        term_id: Term instance defining installment schedule
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
        meta = getattr(invoice_id, 'metadata', {}) or {}
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
    instalments = allocate_instalments(total, schedule)
    for e, value in zip(schedule, instalments):
        # value is this instalment's exact cents; the parts add up to the document total.
        
        # AUDIT: refs JSON captures relationship metadata for queries
        inv_id = getattr(invoice_id, 'id')
        org_id = getattr(invoice_id, 'customer_id', None)
        refs = {
            'links': {
                'parent': {'model': 'invoice', 'id': inv_id},
                'org': {'id': org_id},
            }
        }
        
        # AUDIT: Create ledger with full audit trail
        obj = Ledger(
            dt_due=e.due,                          # When cash is due
            dt_discount_due=e.discount_due,        # When discount expires
            discount_potential=float(e.discount_rate) if e.discount_rate is not None else None,
            model_name='invoice',                  # Source document type
            source='AR',                           # Accounts Receivable
            parent_id=inv_id,                      # Source document ID
            org_id=org_id,                         # Org FK for indexed queries
            invoice=invoice_id,                    # FK for joins
            term=term_id,                          # FK for audit trail
            value_original=float(value),           # Initial amount (immutable)
            value_available=float(value),          # Current unpaid (mutable)
            refs=refs,                             # Additional metadata
        )
        obj.save()
        created.append(obj)
    return created


def company_default_term_ida() -> str:
    """company profile config.receivables.default_term — the Term a document
    uses when it names none."""
    from django.apps import apps as dj_apps
    Setting = dj_apps.get_model('core', 'Setting')
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    receivables = (company.config or {}).get('receivables') if company and isinstance(company.config, dict) else None
    return (receivables or {}).get('default_term') or ''


def resolve_term(document):
    """The Term a document's money is due under — one resolver for AR and AP.

    A document names its term by **name** — ``terms`` holds a Term ida (N30,
    2pct10N30, ...), as WC2 did (Bill, 2026-09-20). The name is what is populated (31
    invoices to 2 in wc_demo) and the only key that survives moving between databases:
    an id is local to one, while N30 means N30 on the desktop and in the cloud alike.
    ``terms_fk`` is read only as a fallback for records that carry it and no name. No
    name and no default raises: a document never silently gets no due date.

    Both sides must read the same fields or the same document ages differently depending
    on which one you ask. AP was reading only the FK and AR only the ida (mine, 4f538b6,
    2026-09-20), and in wc_demo the ida is the populated one — 31 invoices to 2 — so
    every AP schedule was quietly falling back to a default.
    """
    from django.apps import apps as dj_apps
    Term = dj_apps.get_model('accounts', 'Term')

    ida = (getattr(document, 'terms', None) or '').strip()
    if not ida:
        fk = getattr(document, 'terms_fk', None)      # fallback: a record with only an id
        if fk is not None and getattr(fk, 'is_active', True):
            return fk
        ida = company_default_term_ida()
    label = getattr(document, 'ida', None) or getattr(document, 'pk', '?')
    if not ida:
        raise ValueError(
            f'{label} has no terms and the company profile has no config.receivables.default_term.')
    resolved = Term.objects.filter(ida__iexact=ida, is_active=True).first()
    if resolved is None:
        raise ValueError(f'{label} terms "{ida}" is not an active Term record.')
    return resolved



def allocate_instalments(total: Decimal, schedule) -> List[Decimal]:
    """Split a total into instalment amounts that add up to it exactly.

    compute_schedule returns shares (0.3333 / 0.3333 / 0.3334). Multiplying each by the
    total and rounding independently does not add back: 118.20 became 39.40 + 39.40 +
    39.41 = 118.21, a cent more than the invoice (found 2026-09-20, the first time a
    multi-part term was ever exercised). Allocate the cents instead and let the last part
    carry the remainder — the same rule the totals engine uses to spread a document
    discount across lines (Bill, 2026-09-19).
    """
    from apps.transactions.services.pricing.totals_compute import _allocate

    # Allocate on the term's own shares. 300.00 over three parts comes out
    # 99.99 / 99.99 / 100.02 — Bill, 2026-09-20: "the rounding variance of a few cents is
    # understandable by most people." The defect was the parts not adding up to the
    # document, not their being uneven, and allocating on the real shares also keeps a
    # genuinely unequal term (30/70) saying what it means.
    return _allocate(Decimal(str(total)), [Decimal(str(e.share)) for e in schedule])


def settlement_days(org_id, model_name: str = 'invoice') -> List[int]:
    """Days from an instalment's due date to the day the document was settled.

    The schedule comes from the ledger (each part has its own due date, which is what
    ledgers are for) and the settlement date from the document's application events. It
    read Ledger.dt_applied until 2026-09-20 — a field nothing ever set, so it measured
    nothing and every customer scored 0, which reads as "pays exactly on the due date".

    Lived in two places (ledger_balance and org_metrics), broken identically in both.
    """
    from django.apps import apps as dj_apps

    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Document = dj_apps.get_model('transactions', 'Invoice' if model_name == 'invoice' else 'Receipt')
    org_field = 'customer_id' if model_name == 'invoice' else 'vendor_id'

    due_by_doc = {}
    for parent_id, dt_due in Ledger.objects.filter(
        org_id=org_id, model_name=model_name, dt_due__isnull=False,
    ).values_list('parent_id', 'dt_due'):
        if parent_id is None:
            continue
        due_d = dt_due.date() if hasattr(dt_due, 'date') else dt_due
        if parent_id not in due_by_doc or due_d > due_by_doc[parent_id]:
            due_by_doc[parent_id] = due_d        # settled means the last instalment

    from datetime import datetime as _dt, timezone as _tz
    days = []
    for doc in Document.objects.filter(
        is_deleted=False, pk__in=list(due_by_doc), **{org_field: org_id},
    ).only('id', 'events', 'totals'):
        events = [e for e in (getattr(doc, 'events', None) or [])
                  if isinstance(e, dict) and e.get('kind') == 'cash_application' and e.get('dt')]
        if not events:
            continue
        if Decimal(str((doc.totals or {}).get('balance') or 0)) > Decimal('0.005'):
            continue                              # not settled; it says nothing about speed
        settled = _dt.fromtimestamp(max(int(e['dt']) for e in events) / 1000, tz=_tz.utc).date()
        days.append((settled - due_by_doc[doc.pk]).days)
    return days

def apply_terms_for_invoice(invoice, total: Optional[Decimal] = None, term=None, strategy: str = 'records', replace: bool = False):
    """
    Idempotent helper to materialize ledgers when terms are present or applied.
    
    AUDIT: This is the HIGH-LEVEL API for invoice ledger creation.
    It handles term resolution, total calculation, and optional cleanup.
    
    IDEMPOTENCY:
    - If replace=True, deletes existing ledgers before creating new ones
    - Safe to call multiple times with replace=True
    
    TERM RESOLUTION (if term not provided):
    Term: resolve_term() — invoice.terms (a Term ida), else the company
    default term; raises when neither resolves.
    
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

    if term is None:
        term = resolve_term(invoice)

    # Resolve total — JSON envelope is the single source of truth.
    if total is None:
        totals_map = getattr(invoice, 'totals', None) or {}
        if isinstance(totals_map, dict):
            total_val = totals_map.get('total', 0)
            try:
                total = D(str(total_val))
            except Exception:
                total = D('0')
        if not total:
            inv_id = getattr(invoice, 'id', '?')
            logger.error(
                "terms_ledger: invoice %s has no totals.total in JSON envelope. "
                "Run update_sell_cost_totals() to repair.", inv_id,
            )
            return []

    # AUDIT: replace=True provides idempotency by clearing this invoice's own
    # ledgers. Cash ledgers also carry invoice_id; they belong to the cash.
    if replace:
        Ledger.objects.filter(invoice_id=getattr(invoice, 'id'), model_name='invoice').delete()

    if total < 0:
        # Credit memo: one ledger, available immediately — no schedule to wait on
        term = None
    records = create_ledger_records(invoice_id=invoice, total=total, term_id=term, strategy=strategy)
    allocate_received(invoice)
    return records


def apply_terms_for_payable(receipt, total=None, replace: bool = True):
    """Payables work like receivables (Bill, 2026-09-19): each payable creates ledger
    rows with a due date, so AP has a water level the same way AR does.

    A receipt is the vendor's bill. Its vendor and terms come from the purchase it
    belongs to. Rows carry model_name 'receipt', source 'AP', and a positive value:
    what we owe. Payments (cash_out) reduce value_available through allocate_paid.

    A receipt with no lines is a draft: no payable, no ledger row. The money always
    comes from the lines, so every payable dollar is traceable.
    """
    from decimal import Decimal as D
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')

    if total is None:
        # The payable's money always comes from its own lines (Bill, 2026-09-19).
        # vendor_invoice_amount is the vendor's claim, reconciled against this — never a total.
        total = D(str((getattr(receipt, 'totals', None) or {}).get('total') or 0))
    if replace:
        Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt').delete()
    if not total:
        return []

    # A receipt is a transaction: it carries its own vendor and terms (inherited from
    # the purchase it receives against when it is created).
    vendor_id = getattr(receipt, 'vendor_id', None)
    if not vendor_id:
        # Nothing is owed to nobody. A receipt with no vendor is an internal movement
        # (or an unfinished draft), and an AP row with no org hides in every report
        # that groups by vendor (Bill, 2026-09-20).
        logger.info("[terms_ledger] receipt %s has no vendor — no payable",
                    getattr(receipt, 'ida', None) or getattr(receipt, 'pk', None))
        return []
    dt = getattr(receipt, 'dt_received', None) or getattr(receipt, 'dt_created', None)
    from datetime import datetime, timezone as _tz
    if isinstance(dt, int):
        dt = datetime.fromtimestamp(dt / 1000, _tz.utc)
    schedule = compute_schedule(dt or datetime.now(_tz.utc), total, resolve_term(receipt))

    created = []
    for e, value in zip(schedule, allocate_instalments(total, schedule)):
        obj = Ledger(
            dt_due=e.due,
            dt_discount_due=e.discount_due,
            discount_potential=float(e.discount_rate) if e.discount_rate is not None else None,
            model_name='receipt',
            source='AP',
            parent_id=receipt.pk,
            org_id=vendor_id,
            value_original=float(value),
            value_available=float(value),
            refs={'links': {'parent': {'model': 'receipt', 'id': receipt.pk},
                            'org': {'id': vendor_id},
                            getattr(receipt, 'parent_model', None) or 'source':
                                {'id': getattr(receipt, 'parent_id', None)}}},
        )
        obj.save()
        created.append(obj)
    allocate_paid(receipt)
    return created


def allocate_paid(receipt) -> None:
    """Spread what has been paid over the payable's ledgers, earliest due first,
    so Σ receipt ledgers = the receipt's balance. The AP mirror of allocate_received."""
    from decimal import Decimal as D
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    t = getattr(receipt, 'totals', None) or {}
    remaining = D(str(t.get('paid') or 0)) + D(str(t.get('adjusted') or 0))
    ledgers = list(Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt').order_by('dt_due', 'id'))
    for i, ledger in enumerate(ledgers):
        original = D(str(ledger.value_original or 0))
        last = i == len(ledgers) - 1
        if last:
            take = remaining
        elif original == 0 or remaining == 0 or (original > 0) != (remaining > 0):
            take = D('0')
        else:
            take = min(abs(original), abs(remaining)) * (1 if original > 0 else -1)
        remaining -= take
        available = float(original - take)
        if ledger.value_available != available:
            ledger.value_available = available
            ledger.save(update_fields=['value_available'])


def _resolve_term(term_id):
    """A Term instance from its id, or None (compute_schedule then uses the default)."""
    if term_id is None:
        return None
    from django.apps import apps as dj_apps
    return dj_apps.get_model('accounts', 'Term').objects.filter(pk=term_id).first()


def allocate_received(invoice) -> None:
    """Spread what has been settled over the invoice's ledgers, earliest due first.

    Each ledger's value_available = value_original − its share, so
    Σ invoice ledgers = the invoice's balance, always. When more was settled than
    the invoice asked (an overpayment, or a return taken against it), the last
    ledger carries the credit as a negative value: that is money available to the
    customer, and it must show in the ledger, never nowhere (Bill, 2026-09-19).
    """
    from django.apps import apps as dj_apps
    from decimal import Decimal as D
    Ledger = dj_apps.get_model('accounts', 'Ledger')

    t = getattr(invoice, 'totals', None) or {}
    remaining = D(str(t.get('received') or 0)) + D(str(t.get('adjusted') or 0))
    ledgers = list(Ledger.objects.filter(
        invoice_id=invoice.pk, model_name='invoice',
    ).order_by('dt_due', 'id'))
    for i, ledger in enumerate(ledgers):
        original = D(str(ledger.value_original or 0))
        last = i == len(ledgers) - 1
        if last:
            take = remaining                      # the last row carries any credit
        elif original == 0 or remaining == 0 or (original > 0) != (remaining > 0):
            take = D('0')
        else:
            take = min(abs(original), abs(remaining)) * (1 if original > 0 else -1)
        remaining -= take
        available = float(original - take)
        if ledger.value_available != available:
            ledger.value_available = available
            ledger.save(update_fields=['value_available'])


def record_cash(invoice, amount: Decimal, dt_paid, cash=None, gl_account_id=None, source: str = 'AR'):
    """
    Create a cash ledger with NEGATIVE value to offset invoice ledgers.
    
    AUDIT: This creates the CounterbalancING side of the A/R ledger.
    
    ACCOUNTING PRINCIPLE:
    - Invoice ledgers have POSITIVE values (money owed TO us)
    - Cash ledgers have NEGATIVE values (money received FROM customer)
    - Sum of all ledgers = Current A/R balance
    
    Example:
    - Invoice for $1,000: Ledger.value_original = +1000
    - Cash of $600:    Ledger.value_original = -600
    - Balance =           +400 (still owed)
    
    WHY NEGATIVE VALUES:
    The sign convention allows simple aggregation:
    - SUM(value_available) = Current balance
    - No need for separate "debit" vs "credit" fields
    - Easy to validate: invoice total = -cash total when fully paid
    
    LINKAGE:
    - parent_id → Cash record ID
    - invoice_id → Invoice being paid (FK for allocation)
    - model_name → 'cash' for type identification
    
    Args:
        invoice: Invoice instance being paid
        amount: Positive Decimal amount paid (stored as negative)
        dt_paid: Datetime of cash receipt
        cash: Optional Cash instance for audit linkage
        gl_account_id: Optional GL account for FX variance posting
        source: 'AR' for Accounts Receivable (default)
    
    Returns:
        Created Ledger instance with negative value
    """
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    
    # AUDIT: Extract cash ID for linkage
    pid = getattr(cash, 'id', None)
    
    # AUDIT: refs JSON provides alternative query path for cash lookups
    org_id = getattr(cash, 'customer_id', None) or (getattr(invoice, 'customer_id', None) if invoice else None)
    refs = {
        'links': {
            'parent': {'model': 'cash', 'id': pid},
            'org': {'id': org_id},
        }
    }
    
    # AUDIT: Ensure Decimal type for precision
    val = (amount if isinstance(amount, Decimal) else Decimal(str(amount)))

    # WC2: origValue = -amount (immutable), unAppliedValue = -available (tracks applications)
    # `amount` passed here is cash.available (from on_cash_save).
    # value_original uses the full cash.amount for the immutable record.
    original_amount = Decimal(str(getattr(cash, 'amount', val))) if cash else val

    # AUDIT: Create cash ledger with NEGATIVE value
    # -abs(val) ensures negative regardless of input sign
    obj = Ledger(
        dt_recorded=dt_paid,                       # When cash was recorded
        model_name='cash',                      # Source document type
        source=source,                             # Usually 'AR'
        parent_id=pid,                             # Cash record ID
        org_id=org_id,                             # Org FK for indexed queries
        invoice=invoice,                           # FK to Invoice for allocation
        term_id=None,                              # Cash don't have terms
        value_original=float(-original_amount),  # Original cash amount, sign flipped (refund cash → positive)
        value_available=float(-val),             # Current unapplied, sign flipped (tracks applications)
        refs=refs,                                 # Additional metadata
        gl_account=gl_account_id,                  # GL account for FX variance
    )
    obj.save()
    return obj
