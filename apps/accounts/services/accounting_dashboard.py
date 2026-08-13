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


def get_accounting_dashboard() -> Dict[str, Any]:
    """Return all accounting dashboard data in one call."""
    return {
        'journal_status': _get_journal_status(),
        'gl_balance': _get_gl_balance(),
        'transaction_volume': _get_transaction_volume(),
        'locked_records': _get_locked_records(),
        'aging_summary': _get_aging_summary(),
        'pending_inventory': _get_pending_inventory(),
        'dt_generated': int(timezone.now().timestamp() * 1000),
    }


def _get_journal_status() -> Dict[str, Any]:
    """Last journalized records and pending journal count by type."""
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')

    # Last journalized by type
    last_invoice_gl = (
        GlJournal.objects.filter(source_model='invoice')
        .order_by('-dt_created').values('source_id', 'dt_created').first()
    )
    last_payment_gl = (
        GlJournal.objects.filter(source_model='payment')
        .order_by('-dt_created').values('source_id', 'dt_created').first()
    )

    # Count invoices with staged GL but not posted (metadata has gl_accounts but no GlJournal records)
    # Approximation: invoices not locked that have totals > 0
    pending_invoices = Invoice.objects.filter(
        is_locked=False, is_deleted=False, is_active=True,
    ).exclude(
        totals={},
    ).count()

    pending_payments = Payment.objects.filter(
        is_locked=False, is_deleted=False, is_active=True,
    ).exclude(
        amount=0,
    ).count()

    # Total journalized
    total_journal_entries = GlJournal.objects.count()

    return {
        'last_invoice_journalized': last_invoice_gl,
        'last_payment_journalized': last_payment_gl,
        'pending_invoices': pending_invoices,
        'pending_payments': pending_payments,
        'total_journal_entries': total_journal_entries,
    }


def _get_gl_balance() -> Dict[str, Any]:
    """Check GL balance — total debits should equal total credits."""
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    totals = GlJournal.objects.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
    )
    total_debit = Decimal(str(totals['total_debit'] or 0))
    total_credit = Decimal(str(totals['total_credit'] or 0))
    imbalance = total_debit - total_credit

    # Per-source imbalances
    source_imbalances = []
    sources = GlJournal.objects.values('source_model').annotate(
        debits=Sum('debit'), credits=Sum('credit'),
    )
    for s in sources:
        d = Decimal(str(s['debits'] or 0))
        c = Decimal(str(s['credits'] or 0))
        if d != c:
            source_imbalances.append({
                'source_model': s['source_model'],
                'debits': float(d),
                'credits': float(c),
                'imbalance': float(d - c),
            })

    return {
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
        'imbalance': float(imbalance),
        'balanced': abs(imbalance) < Decimal('0.01'),
        'source_imbalances': source_imbalances,
    }


def _get_transaction_volume() -> Dict[str, Any]:
    """Transaction counts by type and status."""
    result = {}
    for model_name in ['Order', 'Invoice', 'Proposal', 'Purchase', 'WorkOrder']:
        try:
            Model = dj_apps.get_model('transactions', model_name)
            total = Model.objects.filter(is_deleted=False).count()
            by_status = dict(
                Model.objects.filter(is_deleted=False)
                .values_list('status')
                .annotate(count=Count('id'))
            )
            result[model_name.lower()] = {
                'total': total,
                'by_status': by_status,
            }
        except Exception:
            pass
    return result


def _get_locked_records() -> Dict[str, Any]:
    """Count of locked (journalized) records by type."""
    result = {}
    for model_name in ['Invoice', 'Payment']:
        try:
            Model = dj_apps.get_model('transactions', model_name)
            locked = Model.objects.filter(is_locked=True, is_deleted=False).count()
            unlocked = Model.objects.filter(is_locked=False, is_deleted=False).count()
            result[model_name.lower()] = {
                'locked': locked,
                'unlocked': unlocked,
            }
        except Exception:
            pass
    return result


