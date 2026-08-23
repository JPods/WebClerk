"""Commerce Dashboard aggregate queries.

Five actions matching the CommerceDashboard.tsx tabs:
  get_sales_dashboard      — orders/invoices/proposals counts+totals, margin summary
  get_purchasing_dashboard  — POs/WOs/receipts/layers, stale PO list
  get_inventory_summary     — item counts, layer counts, low stock, value
  get_velocity_report       — margin velocity distribution
  get_accounting_dashboard  — AR/AP aging, payment summary
"""
import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Count, Sum, Q, F, Avg

logger = logging.getLogger(__name__)


def _margin_distribution(line_details):
    """Split line details into 4 equal-width margin buckets derived from the data.

    Args:
        line_details: list of (margin_pct, sell, cost, tax, commission) tuples

    Returns:
        {
            'buckets': [
                {
                    'label': '0–25%', 'min': 0, 'max': 25,
                    'count': 3, 'revenue': 450.00, 'cost': 380.00,
                    'margin': 70.00, 'tax': 31.50, 'commission': 22.50,
                    'margin_pct': 15.6
                },
                ...
            ],
            'min': 0.0, 'max': 100.0, 'total': 15,
            'totals': {
                'revenue': 5000.00, 'cost': 3200.00, 'margin': 1800.00,
                'tax': 350.00, 'commission': 250.00
            }
        }
    """
    if not line_details:
        return {'buckets': [], 'min': 0, 'max': 0, 'total': 0, 'totals': {}}

    pcts = [d[0] for d in line_details]
    lo = min(pcts)
    hi = max(pcts)

    # Avoid zero-width range
    if hi - lo < 1:
        lo = lo - 1
        hi = hi + 1

    span = hi - lo
    step = span / 4

    buckets = []
    grand = {'revenue': 0, 'cost': 0, 'margin': 0, 'tax': 0, 'commission': 0}

    for i in range(4):
        bmin = round(lo + i * step, 1)
        bmax = round(lo + (i + 1) * step, 1)
        b = {'label': f'{bmin:.0f}–{bmax:.0f}%', 'min': bmin, 'max': bmax,
             'count': 0, 'revenue': 0, 'cost': 0, 'margin': 0, 'tax': 0, 'commission': 0}

        for pct, sell, cost, tax, comm in line_details:
            if (bmin <= pct < bmax) or (i == 3 and pct == bmax):
                b['count'] += 1
                b['revenue'] += sell
                b['cost'] += cost
                b['margin'] += sell - cost
                b['tax'] += tax
                b['commission'] += comm

        # Round and compute bucket margin %
        for k in ('revenue', 'cost', 'margin', 'tax', 'commission'):
            b[k] = round(b[k], 2)
            grand[k] += b[k]
        b['margin_pct'] = round((b['margin'] / b['revenue'] * 100) if b['revenue'] else 0, 1)
        buckets.append(b)

    for k in grand:
        grand[k] = round(grand[k], 2)

    return {
        'buckets': buckets,
        'min': round(lo, 1),
        'max': round(hi, 1),
        'total': len(line_details),
        'totals': grand,
    }


def _cutoff_ms(period_days):
    now_ms = int(timezone.now().timestamp() * 1000)
    return now_ms - (period_days * 86400 * 1000)


def _base_filters(params):
    """Build Q filters from optional customer_id, vendor_id, salesperson_id, rep_id."""
    q = Q()
    if params.get('customer_id'):
        q &= Q(customer_id=params['customer_id'])
    if params.get('vendor_id'):
        q &= Q(vendor_id=params['vendor_id'])
    return q


