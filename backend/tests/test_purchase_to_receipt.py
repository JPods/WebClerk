"""Receiving is a convert, like order→invoice (Bill, 2026-09-27, R3).

POST /wcapi/purchase/<id>/convert/ {to: 'receipt'} makes the receipt's parent; its first save names
the lines ({_from: purchase line id, quantity?}) and receives them (Bill, 2026-11-13): every proposed
line, or only those named, each at the qty given. A receipt line keeps the purchase line's whole cost, and the two costs are independent
after that. More than is left is accepted and flagged to Alice.

Bill, 2026-11-11 (readme 108): saving a receipt receives the goods (R1) — on_hand, on_rc, the purchase
line's remaining and the layer move at the save, at the cost cited. There is no hold (Bill,
2026-11-13: a receipt is made when the goods are here). A received line's dock cost never changes (R3).
"""
import pytest

from apps.core.models.pending import Pending
from apps.orgs.models import Vendor
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
    """Convert, then the first save (Bill, 2026-11-13): the save is what receives."""
    from tests.utils import convert_then_save
    return convert_then_save(client, source, pk, 'receipt', lines=(body or {}).get('lines'))


def _data(r):
    d = r.json()['data']
    return d.get('result', d)


def _item(name):
    return Item.objects.create(name=name, quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                    'allocated': 0, 'available': 0})


def _po(*lines):
    """A purchase from a vendor with a line per (item, ordered, cost). No terms on purpose:
    receiving needs the vendor and lines; the terms bind at the bill (the lead, 2026-11-06)."""
    Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    vendor, _ = Vendor.objects.get_or_create(company='Receiving Vendor', defaults={'is_active': True})
    po = Purchase.objects.create(vendor_id=vendor.pk)
    pols = [PurchaseLine.objects.create(
        purchase=po, item={'item_id': item.pk, 'description': item.name},
        quantity={'active': ordered, 'staged': ordered}, cost=dict(cost))
        for item, ordered, cost in lines]
    return po, pols


def _stock(item):
    item.refresh_from_db()
    q = item.quantity
    return q.get('on_hand'), q.get('on_rc'), q.get('on_po')


def _remaining(pol):
    pol.refresh_from_db()
    return pol.quantity.get('remaining')


def test_a_saved_receipt_takes_everything_left_and_receives_it(admin_client):
    a, b = _item('Widget'), _item('Gadget')
    po, (pa, pb) = _po((a, 10, PO_COST), (b, 5, {'unit': 9.5}))
    r = _convert(admin_client, po.pk)
    assert r.status_code == 200, r.content
    receipt = Receipt.objects.get(pk=_data(r)['receipt_id'])
    assert receipt.ida, 'the core model assigns the number'
    assert receipt.vendor_id == po.vendor_id, 'the receipt is from the purchase\'s vendor'
    assert (receipt.parent_model, receipt.parent_id) == ('purchase', po.pk)
    lines = {line.parent_line_id: line for line in ReceiptLine.objects.filter(receipt=receipt)}
    assert set(lines) == {pa.pk, pb.pk}
    assert lines[pa.pk].quantity['active'] == 10 and lines[pb.pk].quantity['active'] == 5
    pa.refresh_from_db()
    assert lines[pa.pk].cost == pa.cost, 'the receipt line takes the purchase line\'s whole cost'
    assert _stock(a) == (10, 10, 0) and _stock(b) == (5, 5, 0), 'on the shelf at the save'
    layer = lines[pa.pk].inventory_layer
    assert (layer.parent_model, layer.parent_id) == ('receiptline', lines[pa.pk].pk)
    assert layer.quantity['received'] == 10
    for item in (a, b):
        line = next(l for l in lines.values() if l.item_fk_id == item.pk)
        assert Pending.objects.filter(record_id=str(item.pk), purpose='inventory_line_add',
                                      changes__layer__line_id=line.pk).count() == 1
    assert _remaining(pa) == 0 and _remaining(pb) == 0