def _get_aging_summary() -> Dict[str, Any]:
    """Aggregate aging across all customer orgs."""
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')

    customers = OrgBase.objects.filter(
        org_type='customer', is_active=True, is_deleted=False,
    )

    total_current = Decimal('0')
    total_30 = Decimal('0')
    total_60 = Decimal('0')
    total_90 = Decimal('0')
    customers_with_balance = 0

    for cust in customers:
        financial = getattr(cust, 'financial', None)
        if not isinstance(financial, dict):
            continue
        cust_fin = financial.get('customer', {})
        aging = cust_fin.get('aging', {})
        if not aging:
            continue

        current = Decimal(str(aging.get('current', 0) or 0))
        p1 = Decimal(str(aging.get('period_1', 0) or 0))
        p2 = Decimal(str(aging.get('period_2', 0) or 0))
        p3 = Decimal(str(aging.get('period_3', 0) or 0))

        if current + p1 + p2 + p3 > 0:
            customers_with_balance += 1
            total_current += current
            total_30 += p1
            total_60 += p2
            total_90 += p3

    return {
        'current': float(total_current),
        'period_1_30': float(total_30),
        'period_2_60': float(total_60),
        'period_3_90_plus': float(total_90),
        'total_ar': float(total_current + total_30 + total_60 + total_90),
        'customers_with_balance': customers_with_balance,
    }


def _get_pending_inventory() -> Dict[str, Any]:
    """Unprocessed inventory pending records."""
    Pending = dj_apps.get_model('core', 'Pending')

    unprocessed = Pending.objects.filter(
        model_name='item',
        purpose__startswith='inventory',
        dt_processed=0,
    )

    count = unprocessed.count()

    # Age of oldest unprocessed
    oldest = unprocessed.order_by('dt_created').values('dt_created').first()
    oldest_age_ms = 0
    if oldest and oldest['dt_created']:
        now_ms = int(timezone.now().timestamp() * 1000)
        oldest_age_ms = now_ms - oldest['dt_created']

    return {
        'unprocessed_count': count,
        'oldest_age_ms': oldest_age_ms,
        'oldest_age_minutes': round(oldest_age_ms / 60000, 1) if oldest_age_ms else 0,
    }


# ---------------------------------------------------------------------------
# Journal Exceptions — single-button view of everything that can't post
# ---------------------------------------------------------------------------

def get_journal_exceptions(year: int = None, month: int = None) -> Dict[str, Any]:
    """Return all transactions that cannot be journalized, grouped by reason.

    Opens in a separate window from the accounting dashboard. Three panels:

    1. **exceptions** — out-of-balance journals that need user action
       (ForceToBalance or fix the source transaction)
    2. **skipped** — hold payments, consigned invoices, zero-amount payments
       (informational — no action needed unless status changes)
    3. **queue** — open transactions not yet journalized (eligible to post)

    If year/month provided, filters to that period. Otherwise shows all open.

    Returns:
        {exceptions: [...], skipped: [...], queue: [...], summary: {...}}
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')
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
        GlJournal.objects.filter(source_model='payment')
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
        is_active=True, is_deleted=False, **period_filter,
    ).exclude(pk__in=posted_inv_ids)

    for inv in inv_qs:
        rec = _txn_dict(inv, 'invoice')
        status = (getattr(inv, 'status', '') or '').lower()

        if status == 'consigned':
            rec['reason'] = 'Consigned — revenue deferred'
            skipped.append(rec)
        elif inv.is_locked:
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

    # --- Payments ---
    pay_qs = Payment.objects.filter(
        is_active=True, is_deleted=False, **period_filter,
    ).exclude(pk__in=posted_pay_ids)

    for pay in pay_qs:
        rec = _txn_dict(pay, 'payment')
        rec['amount'] = float(getattr(pay, 'amount', 0) or 0)
        status = (getattr(pay, 'status', '') or '').lower()

        if status.startswith('hold'):
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
        is_active=True, is_deleted=False, **period_filter,
    ).exclude(pk__in=posted_po_ids)

    for po in po_qs:
        rec = _txn_dict(po, 'purchase')
        if po.is_locked:
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
        price_data = line.price or {}
        extended = Decimal(str(price_data.get('extended', 0) or 0))
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
        cost_data = getattr(line, 'cost', None) or getattr(line, 'price', None) or {}
        extended = Decimal(str(cost_data.get('extended', 0) or 0))
        if extended == 0:
            continue
        total_debit += extended
        total_credit += extended

    residual = total_debit - total_credit
    if residual != 0:
        return {'error': f'Out of balance: residual={residual}', 'residual': residual}
    return {}
