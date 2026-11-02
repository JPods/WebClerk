"""Shipped before received (Bill, 2026-11-02): "I must ship an invoice. The product arrived, but was
not yet received. So I ship it. The only issue is if the cost of goods is different, an adjustment
must be made when the receipt is processed."

Shipping short opens a deficit at the item's average cost. The receipt fills it first, from its new
layer; the receipt's journal posts those units' cost at the layer's cost — only the difference when
the invoice already posted them at the deficit's cost. Either way COGS ends at the real cost and GL
inventory equals what the layers hold.
"""
from decimal import Decimal

import pytest

from tests.test_stock_layers_follow_sales import _invoice, _line

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]

COGS, INVENTORY = '5000-cost_of_goods_sold', '1200-inventory'


def _run(verb, model, pk, data=None):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    return run_command(Actor.system(), verb, model, pk, data or {})


def _item(avg='3.00'):
    from apps.products.models import Item, Warehouse
    Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    return Item.objects.create(name='Widget', cost={'avg': float(avg)},
                               quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0, 'allocated': 0, 'available': 0})


def _receive(item, qty, unit):
    from apps.transactions.models import Purchase, PurchaseLine, Receipt
    po = Purchase.objects.create()
    pol = PurchaseLine.objects.create(purchase=po, item={'item_id': item.pk, 'description': item.name},
                                      quantity={'active': qty, 'staged': qty}, cost={'unit': unit, 'precision': 2})
    out = _run('convert', 'purchase', po.pk, {'to': 'receipt', 'lines': [{'line_id': pol.pk}]})
    receipt = Receipt.objects.get(pk=out['receipt_id'])
    _run('receive', 'receipt', receipt.pk)
    return receipt


def _net(account, *sources):
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(account=account)
    return round(sum((r.debit or 0) - (r.credit or 0) for r in rows
                     if (r.source_model, r.source_id) in sources), 2)


def _deficit(item):
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    return Pending.objects.get(purpose=DEFICIT_PURPOSE, record_id=str(item.pk))


def _layer_value(item):
    from apps.products.models.inventory_layer import InventoryLayer
    return round(sum(float(l.remaining_qty()) * float((l.cost or {}).get('landed') or 0)
                     for l in InventoryLayer.objects.filter(item_id=item.pk)), 2)


def test_invoice_posted_first_then_the_receipt_posts_the_difference():
    from apps.accounts.services.journalize import journalize_invoice
    item = _item('3.00')
    invoice = _invoice()
    _line(invoice, item, 3)                                 # none on the shelf: 3 short @ 3.00
    assert journalize_invoice(invoice.pk).get('created')
    assert _net(COGS, ('invoice', invoice.pk)) == 9.0

    receipt = _receive(item, 10, 4.0)                       # arrives at 4.00
    deficit = _deficit(item)
    assert deficit.dt_processed and deficit.incremental_remaining('deficit_qty') == 0
    out = _run('journalize', 'receipt', receipt.pk)
    assert out.get('created'), out

    both = (('invoice', invoice.pk), ('receipt', receipt.pk))
    assert _net(COGS, ('receipt', receipt.pk)) == 3.0       # 3 × (4.00 − 3.00)
    assert _net(COGS, *both) == 12.0                        # the real cost: 3 × 4.00
    assert _net(INVENTORY, *both) == _layer_value(item) == 28.0   # 7 left @ 4.00
    item.refresh_from_db()
    assert float(item.quantity['on_hand']) == 7.0


def test_receipt_before_the_invoice_posts_the_full_cost_once():
    from apps.accounts.services.journalize import journalize_invoice
    item = _item('3.00')
    invoice = _invoice()
    _line(invoice, item, 3)
    receipt = _receive(item, 10, 4.0)                       # filled before the invoice posts
    assert journalize_invoice(invoice.pk).get('created')
    assert _net(COGS, ('invoice', invoice.pk)) == 0.0       # nothing left short to post
    _run('journalize', 'receipt', receipt.pk)

    both = (('invoice', invoice.pk), ('receipt', receipt.pk))
    assert _net(COGS, *both) == 12.0
    assert _net(INVENTORY, *both) == _layer_value(item) == 28.0


def test_a_receipt_smaller_than_the_shortage_fills_part_of_it():
    item = _item('3.00')
    invoice = _invoice()
    _line(invoice, item, 5)                                 # 5 short
    _receive(item, 2, 4.0)
    deficit = _deficit(item)
    assert not deficit.dt_processed and deficit.incremental_remaining('deficit_qty') == 3
    assert _layer_value(item) == 0.0                        # both received units went out
