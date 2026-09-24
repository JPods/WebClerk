"""A shipment invoices exactly the lines and quantities shipped.

Bill, 2026-09-23 (audit gap 4): through the one conversion engine, like any
order→invoice. No line-less invoices. ship_order used to convert every remaining line
whatever was packed, never saved the lines the engine returns for review — so the
invoice had none — and read result keys the engine does not return.
"""
import pytest

from apps.core.services.door import Actor
from tests.conftest import OrderFactory, OrderLineFactory

pytestmark = pytest.mark.django_db


def _order_with_two_lines():
    order = OrderFactory()
    a = OrderLineFactory(order=order, line_number=1, line_type='product',
                         quantity={'active': 10, 'remaining': 10}, price={'unit': 5, 'precision': 2})
    b = OrderLineFactory(order=order, line_number=2, line_type='product',
                         quantity={'active': 4, 'remaining': 4}, price={'unit': 7, 'precision': 2})
    return order, a, b


def _ship(order):
    from apps.transactions.services.fulfillment.fulfillment_ship import ship_order
    return ship_order(order.pk, {'carrier': 'UPS', 'tracking_number': '1Z'},
                      actor=Actor.system(source='command'))


def test_the_invoice_carries_exactly_what_was_packed():
    from apps.transactions.models import Invoice, InvoiceLine, OrderLine
    from apps.transactions.services.fulfillment.fulfillment_ship import confirm_pack

    order, a, b = _order_with_two_lines()
    confirm_pack(order.pk, [{'line_id': a.pk, 'qty_packed': 6}])

    result = _ship(order)

    invoice = Invoice.objects.get(pk=result['invoice_id'])
    lines = list(InvoiceLine.objects.filter(invoice=invoice))
    assert len(lines) == 1, "only the packed line, and never none"
    assert float(lines[0].quantity['active']) == 6
    assert lines[0].parent_line_id == a.pk
    assert result['lines_shipped'] == 1

    a.refresh_from_db(), b.refresh_from_db()
    assert float(a.quantity['remaining']) == 4, "the order line keeps what was not shipped"
    assert float(b.quantity['remaining']) == 4, "an unpacked line is untouched"

    order.refresh_from_db()
    packed = order.metadata['shipping']['packed_lines']
    assert all(pl.get('invoice_id') == invoice.pk for pl in packed)
    assert invoice.metadata['shipping']['carrier'] == 'UPS'


def test_shipping_twice_without_a_new_pack_is_refused():
    from apps.transactions.services.fulfillment.fulfillment_ship import confirm_pack

    order, a, _ = _order_with_two_lines()
    confirm_pack(order.pk, [{'line_id': a.pk, 'qty_packed': 2}])
    _ship(order)

    with pytest.raises(ValueError, match='nothing packed'):
        _ship(order)


def test_packing_more_than_is_left_to_invoice_is_refused_before_anything_is_saved():
    from apps.transactions.models import Invoice
    from apps.transactions.services.fulfillment.fulfillment_ship import confirm_pack

    order, _, b = _order_with_two_lines()
    confirm_pack(order.pk, [{'line_id': b.pk, 'qty_packed': 9}])
    before = Invoice.objects.count()

    with pytest.raises(ValueError, match='only 4'):
        _ship(order)

    assert Invoice.objects.count() == before, "the header rolls back with the refusal"