def get_sales_dashboard(params):
    from apps.transactions.models import Order, Invoice, Proposal

    period = params.get('period_days', 30)
    cutoff = _cutoff_ms(period)
    base_q = _base_filters(params) & Q(dt_created__gte=cutoff)

    orders = Order.objects.filter(base_q).aggregate(
        count=Count('id'), total=Sum('total'))
    invoices = Invoice.objects.filter(base_q).aggregate(
        count=Count('id'), total=Sum('total'))
    proposals = Proposal.objects.filter(base_q).aggregate(
        count=Count('id'), total=Sum('total'))

    # Margin from invoice lines — iterate and compute from price/cost JSON
    from apps.transactions.models import InvoiceLine
    lines_q = Q(invoice__dt_created__gte=cutoff)
    if params.get('customer_id'):
        lines_q &= Q(invoice__customer_id=params['customer_id'])
    margin_floor = params.get('margin_floor', 20)
    above = 0
    below = 0
    line_details = []  # (margin_pct, sell, cost, tax, commission)

    for line in InvoiceLine.objects.filter(lines_q).iterator(chunk_size=200):
        price_d = line.price if isinstance(line.price, dict) else {}
        cost_d = line.cost if isinstance(line.cost, dict) else {}
        tax_d = line.tax if isinstance(line.tax, dict) else {}
        comm_d = line.commission if isinstance(line.commission, dict) else {}
        qty_d = line.quantity if isinstance(line.quantity, dict) else {}

        sell = price_d.get('extended') or price_d.get('unit')
        cost = cost_d.get('extended') or cost_d.get('unit')
        tax = tax_d.get('amount') or tax_d.get('total') or 0
        commission = comm_d.get('amount') or comm_d.get('total') or 0

        if sell and cost:
            try:
                s, c = float(sell), float(cost)
                t = float(tax) if tax else 0
                cm = float(commission) if commission else 0
                if s > 0:
                    pct = ((s - c) / s) * 100
                    line_details.append((pct, s, c, t, cm))
                    if pct >= margin_floor:
                        above += 1
                    else:
                        below += 1
            except (ValueError, TypeError):
                pass

    margin_pcts = [d[0] for d in line_details]
    avg_pct = sum(margin_pcts) / len(margin_pcts) if margin_pcts else 0

    # 4-bucket margin distribution — scale derived from actual data
    distribution = _margin_distribution(line_details)

    return {
        'transactions': {
            'orders': {'count': orders['count'] or 0, 'total': float(orders['total'] or 0)},
            'invoices': {'count': invoices['count'] or 0, 'total': float(invoices['total'] or 0)},
            'proposals': {'count': proposals['count'] or 0, 'total': float(proposals['total'] or 0)},
        },
        'margin': {
            'avg_pct': round(avg_pct, 1),
            'above_count': above,
            'below_count': below,
            'floor': margin_floor,
            'distribution': distribution,
        },
    }


def get_purchasing_dashboard(params):
    from apps.transactions.models import Purchase, WorkOrder

    period = params.get('period_days', 30)
    cutoff = _cutoff_ms(period)
    base_q = Q(dt_created__gte=cutoff)
    if params.get('vendor_id'):
        base_q &= Q(vendor_id=params['vendor_id'])

    pos = Purchase.objects.filter(base_q)
    po_open = pos.filter(status='open').count()
    po_partial = pos.filter(status='partial').count()
    po_received = pos.filter(status__in=['released', 'received', 'complete']).count()
    po_total = pos.count()

    wos = WorkOrder.objects.filter(Q(dt_created__gte=cutoff))
    wo_open = wos.filter(status='open').count()
    wo_in_progress = wos.filter(status__in=['in_progress', 'active']).count()
    wo_completed = wos.filter(status__in=['complete', 'released']).count()

    # Stale POs (open > 30 days)
    stale_cutoff = _cutoff_ms(30)
    stale = Purchase.objects.filter(
        status='open', dt_created__lt=stale_cutoff
    ).values('id', 'ida', 'status', 'dt_created')[:20]
    now_ms = int(timezone.now().timestamp() * 1000)
    stale_list = [{
        'po_id': s['id'], 'ida': s['ida'], 'status': s['status'],
        'days_open': (now_ms - s['dt_created']) // 86400000,
    } for s in stale]

    return {
        'purchase_orders': {
            'open': po_open, 'partial': po_partial,
            'received': po_received, 'total': po_total,
        },
        'work_orders': {
            'open': wo_open, 'in_progress': wo_in_progress,
            'completed': wo_completed,
        },
        'receipts': {'count': 0, 'qty': 0},
        'layers': {'created': 0, 'unreconciled': 0},
        'stale_pos': stale_list,
    }


