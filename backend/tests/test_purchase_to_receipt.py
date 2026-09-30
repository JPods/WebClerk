"""Receiving is a convert, like order→invoice (Bill, 2026-09-27, R3).

POST /wcapi/purchase/<id>/convert/ {to: 'receipt', lines?: [{line_id, qty?}]} saves a planned
receipt through the door: without lines, everything left on the purchase; with them, only those
lines, each at the qty given. A receipt line keeps the purchase line's whole cost, and the two
costs are independent after that. More than is left is accepted and flagged to Alice.

Bill, 2026-09-30: the goods go on the shelf when the receipt is received, a step of its own. A
planned receipt holds them as staged; POST /wcapi/receipt/<id>/receive/ moves on_hand and on_rc,
drops the purchase line's remaining and creates each layer at the receipt's final cost, which
never changes after (2026-09-28).
"""
import pytest

from apps.core.models import Setting
from apps.core.models.pending import Pending
from apps.products.models import Item, Warehouse
from apps.transactions.models import Purchase, PurchaseLine, Receipt, ReceiptLine

pytestmark = pytest.mark.django_db

PO_COST = {'unit': 4.0, 'freight': 0.5, 'discount_percent': 10, 'precision': 2}


@pytest.fixture
def admin_client(client, django_user_model):
    admin = django_user_model.objects.create_user(email='receive@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    return client


def _convert(client, pk, body=None, source='purchase'):
    return client.post(f'/wcapi/{source}/{pk}/convert/', {'to': 'receipt', **(body or {})},
                       content_type='application/json')


def _data(r):
    d = r.json()['data']
    return d.get('result', d)


def _item(name):
    return Item.objects.create(name=name, quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                    'allocated': 0, 'available': 0})


def _po(*lines):
    """A purchase with a line per (item, ordered, cost)."""
    Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    po = Purchase.objects.create()
    pols = [PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'description': item.name},
        quantity={'active': ordered, 'staged': ordered}, cost=dict(cost))
        for item, ordered, cost in lines]
    return po, pols


def _receive(client, receipt_id, body=None):
    return client.post(f'/wcapi/receipt/{receipt_id}/receive/', body or {},
                       content_type='application/json')


def _stock(item):
    item.refresh_from_db()
    q = item.quantity
    return q.get('on_hand'), q.get('on_rc'), q.get('on_po')


def _remaining(pol):
    pol.refresh_from_db()
    return pol.quantity.get('remaining')


def test_a_planned_receipt_takes_everything_left_and_holds_it_until_received(admin_client):
    a, b = _item('Widget'), _item('Gadget')
    po, (pa, pb) = _po((a, 10, PO_COST), (b, 5, {'unit': 9.5}))
    r = _convert(admin_client, po.pk)
    assert r.status_code == 200, r.content
    receipt = Receipt.objects.get(pk=_data(r)['receipt_id'])
    assert receipt.ida, 'the core model assigns the number'
    assert (receipt.status, receipt.parent_model, receipt.parent_id) == ('planned', 'purchase', po.pk)
    lines = {line.parent_line_id: line for line in ReceiptLine.objects.filter(receipt=receipt)}
    assert set(lines) == {pa.pk, pb.pk}
    assert (lines[pa.pk].quantity['staged'], lines[pa.pk].quantity['active']) == (10, 0)
    pa.refresh_from_db()
    assert lines[pa.pk].cost == pa.cost, 'the receipt line takes the purchase line\'s whole cost'
    assert _stock(a) == (0, 0, 10), 'planned: nothing on the shelf, still on order'
    assert not any(line.inventory_layer_id for line in lines.values())

    r = _receive(admin_client, receipt.pk)
    assert r.status_code == 200, r.content
    lines = {line.parent_line_id: line for line in ReceiptLine.objects.filter(receipt=receipt)}
    assert lines[pa.pk].quantity['active'] == 10 and lines[pb.pk].quantity['active'] == 5
    assert _stock(a) == (10, 10, 0) and _stock(b) == (5, 5, 0)
    layer = lines[pa.pk].inventory_layer
    assert layer.cost['unit_po'] == 4.0
    assert (layer.parent_model, layer.parent_id) == ('receiptline', lines[pa.pk].pk)
    for item in (a, b):
        line = next(l for l in lines.values() if l.item_fk_id == item.pk)
        assert Pending.objects.filter(record_id=str(item.pk), purpose='inventory_line_add',
                                      changes__layer__line_id=line.pk).count() == 1
    assert _remaining(pa) == 0 and _remaining(pb) == 0
    r = _receive(admin_client, receipt.pk)
    assert r.status_code == 400 and r.json()['error']['code'] == 'nothing_to_receive', r.content


