"""An invoice's COGS is what its layers gave, never the item's cost (GL-by-layer step 5;
Bill 2026-09-28/30): each movement at its layer's fixed cost, plus what the lines took short (an
open deficit) at the average it opened at. GL inventory then leaves exactly as the layers did.
"""
from decimal import Decimal

import pytest

from tests.test_stock_layers_follow_sales import _invoice, _line, _set, _stocked

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]


def _net(invoice, account):
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice', account=account)
    return round(sum((r.debit or 0) - (r.credit or 0) for r in rows), 2)


def _journalize(invoice):
    from apps.accounts.services.journalize import journalize_invoice
    out = journalize_invoice(invoice.pk)
    assert out.get('created'), out
    return out


def test_cogs_is_the_consumed_layers_cost_not_the_items():
    from apps.products.models import Item
    from apps.products.models.inventory_layer import InventoryMovement
    item, _ = _stocked()                                # layers 5 @ 1, 5 @ 2, 5 @ 3 (FIFO)
    Item.objects.filter(pk=item.pk).update(cost={'standard': 9.0, 'average': 9.0})
    invoice = _invoice()
    _line(invoice, item, 7)                             # 5 @ 1 + 2 @ 2 = 9.00
    _journalize(invoice)
    assert _net(invoice, '5000-cost_of_goods_sold') == 9.0
    assert _net(invoice, '1200-inventory') == -9.0
    assert all(m.dt_journaled > 0 for m in InventoryMovement.objects.filter(parent_model='invoiceline'))


def test_a_give_back_before_posting_nets_out():
    item, _ = _stocked()
    invoice = _invoice()
    line = _line(invoice, item, 7)
    _set(line, 5)                                       # 2 @ 2 come back
    _journalize(invoice)
    assert _net(invoice, '5000-cost_of_goods_sold') == 5.0


def test_a_short_sale_costs_the_shortfall_at_the_deficit_average():
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    item, _ = _stocked(layers=((2, '4.00'),))
    invoice = _invoice()
    _line(invoice, item, 3)                             # 2 @ 4 from the layer, 1 short
    deficit = Pending.objects.get(purpose=DEFICIT_PURPOSE, record_id=str(item.pk))
    short_cost = Decimal(str(deficit.changes['unit_cost']))
    _journalize(invoice)
    assert _net(invoice, '5000-cost_of_goods_sold') == float((8 + short_cost).quantize(Decimal('0.01')))
