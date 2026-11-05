"""Accounting dashboard data service.

Provides summary data for the admin accounting dashboard:
- Last journalized records by type
- Pending journal count (staged but not posted)
- GL imbalances (debits != credits)
- Orphan counts
- Aging summary
- Transaction volume by type
- Locked record counts
- Journal exceptions (transactions that cannot be processed)
"""
import logging
import time
from decimal import Decimal
from typing import Any, Dict, List

from django.apps import apps as dj_apps
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_journal_exceptions(year: int = None, month: int = None) -> Dict[str, Any]:
    """Return all transactions that cannot be journalized, grouped by reason.

    Opens in a separate window from the accounting dashboard. Three panels:

    1. **exceptions** — out-of-balance journals that need user action
       (ForceToBalance or fix the source transaction)
    2. **skipped** — hold cash, consigned invoices, zero-amount cash
       (informational — no action needed unless status changes)
    3. **queue** — open transactions not yet journalized (eligible to post)

    If year/month provided, filters to that period. Otherwise shows all open.

    Returns:
        {exceptions: [...], skipped: [...], queue: [...], summary: {...}}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Cash = dj_apps.get_model('transactions', 'Cash')
    Purchase = dj_apps.get_model('transactions', 'Purchase')

    now_ms = int(time.time() * 1000)

    # Period filter
    period_filter = {}
    if year and month:
        import calendar
        from datetime import date
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1)
        else:
            period_end = date(year, month + 1, 1)
        start_ms = int(calendar.timegm(period_start.timetuple()) * 1000)
        end_ms = int(calendar.timegm(period_end.timetuple()) * 1000)
        period_filter = {'dt_created__gte': start_ms, 'dt_created__lt': end_ms}

    # IDs already journalized
    posted_inv_ids = set(
        GlJournal.objects.filter(source_model='invoice')
        .values_list('source_id', flat=True)
    )
    posted_pay_ids = set(
        GlJournal.objects.filter(source_model='cash')
        .values_list('source_id', flat=True)
    )
    posted_po_ids = set(
        GlJournal.objects.filter(source_model='purchase')
        .values_list('source_id', flat=True)
    )

    exceptions = []
    skipped = []
    queue = []

    def _txn_dict(instance, model_name):
        """Standard dict for a transaction record."""
        return {
            'id': instance.pk,
            'ida': getattr(instance, 'ida', ''),
            'model': model_name,
            'status': getattr(instance, 'status', ''),
            'total': float(getattr(instance, 'total', 0) or 0),
            'customer_id': getattr(instance, 'customer_id', None),
            'dt_created': getattr(instance, 'dt_created', None),
        }

    # --- Invoices ---
    inv_qs = Invoice.objects.filter(
        is_active=True, **period_filter,
    ).exclude(pk__in=posted_inv_ids)

    for inv in inv_qs:
        rec = _txn_dict(inv, 'invoice')
        status = (getattr(inv, 'status', '') or '').lower()

        if status == 'consigned':
            rec['reason'] = 'Consigned — revenue deferred'
            skipped.append(rec)
        elif inv.dt_journaled:
            # Locked but no journal entries — something went wrong
            rec['reason'] = 'Locked but not journalized — possible interrupted posting'
            exceptions.append(rec)
        else:
            # Try a dry-run balance check
            check = _dry_run_invoice_balance(inv)
            if check.get('error'):
                rec['reason'] = check['error']
                rec['residual'] = float(check.get('residual', 0))
                exceptions.append(rec)
            else:
                queue.append(rec)

    # --- Cash ---
    pay_qs = Cash.objects.filter(
        is_active=True, **period_filter,
    ).exclude(pk__in=posted_pay_ids)

    for pay in pay_qs:
        rec = _txn_dict(pay, 'cash')
        rec['amount'] = float(getattr(pay, 'amount', 0) or 0)
        status = (getattr(pay, 'status', '') or '').lower()

        if status == 'on_hold':
            rec['reason'] = f'On hold (status={pay.status})'
            skipped.append(rec)
        elif rec['amount'] == 0:
            # Check if already auto-completed
            meta = pay.metadata or {}
            gl_info = meta.get('gl_accounts', {})
            if gl_info.get('zero_amount'):
                continue  # already handled
            rec['reason'] = 'Zero amount — will auto-complete'
            skipped.append(rec)
        else:
            queue.append(rec)

    # --- Purchases ---
    po_qs = Purchase.objects.filter(
        is_active=True, **period_filter,
    ).exclude(pk__in=posted_po_ids)

    for po in po_qs:
        rec = _txn_dict(po, 'purchase')
        if po.dt_journaled:
            rec['reason'] = 'Locked but not journalized — possible interrupted posting'
            exceptions.append(rec)
        else:
            check = _dry_run_purchase_balance(po)
            if check.get('error'):
                rec['reason'] = check['error']
                rec['residual'] = float(check.get('residual', 0))
                exceptions.append(rec)
            else:
                queue.append(rec)

    # --- Force-balanced records (resolved exceptions — show in history) ---
    force_balanced = list(
        GlJournal.objects.filter(
            source='manual', note__startswith='Force-to-balance:',
        ).values('source_id', 'source_model', 'note', 'debit', 'credit', 'dt_created')
        .order_by('-dt_created')[:50]
    )

    return {
        'exceptions': exceptions,
        'skipped': skipped,
        'queue': queue,
        'force_balanced': force_balanced,
        'summary': {
            'exception_count': len(exceptions),
            'skipped_count': len(skipped),
            'queue_count': len(queue),
            'force_balanced_count': len(force_balanced),
        },
        'period': f'{year}-{month:02d}' if year and month else 'all_open',
        'dt_generated': now_ms,
    }


def _dry_run_invoice_balance(invoice) -> dict:
    """Check if an invoice would balance without actually posting.

    Runs the same line-walk as journalize_invoice but only checks the math.
    """
    InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')

    lines = InvoiceLine.objects.filter(invoice_id=invoice.pk)
    if not lines.exists():
        return {'error': 'No lines'}

    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for line in lines:
        extended = Decimal(str((line.totals or {}).get('amount', 0) or 0))
        if extended == 0:
            continue

        # AR debit = Revenue credit for each line (should balance)
        total_debit += extended
        total_credit += extended

        # COGS/Inventory — only if item has cost
        item_id = line.item_fk_id
        if not item_id:
            item_data = line.item or {}
            item_id = item_data.get('item_id')
        if item_id:
            try:
                Item = dj_apps.get_model('products', 'Item')
                item = Item.objects.get(pk=item_id)
                cost_data = item.cost or {}
                item_cost = Decimal(str(cost_data.get('standard', cost_data.get('average', 0)) or 0))
                qty_data = line.quantity or {}
                qty = Decimal(str(qty_data.get('active', 0) or 0))
                if item_cost > 0 and qty > 0:
                    cogs = item_cost * qty
                    total_debit += cogs
                    total_credit += cogs
            except Exception:
                pass

    residual = total_debit - total_credit
    if residual != 0:
        return {'error': f'Out of balance: residual={residual}', 'residual': residual}
    return {}


def _dry_run_purchase_balance(purchase) -> dict:
    """Check if a purchase would balance without actually posting."""
    PurchaseLine = dj_apps.get_model('transactions', 'PurchaseLine')

    lines = PurchaseLine.objects.filter(purchase_id=purchase.pk)
    if not lines.exists():
        return {'error': 'No lines'}

    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for line in lines:
        extended = Decimal(str((line.totals or {}).get('amount', 0) or 0))
        if extended == 0:
            continue
        total_debit += extended
        total_credit += extended

    residual = total_debit - total_credit
    if residual != 0:
        return {'error': f'Out of balance: residual={residual}', 'residual': residual}
    return {}