def get_inventory_summary(params):
    from apps.products.models import Item

    items = Item.objects.filter(is_active=True, is_deleted=False)
    total_items = items.count()

    # Count items with on_hand > 0
    in_stock = 0
    low_stock = 0
    total_value = Decimal('0')

    for item in items.iterator(chunk_size=500):
        qty = item.quantity if isinstance(item.quantity, dict) else {}
        on_hand = qty.get('on_hand', 0) or 0
        if on_hand > 0:
            in_stock += 1
            cost_d = item.cost if isinstance(item.cost, dict) else {}
            avg_cost = cost_d.get('avg') or cost_d.get('standard') or 0
            try:
                total_value += Decimal(str(avg_cost)) * Decimal(str(on_hand))
            except Exception:
                pass
        inv_min = qty.get('inventory_min', 0) or 0
        if on_hand > 0 and inv_min > 0 and on_hand <= inv_min:
            low_stock += 1

    avg_turns = items.aggregate(avg=Avg('annual_turns'))['avg'] or 0

    return {
        'total_items': total_items,
        'in_stock': in_stock,
        'active_layers': 0,
        'active_reservations': 0,
        'low_stock_count': low_stock,
        'total_value': float(total_value),
        'avg_turns': float(avg_turns),
    }


def get_velocity_report(params):
    from apps.products.models import Item

    items = Item.objects.filter(is_active=True, is_deleted=False)
    categories = {'star': 0, 'volume_driver': 0, 'normal': 0, 'dead_capital': 0, '': 0}
    for cat, count in items.values_list('velocity_category').annotate(c=Count('id')):
        categories[cat or ''] = count

    return {
        'star': categories.get('star', 0),
        'volume_driver': categories.get('volume_driver', 0),
        'normal': categories.get('normal', 0),
        'dead_capital': categories.get('dead_capital', 0),
        'uncategorized': categories.get('', 0),
        'total_items': sum(categories.values()),
    }


def get_accounting_dashboard(params):
    from apps.transactions.models import Invoice, Payment

    period = params.get('period_days', 30)
    cutoff = _cutoff_ms(period)
    now_ms = int(timezone.now().timestamp() * 1000)

    # AR — open invoices
    open_invoices = Invoice.objects.filter(
        status__in=['open', 'released'], balance__gt=0
    ).aggregate(count=Count('id'), total=Sum('balance'))

    # Aging buckets (based on dt_created)
    day_30 = now_ms - (30 * 86400000)
    day_60 = now_ms - (60 * 86400000)
    day_90 = now_ms - (90 * 86400000)
    ar_current = Invoice.objects.filter(status__in=['open', 'released'], balance__gt=0, dt_created__gte=day_30).aggregate(t=Sum('balance'))['t'] or 0
    ar_30_60 = Invoice.objects.filter(status__in=['open', 'released'], balance__gt=0, dt_created__lt=day_30, dt_created__gte=day_60).aggregate(t=Sum('balance'))['t'] or 0
    ar_60_90 = Invoice.objects.filter(status__in=['open', 'released'], balance__gt=0, dt_created__lt=day_60, dt_created__gte=day_90).aggregate(t=Sum('balance'))['t'] or 0
    ar_over_90 = Invoice.objects.filter(status__in=['open', 'released'], balance__gt=0, dt_created__lt=day_90).aggregate(t=Sum('balance'))['t'] or 0

    # Payments in period
    payments = Payment.objects.filter(dt_created__gte=cutoff).aggregate(
        count=Count('id'), total=Sum('total'))

    return {
        'ar': {
            'open_count': open_invoices['count'] or 0,
            'open_total': float(open_invoices['total'] or 0),
            'current': float(ar_current),
            '30_60': float(ar_30_60),
            '60_90': float(ar_60_90),
            'over_90': float(ar_over_90),
        },
        'payments': {
            'count': payments['count'] or 0,
            'total': float(payments['total'] or 0),
        },
    }