def test_a_receipt_has_no_receive_command(admin_client):
    """Bill, 2026-11-13: no hold, so nothing waits for a second step."""
    a = _item('Widget')
    po, _ = _po((a, 10, PO_COST))
    receipt_id = _data(_convert(admin_client, po.pk))['receipt_id']
    r = admin_client.post(f'/wcapi/receipt/{receipt_id}/receive/', {}, content_type='application/json')
    assert r.status_code == 404 and r.json()['error']['code'] == 'unknown_command', r.content


def test_a_partial_receipt_then_what_is_left_then_nothing(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    r = _convert(admin_client, po.pk, {'lines': [{'line_id': pa.pk, 'qty': 7}]})
    assert r.status_code == 200, r.content
    assert _stock(a) == (7, 7, 3) and _remaining(pa) == 3
    r = _convert(admin_client, po.pk)
    assert r.status_code == 200, r.content
    second = ReceiptLine.objects.get(receipt_id=_data(r)['receipt_id'])
    assert second.quantity['active'] == 3, 'what is received is not received again'
    assert _stock(a) == (10, 10, 0)
    r = _convert(admin_client, po.pk)
    assert r.status_code == 400 and r.json()['error']['code'] == 'nothing_to_convert', r.content


def test_named_lines_receive_only_those(admin_client):
    a, b = _item('Widget'), _item('Gadget')
    po, (pa, pb) = _po((a, 10, PO_COST), (b, 5, {'unit': 9.5}))
    assert _convert(admin_client, po.pk, {'lines': [{'line_id': pb.pk}]}).status_code == 200
    assert _stock(a) == (0, 0, 10) and _stock(b) == (5, 5, 0)
    assert _convert(admin_client, po.pk, {'lines': [{'line_id': pa.pk, 'qty': 4}]}).status_code == 200
    assert _stock(a) == (4, 4, 6)


def test_the_cost_is_fixed_once_received(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    pa.refresh_from_db()
    before = dict(pa.cost)
    receipt_id = _data(_convert(admin_client, po.pk))['receipt_id']
    line = ReceiptLine.objects.get(receipt_id=receipt_id)
    layer_cost = dict(line.inventory_layer.cost)
    r = admin_client.patch(f'/wcapi/receipt/{receipt_id}/',
                           {'lines': [{'id': line.pk, 'cost': {'unit': 5.0}}]},
                           content_type='application/json')
    assert r.status_code == 409 and r.json()['error']['code'] == 'layer_cost_fixed', r.content
    line.refresh_from_db()
    assert line.inventory_layer.cost == layer_cost, 'the dock cost never changes (R3)'
    pa.refresh_from_db()
    assert pa.cost == before, 'a receipt cost never writes back to the purchase'


def test_a_received_quantity_is_corrected_by_a_save(admin_client):
    """The vendor sent less than was asked: the line's quantity is lowered, and the stock, the layer
    and the purchase line's remaining follow. What the purchase asked stays on the line as staged."""
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    receipt_id = _data(_convert(admin_client, po.pk))['receipt_id']
    line = ReceiptLine.objects.get(receipt_id=receipt_id)
    r = admin_client.patch(f'/wcapi/receipt/{receipt_id}/',
                           {'lines': [{'id': line.pk, 'quantity': {'active': 6}}]},
                           content_type='application/json')
    assert r.status_code == 200, r.content
    assert _stock(a) == (6, 6, 4) and _remaining(pa) == 4
    line.refresh_from_db()
    assert line.inventory_layer.quantity['received'] == 6
    assert (line.quantity['staged'], line.quantity['active']) == (10, 6)


def test_the_discounted_unit_and_a_header_freight_share_reach_the_layer_born_at_a_plain_save(admin_client):
    """Found building readme 108 step 1: a line's door runs in its post_save, before the unit of work
    computes the receipt's totals, so a layer born there read the totals as they stood before the
    save — the discounted unit and the header freight share of the old quantities. The stock write
    now waits for the totals, so each layer carries the engine's discounted unit and its share."""
    from apps.products.models import Warehouse
    a, b = _item('Widget'), _item('Gadget')
    wh, _ = Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    vendor = Receipt._meta.get_field('vendor').related_model.objects.create(company='Plain Save Vendor')
    r = admin_client.post('/wcapi/receipt/', {}, content_type='application/json')   # the new verb
    assert r.status_code in (200, 201), r.content
    receipt_id = r.json()['data']['id']
    def put(body):
        r = admin_client.put(f'/wcapi/receipt/{receipt_id}/', body, content_type='application/json')
        assert r.status_code == 200, r.content
    # The lines first (nothing received yet), then the freight they carry; then one save receives
    # both, so the freight's split depends on both lines' totals at that save.
    put({'vendor_id': vendor.pk, 'lines': [
        {'item_fk_id': a.pk, 'item': {'item_id': a.pk}, 'warehouse_id': wh.pk, 'line_number': 10,
         'quantity': {'active': 0, 'staged': 10}, 'cost': {'unit': 4.0, 'discount_percent': 10, 'precision': 2}},
        {'item_fk_id': b.pk, 'item': {'item_id': b.pk}, 'warehouse_id': wh.pk, 'line_number': 20,
         'quantity': {'active': 0, 'staged': 5}, 'cost': {'unit': 12.0, 'precision': 2}}]})
    put({'allocations': {'freight': 30}})
    la, lb = (ReceiptLine.objects.get(item_fk_id=i.pk) for i in (a, b))
    assert _stock(a)[0] == 0
    put({'lines': [{'id': la.pk, 'quantity': {'active': 10, 'staged': 10}},
                   {'id': lb.pk, 'quantity': {'active': 5, 'staged': 5}}]})
    la.refresh_from_db(); lb.refresh_from_db()
    assert _stock(a)[0] == 10 and _stock(b)[0] == 5
    for line in (la, lb):
        layer = line.inventory_layer
        totals = line.totals
        assert layer.cost['unit_po'] == pytest.approx(float(totals['discounted_unit']))
        assert layer.cost['freight'] == pytest.approx(float(totals['landed']['freight']) / line.quantity['active'], abs=1e-4)
    shares = sum(float(l.totals['landed']['freight']) for l in (la, lb))
    assert shares == pytest.approx(30), 'the freight is spread over both lines, not all on the first'
    assert la.inventory_layer.cost['freight'] > 0 and lb.inventory_layer.cost['freight'] > 0


def test_an_over_shipment_is_accepted_and_flagged_to_alice_once(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    r = _convert(admin_client, po.pk, {'lines': [{'line_id': pa.pk, 'qty': 12}]})
    assert r.status_code == 200, r.content
    receipt_id = _data(r)['receipt_id']
    from apps.ai_assistant.services.notes import open_alice_actions
    notes = open_alice_actions('action_required', kind='over_receipt', purchase_line_id=pa.pk)
    assert _stock(a)[0] == 12
    assert notes.count() == 1, 'received at the save, so flagged at the save'
    details = notes[0].config['alice']['details']
    assert (details['ordered'], details['received']) == (10, 12)
    line = ReceiptLine.objects.get(receipt_id=receipt_id)
    assert admin_client.patch(f'/wcapi/receipt/{receipt_id}/', {'lines': [{'id': line.pk, 'lot': 'L1'}]},
                              content_type='application/json').status_code == 200
    assert notes.count() == 1, 'a re-save does not repeat the flag'


def test_a_receipt_within_the_order_raises_no_flag(admin_client):
    a = _item('Widget')
    po, (pa,) = _po((a, 10, PO_COST))
    assert _convert(admin_client, po.pk).status_code == 200
    from apps.ai_assistant.services.notes import open_alice_actions
    assert not open_alice_actions('action_required', kind='over_receipt').exists()


@pytest.mark.parametrize('lines, code', [
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
    assert not ReceiptLine.objects.exists()
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
    """An order a person can invoice: a customer, terms and a line (invoicing is a money step)."""
    from apps.orgs.models import Customer
    from apps.transactions.models import Order, OrderLine
    buyer, _ = Customer.objects.get_or_create(company='Invoiced Customer', defaults={'is_active': True})
    order = Order.objects.create(customer_id=buyer.pk, terms='N30')
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
    from tests.utils import convert_then_save
    r = convert_then_save(admin_client, 'order', order.pk, 'invoice', lines=[{'line_id': line.pk, 'qty': 5}])
    assert r.status_code == 400, r.content
    assert b'transfer_exceeds_remaining' in r.content


def test_a_person_invoices_named_order_lines(admin_client):
    a = _item('Widget')
    Item.objects.filter(pk=a.pk).update(quantity={'on_hand': 50, 'on_po': 0, 'on_rc': 0,
                                                  'allocated': 0, 'available': 50})
    order, line = _order(a, 4)
    from tests.utils import convert_then_save
    r = convert_then_save(admin_client, 'order', order.pk, 'invoice', lines=[{'line_id': line.pk, 'qty': 3}])
    assert r.status_code == 200, r.content
    from apps.transactions.models import InvoiceLine
    (inv_line,) = InvoiceLine.objects.filter(refs__source__order_line_id=line.pk)
    assert float(inv_line.quantity['active']) == 3


def test_order_to_purchase_still_takes_the_item_cost(admin_client):
    a = _item('Widget')
    Item.objects.filter(pk=a.pk).update(cost={'standard': 3.0})
    order, line = _order(a, 4)
    from tests.utils import convert_then_save
    r = convert_then_save(admin_client, 'order', order.pk, 'purchase')
    assert r.status_code == 200, r.content
    (saved,) = PurchaseLine.objects.filter(purchase_id=_data(r)['purchase_id'])
    assert saved.cost['unit'] == 3.0, 'a purchase pays the item cost, not the sell estimate'


# ── the line engine refuses what it cannot write (found building R3, 2026-09-27) ─────────

def test_lines_sent_to_a_model_without_lines_are_refused_not_dropped(admin_client):
    item = _item('No lines here')
    r = admin_client.patch(f'/wcapi/item/{item.pk}/', {'name': 'Changed', 'lines': [{'x': 1}]},
                           content_type='application/json')
    assert r.status_code == 400, r.content
    assert b'lines_not_accepted' in r.content
    item.refresh_from_db()
    assert item.name == 'No lines here'


def test_a_receipt_carries_its_purchases_vendor_block_as_it_stood(admin_client):
    """Readme 109: the receipt's one party block is the vendor, copied from the purchase — a
    snapshot, so a vendor who moves later does not move on the receipt. Read on the wire."""
    a = _item('RCV-VEND-A')
    po, _ = _po((a, 2, {'unit': '5.00'}))
    then = {'contact_id': None, 'company': 'Parts Inc', 'attention': 'Sal',
            'full_address': '9 Mill St, Denver, CO 80201', 'instructions': ''}
    Purchase.objects.filter(pk=po.pk).update(addresses={'vendor': then}, phones={'vendor': {'number': '303-555-0100'}})
    Vendor.objects.filter(pk=po.vendor_id).update(addresses={'bill_to': {**then, 'full_address': 'Moved Away 1'}})
    receipt_id = _data(_convert(admin_client, po.pk))['receipt_id']
    record = admin_client.get(f'/wcapi/receipt/{receipt_id}/', HTTP_HOST='localhost').json()
    record = record.get('data', record)
    record = record.get('record', record)
    assert record['addresses'] == {'vendor': then}
    assert record['phones']['vendor']['number'] == '303-555-0100'
    assert set(record['company']) == {'id', 'ida', 'name', 'is_individual'}


def test_a_receipt_has_no_ship_to_to_search_for(admin_client):
    a = _item('RCV-NOSHIP-A')
    po, _ = _po((a, 1, {'unit': '5.00'}))
    receipt = Receipt.objects.get(pk=_data(_convert(admin_client, po.pk))['receipt_id'])
    import json
    r = admin_client.put(f'/wcapi/receipt/{receipt.pk}/',
                         json.dumps({'id': receipt.pk, 'version': receipt.version,
                                     '_ship_to_from': {'model': 'customer', 'id': 1}}),
                         content_type='application/json', HTTP_HOST='localhost')
    assert r.status_code == 400 and 'no_ship_to' in r.content.decode(), r.content
