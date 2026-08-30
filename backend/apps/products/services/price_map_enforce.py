"""
MAP (Minimum Advertised Price) Enforcement Service — ORG-08

Checks sell prices against manufacturer MAP / MSRP thresholds.
Flags violations at item, order, and reporting levels.

All functions single-purpose. Called from wcapi/manage.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from decimal import Decimal
from django.apps import apps as dj_apps
import time


def _now_ms():
    return int(time.time() * 1000)


def _dec(v) -> Decimal:
    if v is None:
        return Decimal('0')
    return Decimal(str(v))


def check_map_violation(item_id: int, sell_price) -> Dict:
    """Check if sell_price < MAP for a single item.

    MAP source priority:
      1. item.price.msrp (most items store MAP = MSRP)
      2. ItemXRef manufacturer cost data (fallback)

    Returns: {violation, map_price, sell_price, difference, item_ida}
    """
    Item = dj_apps.get_model('products', 'Item')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return {'violation': False, 'error': f'Item {item_id} not found'}

    sell = _dec(sell_price)
    map_price = None

    # 1. Check item.price.msrp
    price_data = item.price or {}
    msrp_val = price_data.get('msrp')
    if msrp_val is not None:
        map_price = _dec(msrp_val)

    # 2. Fallback: check ItemXRef for manufacturer MAP price
    if map_price is None or map_price == 0:
        ItemXRef = dj_apps.get_model('products', 'ItemXRef')
        xrefs = ItemXRef.objects.filter(
            item_id=item_id,
            source='manufacturer',
        )
        for xref in xrefs:
            cost_data = xref.cost or {}
            xref_map = cost_data.get('map_price') or cost_data.get('msrp')
            if xref_map is not None:
                map_price = _dec(xref_map)
                break

    if map_price is None or map_price == 0:
        return {
            'violation': False,
            'map_price': None,
            'sell_price': str(sell),
            'difference': None,
            'item_ida': getattr(item, 'ida', ''),
            'note': 'No MAP/MSRP on file',
        }

    violation = sell < map_price
    return {
        'violation': violation,
        'map_price': str(map_price),
        'sell_price': str(sell),
        'difference': str(map_price - sell) if violation else '0',
        'item_ida': getattr(item, 'ida', ''),
    }


def check_order_map_violations(order_id: int) -> List[Dict]:
    """Check all lines in an order for MAP violations.

    Returns: list of violation dicts for lines that violate MAP.
    """
    OrderLine = dj_apps.get_model('transactions', 'OrderLine')

    lines = OrderLine.objects.filter(order_id=order_id)
    violations = []

    for line in lines:
        item_fk = line.item_id_fk_id if hasattr(line, 'item_id_fk_id') else None
        if not item_fk:
            continue

        price_data = line.price or {}
        unit_price = price_data.get('unit') or price_data.get('base')
        if unit_price is None:
            continue

        result = check_map_violation(item_fk, unit_price)
        if result.get('violation'):
            result['line_id'] = line.pk
            result['order_id'] = order_id
            violations.append(result)

    return violations


def get_map_violations_report(period_days: int = 30) -> List[Dict]:
    """Find all recent invoice lines where sell price < MAP.

    Scans invoices from the last `period_days` days.

    Returns: [{invoice_ida, line_id, item_ida, map_price, sell_price, customer, dt}]
    """
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')

    cutoff_ms = _now_ms() - (period_days * 86400 * 1000)

    invoices = Invoice.objects.filter(
        dt_created__gte=cutoff_ms,
        is_deleted=False,
    ).select_related('customer')

    violations = []

    for invoice in invoices:
        lines = InvoiceLine.objects.filter(invoice_id=invoice.pk)
        for line in lines:
            item_fk = line.item_id_fk_id if hasattr(line, 'item_id_fk_id') else None
            if not item_fk:
                continue

            price_data = line.price or {}
            unit_price = price_data.get('unit') or price_data.get('base')
            if unit_price is None:
                continue

            result = check_map_violation(item_fk, unit_price)
            if result.get('violation'):
                customer_name = ''
                if invoice.customer:
                    customer_name = getattr(invoice.customer, 'name', str(invoice.customer_id))

                violations.append({
                    'invoice_ida': getattr(invoice, 'ida', ''),
                    'line_id': line.pk,
                    'item_ida': result.get('item_ida', ''),
                    'map_price': result['map_price'],
                    'sell_price': result['sell_price'],
                    'customer': customer_name,
                    'dt': invoice.dt_created,
                })

    return violations
