from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional


@dataclass
class ScheduleEntry:
    due: datetime
    share: Decimal  # fraction of total (0-1)
    discount_due: Optional[datetime] = None
    discount_rate: Optional[Decimal] = None  # 0.02 for 2%


def compute_schedule(invoice_dt: datetime, total: Decimal, term) -> List[ScheduleEntry]:
    """Compute a payment schedule from a Term.

    Rules:
    - Single payment if period_count is None/<=1. Due at invoice_dt + days_due.
    - If period_count > 1 and days_in_period set, split into equal shares spaced by days_in_period.
    - Early payment discount applies if days_discount and discount_rate are set; placed on first entry.
    - All datetimes are treated as UTC if naive.
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

    period_count = getattr(term, 'period_count', None) or 1
    days_due = getattr(term, 'days_due', None) or 0
    days_in_period = getattr(term, 'days_in_period', None) or days_due or 30
    days_discount = getattr(term, 'days_discount', None)
    discount_rate = getattr(term, 'discount_rate', None)

    entries: List[ScheduleEntry] = []

    if period_count <= 1:
        due = invoice_dt + timedelta(days=days_due)
        disc_due = None
        disc_rate = None
        if days_discount and discount_rate:
            disc_due = invoice_dt + timedelta(days=days_discount)
            disc_rate = Decimal(str(discount_rate))
        entries.append(ScheduleEntry(due=due, share=Decimal('1'), discount_due=disc_due, discount_rate=disc_rate))
        return entries

    # Multi-installment
    share = (Decimal('1') / Decimal(str(period_count))).quantize(Decimal('0.0001'))
    for i in range(period_count):
        due = invoice_dt + timedelta(days=days_in_period * (i + 1))
        disc_due = None
        disc_rate = None
        if i == 0 and days_discount and discount_rate:
            disc_due = invoice_dt + timedelta(days=days_discount)
            disc_rate = Decimal(str(discount_rate))
        entries.append(ScheduleEntry(due=due, share=share, discount_due=disc_due, discount_rate=disc_rate))
    # Adjust last share to absorb rounding
    total_share = sum((e.share for e in entries), Decimal('0'))
    if total_share != Decimal('1'):
        diff = Decimal('1') - total_share
        entries[-1].share = (entries[-1].share + diff)
    return entries


def create_ledger_records(invoice, total: Decimal, term, strategy: str = 'records'):
    """Create ledgers for an invoice based on a term.

    strategy:
      - 'records': create one Ledger per schedule entry (default).
      - 'metadata': attach schedule to invoice.metadata['terms']['schedule'] and do not create records.
    Note: This function does not handle concurrency or payments; call from a transaction.
    """
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')

    # Accept invoice.dt_created as epoch ms; fallback to now
    inv_dt = getattr(invoice, 'dt_created', None)
    schedule = compute_schedule(inv_dt if inv_dt is not None else datetime.now(timezone.utc), total, term)
    created = []
    if strategy == 'metadata':
        # Attach to invoice metadata
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
        invoice.metadata = meta
        invoice.save(update_fields=['metadata'])
        return created

    # Default: create records
    for e in schedule:
        value = (total * e.share)
        refs = {
            'links': {
                'parent': {'model': 'invoice', 'id': getattr(invoice, 'id')}
            }
        }
        obj = Ledger(
            dt_due=e.due,
            dt_discount_due=e.discount_due,
            discount_potential=float(e.discount_rate) if e.discount_rate is not None else None,
            model_name='invoice',  #chaned from t_n
            source='AR',
            parent_id=getattr(invoice, 'id'),  #chaned from t_n
            invoice=invoice,
            term=term,
            value_original=float(value),
            value_available=float(value),
            refs=refs,
        )
        obj.save()
        created.append(obj)
    return created


def apply_terms_for_invoice(invoice, total: Optional[Decimal] = None, term=None, strategy: str = 'records', replace: bool = False):
    """Idempotent helper to materialize ledgers when terms are present or applied.

    - If replace=True, existing ledger rows for this invoice are removed before creation.
    - If total is not provided, tries invoice.total map, then falls back to aggregate of invoice lines.
    - If term not provided, tries invoice.prefs.payment_terms (id or description).
    """
    from django.apps import apps as dj_apps
    from decimal import Decimal as D
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Term = dj_apps.get_model('accounts', 'Term')

    # Resolve term
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
            agg = compute_line_aggregate(parent_ref_id=getattr(invoice, 'id'), model_key='invoice-line')
            total = D(agg.get('total_price_extended', '0'))
            if total <= 0:
                return []

    if replace:
        Ledger.objects.filter(invoice_id=getattr(invoice, 'id')).delete()

    return create_ledger_records(invoice=invoice, total=total, term=term, strategy=strategy)


def record_payment(invoice, amount: Decimal, dt_paid, payment=None, gl_account_fx_variance=None, source: str = 'AR'):
    """Create a payment ledger with negative value to offset invoice ledgers.

    - amount: positive decimal (we store as negative in ledger)
    - dt_paid: datetime for payment posting/record
    - payment: optional payment object to link via parent_id and model_name='payment'
    - gl_account_fx_variance: optional Gl_account instance for FX gain/loss
    """
    from django.apps import apps as dj_apps
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    pid = getattr(payment, 'id', None)
    refs = {
        'links': {
            'parent': {'model': 'payment', 'id': pid}
        }
    }
    val = (amount if isinstance(amount, Decimal) else Decimal(str(amount)))
    obj = Ledger(
        dt_recorded=dt_paid,
        dt_posted=dt_paid,
        is_settled=False,
        model_name='payment',  #chaned from t_n
        source=source,
        parent_id=pid,  #chaned from t_n
        invoice=invoice,
        term=None,
        value_original=float(-abs(val)),
        value_available=float(-abs(val)),
        refs=refs,
        gl_account_fx_variance=gl_account_fx_variance,
    )
    obj.save()
    return obj
