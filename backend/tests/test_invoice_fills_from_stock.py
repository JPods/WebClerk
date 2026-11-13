"""Order → invoice takes what the order has left, up to what is in stock (Bill, 2026-11-13).

With R = the order line's remaining and H = the item's stock: the invoice takes min(R, max(H, 0))
and R less that stays on the order line. Stock is counted down in line order. A credit line (a
negative quantity) goes whole, and so does a line whose item holds no stock. The invoice line keeps
what was asked as ``staged``: staged − active is what did not ship. Nobody is asked for quantities.
"""
import pytest

from apps.core.services.door import Refused
from apps.transactions.models import InvoiceLine, Order, OrderLine
from apps.transactions.services.convert.convert import convert_order_to_invoice
from tests.test_stock_layers_follow_sales import _stocked

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]


def _order(*lines):
    from apps.orgs.models import OrgBase
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    order = Order.objects.create(status='confirmed', customer_id=buyer.pk, finance={'sales_tax_rate': 0})
    made = [OrderLine.objects.create(
        order=order, item={'item_id': item.pk, 'id_num': item.pk, 'description': item.name},
        quantity={'active': qty}, price={'unit': 10, 'precision': 2}, cost={'unit': 0})
        for item, qty in lines]
    return order, made


def _invoiced(result):
    return {l.parent_line_id: l for l in InvoiceLine.objects.filter(invoice_id=result['invoice_id'])}


def test_enough_in_stock_invoices_all_that_is_left():
    item, _ = _stocked()                                   # 15 on hand
    order, (line,) = _order((item, 6))
    result = convert_order_to_invoice(order.pk)
    assert _invoiced(result)[line.pk].quantity['active'] == 6
    line.refresh_from_db()
    assert line.quantity['remaining'] == 0
    assert not any('Not everything shipped' in m for m in result['messages'])


def test_short_stock_invoices_what_there_is_and_the_rest_stays_on_the_order():
    item, _ = _stocked(layers=((4, '1.00'),))              # 4 on hand
    order, (line,) = _order((item, 10))
    result = convert_order_to_invoice(order.pk)
    quantity = _invoiced(result)[line.pk].quantity
    assert (quantity['active'], quantity['staged']) == (4, 10)   # 6 did not ship
    line.refresh_from_db()
    assert line.quantity['remaining'] == 6
    item.refresh_from_db()
    assert item.quantity['on_hand'] == 0
    assert any('4 of 10 invoiced, 6 stays on the order' in m for m in result['messages'])


def test_two_lines_of_one_item_do_not_both_take_the_stock():
    item, _ = _stocked(layers=((5, '1.00'),))              # 5 on hand
    order, (first, second) = _order((item, 3), (item, 4))
    result = convert_order_to_invoice(order.pk)
    lines = _invoiced(result)
    assert lines[first.pk].quantity['active'] == 3
    assert lines[second.pk].quantity['active'] == 2
    second.refresh_from_db()
    assert second.quantity['remaining'] == 2


def test_a_line_with_nothing_in_stock_is_left_out_and_named():
    stocked, _ = _stocked(layers=((5, '1.00'),))
    from apps.products.models import Item
    empty = Item.objects.create(name='Gone', sku='GONE', quantity={'on_hand': 0, 'allocated': 0, 'available': 0})
    order, (has, has_not) = _order((stocked, 2), (empty, 3))
    result = convert_order_to_invoice(order.pk)
    assert set(_invoiced(result)) == {has.pk}
    has_not.refresh_from_db()
    assert has_not.quantity['remaining'] == 3
    assert any('GONE: 0 of 3 invoiced' in m for m in result['messages'])


def test_stock_below_zero_counts_as_none():
    from apps.products.models import Item
    item = Item.objects.create(name='Owed', sku='OWED', quantity={'on_hand': -2, 'allocated': 0, 'available': -2})
    order, (line,) = _order((item, 3))
    with pytest.raises(Refused) as refused:
        convert_order_to_invoice(order.pk)
    assert refused.value.code == 'nothing_in_stock'
    line.refresh_from_db()
    assert line.quantity['remaining'] == 3


def test_a_credit_line_goes_whole_and_adds_to_stock():
    item, _ = _stocked(layers=((1, '1.00'),))              # 1 on hand
    order, (line,) = _order((item, -4))
    result = convert_order_to_invoice(order.pk)
    assert _invoiced(result)[line.pk].quantity['active'] == -4
    item.refresh_from_db()
    assert item.quantity['on_hand'] == 5
    line.refresh_from_db()
    assert line.quantity['remaining'] == 0