def test_a_partial_receipt_then_what_is_left_then_nothing(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    first = _data(_convert(admin_client, po.pk, {'lines': [{'line_id': pa.pk, 'qty': 7}]}))['receipt_id']
    r = _convert(admin_client, po.pk)
    assert r.status_code == 200, r.content
    second = ReceiptLine.objects.get(receipt_id=_data(r)['receipt_id'])
    assert second.quantity['staged'] == 3, 'what open receipts plan is not planned again'
    r = _convert(admin_client, po.pk)
    assert r.status_code == 400 and r.json()['error']['code'] == 'nothing_to_convert', r.content
    assert _receive(admin_client, first).status_code == 200
    assert _stock(a) == (7, 7, 3) and _remaining(pa) == 3
    assert _receive(admin_client, second.receipt_id).status_code == 200
    assert _stock(a) == (10, 10, 0)


def test_named_lines_convert_and_receive_only_those(admin_client):
    a, b = _item('Widget'), _item('Gadget')
    po, (pa, pb) = _po((a, 10, PO_COST), (b, 5, {'unit': 9.5}))
    r = _convert(admin_client, po.pk)
    receipt_id = _data(r)['receipt_id']
    lb = ReceiptLine.objects.get(receipt_id=receipt_id, parent_line_id=pb.pk)
    la = ReceiptLine.objects.get(receipt_id=receipt_id, parent_line_id=pa.pk)
    assert _receive(admin_client, receipt_id, {'lines': [{'line_id': lb.pk}]}).status_code == 200
    assert _stock(a) == (0, 0, 10) and _stock(b) == (5, 5, 0)
    assert _receive(admin_client, receipt_id, {'lines': [{'line_id': la.pk, 'qty': 4}]}).status_code == 200
    assert _stock(a) == (4, 4, 6)


def test_the_cost_is_edited_before_receiving_and_fixed_after(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    pa.refresh_from_db()
    receipt_id = _data(_convert(admin_client, po.pk))['receipt_id']
    line = ReceiptLine.objects.get(receipt_id=receipt_id)
    r = admin_client.patch(f'/wcapi/receipt/{receipt_id}/',
                           {'lines': [{'id': line.pk, 'cost': {'unit': 4.25}}]},
                           content_type='application/json')
    assert r.status_code == 200, r.content
    before = dict(pa.cost)
    pa.refresh_from_db()
    assert pa.cost == before, 'a receipt cost never writes back to the purchase'
    assert _receive(admin_client, receipt_id).status_code == 200
    line.refresh_from_db()
    layer_cost = dict(line.inventory_layer.cost)
    assert line.inventory_layer.cost['unit_po'] == 4.25, 'the layer is born at the receipt cost'
    r = admin_client.patch(f'/wcapi/receipt/{receipt_id}/',
                           {'lines': [{'id': line.pk, 'cost': {'unit': 5.0}}]},
                           content_type='application/json')
    assert r.status_code == 409 and r.json()['error']['code'] == 'layer_cost_fixed', r.content
    line.refresh_from_db()
    assert line.inventory_layer.cost == layer_cost, 'a layer never changes'


def test_a_request_cannot_receive_by_setting_active(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    receipt_id = _data(_convert(admin_client, po.pk))['receipt_id']
    line = ReceiptLine.objects.get(receipt_id=receipt_id)
    r = admin_client.patch(f'/wcapi/receipt/{receipt_id}/',
                           {'lines': [{'id': line.pk, 'quantity': {'active': 10}}]},
                           content_type='application/json')
    assert r.status_code == 400 and r.json()['error']['code'] == 'receive_command', r.content
    assert _stock(a) == (0, 0, 10)


def test_an_over_shipment_is_accepted_and_flagged_to_alice_once(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    r = _convert(admin_client, po.pk, {'lines': [{'line_id': pa.pk, 'qty': 12}]})
    assert r.status_code == 200, r.content
    receipt_id = _data(r)['receipt_id']
    notes = Setting.objects.filter(purpose='alice_pending', role='action_required',
                                   config__kind='over_receipt', config__purchase_line_id=pa.pk)
    assert not notes.exists(), 'planned: nothing received yet'
    assert _receive(admin_client, receipt_id).status_code == 200
    assert _stock(a)[0] == 12
    assert notes.count() == 1
    assert (notes[0].config['ordered'], notes[0].config['received']) == (10, 12)
    line = ReceiptLine.objects.get(receipt_id=receipt_id)
    assert admin_client.patch(f'/wcapi/receipt/{receipt_id}/', {'lines': [{'id': line.pk, 'lot': 'L1'}]},
                              content_type='application/json').status_code == 200
    assert notes.count() == 1, 'a re-save does not repeat the flag'


def test_a_receipt_within_the_order_raises_no_flag(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    assert _convert(admin_client, po.pk).status_code == 200
    assert not Setting.objects.filter(purpose='alice_pending', config__kind='over_receipt').exists()


@pytest.mark.parametrize('lines, code', [
    ([], 'lines_required'),
    ([{'qty': 1}], 'line_id_required'),
    ([{'line_id': 'PA', 'qty': 0}], 'qty_not_positive'),
    ([{'line_id': 'PA', 'qty': -2}], 'qty_not_positive'),
    ([{'line_id': 'OTHER', 'qty': 1}], 'no_lines'),
])
def test_refusals_are_coached_and_receive_nothing(admin_client, lines, code):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    _other, (other,) = _po((a, 3, PO_COST))
    ids = {'PA': pa.pk, 'OTHER': other.pk}
    held = _stock(a)
    body = {'lines': [{**row, 'line_id': ids[row['line_id']]} if 'line_id' in row else row
                      for row in lines]}
    r = _convert(admin_client, po.pk, body)
    assert r.status_code == 400 and r.json()['error']['code'] == code, r.content
    assert not Receipt.objects.exists()
    assert _stock(a) == held, 'nothing moved'


def test_a_role_that_may_not_change_purchases_is_refused(client, django_user_model):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    customer = django_user_model.objects.create_user(email='portal@test.com', password='x',
                                                     username='', role='customer')
    client.force_login(customer)
    r = _convert(client, po.pk)
    assert r.status_code in (403, 404), r.content
    assert not Receipt.objects.exists()


def test_the_old_receive_routes_are_gone(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    for path, body in ((f'/wcapi/purchase/{po.pk}/receive-goods/',
                        {'receipt_id': 'R-1', 'lines': [{'po_line_id': pa.pk, 'qty': 1,
                                                         'warehouse_code': 'MAIN'}]}),
                       (f'/wcapi/purchase/{po.pk}/receive/',
                        {'lines': [{'po_line_id': pa.pk, 'qty': 1}]})):
        r = admin_client.post(path, body, content_type='application/json')
        assert r.status_code in (400, 404, 405), r.content
    assert not Receipt.objects.exists()


# ── the other pairs keep their rules ───────────────────────────────────────────────

def _order(item, ordered):
    from apps.transactions.models import Order, OrderLine
    order = Order.objects.create()
    line = OrderLine.objects.create(order=order, item_fk=item,
                                    item={'item_id': item.pk, 'description': item.name},
                                    quantity={'active': ordered, 'staged': ordered},
                                    price={'unit': 20.0}, cost={'unit': 1.0})
    return order, line


def test_order_to_invoice_still_refuses_more_than_is_left(admin_client):
    a = _item('Widget')
    Item.objects.filter(pk=a.pk).update(quantity={'on_hand': 50, 'on_po': 0, 'on_rc': 0,
                                                  'allocated': 0, 'available': 50})
    order, line = _order(a, 4)
    # A person's named-line invoice passes the door: invoice lines declare the leaves the
    # convert copies (Bill, 2026-09-28). Only the quantity is refused.
    r = admin_client.post(f'/wcapi/order/{order.pk}/convert/',
                          {'to': 'invoice', 'lines': [{'line_id': line.pk, 'qty': 5}]},
                          content_type='application/json')
    assert r.status_code == 400, r.content
    assert b'transfer_exceeds_remaining' in r.content


def test_a_person_invoices_named_order_lines(admin_client):
    a = _item('Widget')
    Item.objects.filter(pk=a.pk).update(quantity={'on_hand': 50, 'on_po': 0, 'on_rc': 0,
                                                  'allocated': 0, 'available': 50})
    order, line = _order(a, 4)
    r = admin_client.post(f'/wcapi/order/{order.pk}/convert/',
                          {'to': 'invoice', 'lines': [{'line_id': line.pk, 'qty': 3}]},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    from apps.transactions.models import InvoiceLine
    (inv_line,) = InvoiceLine.objects.filter(refs__source__order_line_id=line.pk)
    assert float(inv_line.quantity['active']) == 3


def test_order_to_purchase_still_takes_the_item_cost(admin_client):
    a = _item('Widget')
    Item.objects.filter(pk=a.pk).update(cost={'standard': 3.0})
    order, line = _order(a, 4)
    r = admin_client.post(f'/wcapi/order/{order.pk}/convert/', {'to': 'purchase'},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    (review,) = _data(r)['lines']
    assert review['cost']['unit'] == 3.0, 'a purchase pays the item cost, not the sell estimate'


# ── the line engine refuses what it cannot write (found building R3, 2026-09-27) ─────────

def test_lines_sent_to_a_model_without_lines_are_refused_not_dropped(admin_client):
    item = _item('No lines here')
    r = admin_client.patch(f'/wcapi/item/{item.pk}/', {'name': 'Changed', 'lines': [{'x': 1}]},
                           content_type='application/json')
    assert r.status_code == 400, r.content
    assert b'lines_not_accepted' in r.content
    item.refresh_from_db()
    assert item.name == 'No lines here'
