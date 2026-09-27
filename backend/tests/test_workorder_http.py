"""The requests the stock screens send (frontend/src/api/workorderApi.ts), end to end over HTTP.

newRecord('workorder') → PUT /wcapi/workorder/<id>/ {kind, lines} → (build) expand → complete.
Guards the fields a correction depends on — kind, line_type, physical.layer_id, comments.process —
reaching the door, not being dropped on the way.
"""
from decimal import Decimal

import pytest

from tests.test_workorder_build import _bom, _item

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    from apps.products.models import Warehouse
    from tests.helpers.auth import make_authenticated_client
    Warehouse.objects.create(code='WH1', name='Main')
    return make_authenticated_client()


def _new_workorder(client, kind, lines):
    made = client.post('/wcapi/workorder/', {}, format='json')
    assert made.status_code in (200, 201), made.content
    wo_id = made.json()['data']['id']
    saved = client.put(f'/wcapi/workorder/{wo_id}/', {'kind': kind, 'lines': lines}, format='json')
    assert saved.status_code == 200, saved.content
    return wo_id


def _q(item):
    item.refresh_from_db()
    return float(item.quantity['on_hand'])


def test_a_count_and_an_adjustment_over_http(client):
    from apps.products.models.inventory_layer import InventoryLayer
    from apps.transactions.models import WorkOrder, WorkOrderLine
    frame = _item('Frame', stock='20', cost='5')
    tire = _item('Tire', stock='10', cost='2')
    layer = InventoryLayer.objects.get(item_id=tire.pk)
    wo_id = _new_workorder(client, 'count', [
        {'id': -1, 'line_type': 'count', 'item': {'item_id': frame.pk}, 'quantity': {'active': 18}},
        {'id': -2, 'line_type': 'adjust', 'item': {'item_id': tire.pk}, 'quantity': {'active': -3},
         'physical': {'layer_id': layer.pk}, 'comments': {'process': [{'mgs': 'three cut in receiving'}]}},
    ])
    assert WorkOrder.objects.get(pk=wo_id).kind == 'count'
    assert (_q(frame), _q(tire)) == (18, 7)
    adjust = WorkOrderLine.objects.get(workorder_id=wo_id, line_type='adjust')
    [event] = adjust.events
    assert event['reason'] == 'three cut in receiving' and event['layer_id'] == layer.pk
    [entry] = adjust.comments['process']
    assert entry['time'] and entry['user']            # stamped by the server: who and when
    layer.refresh_from_db()
    assert float(layer.quantity['issued']) == 3


def test_an_adjustment_without_its_reason_is_refused_over_http(client):
    tire = _item('Tire', stock='10', cost='2')
    made = client.post('/wcapi/workorder/', {}, format='json')
    wo_id = made.json()['data']['id']
    saved = client.put(f'/wcapi/workorder/{wo_id}/', {'kind': 'count', 'lines': [
        {'id': -1, 'line_type': 'adjust', 'item': {'item_id': tire.pk}, 'quantity': {'active': -1}}]},
        format='json')
    assert saved.status_code == 400
    assert saved.json()['error']['code'] == 'reason_required'
    assert _q(tire) == 10


def test_a_build_over_http(client):
    from apps.transactions.models import WorkOrderLine
    cart, wheel = _item('Cart'), _item('Wheel', stock='40', cost='8')
    _bom(cart, wheel, '4')
    wo_id = _new_workorder(client, 'production', [
        {'id': -1, 'line_type': 'build', 'item': {'item_id': cart.pk}, 'quantity': {'active': 10}}])
    build = WorkOrderLine.objects.get(workorder_id=wo_id, line_type='build')
    assert client.post(f'/wcapi/workorder/{wo_id}/expand/', {'line_id': build.pk, 'depth': 1},
                       format='json').status_code == 200
    done = client.post(f'/wcapi/workorder/{wo_id}/complete/', {}, format='json')
    assert done.status_code == 200, done.content
    assert (_q(cart), _q(wheel)) == (10, 0)
    build.refresh_from_db()
    assert build.events[0]['unit_cost'] == pytest.approx(float(Decimal('32')))   # 4 × 8


def test_a_line_payload_never_writes_events(client):
    """Events are what the applier did to a line; a request carrying them is refused."""
    tire = _item('Tire', stock='10', cost='2')
    made = client.post('/wcapi/workorder/', {}, format='json')
    wo_id = made.json()['data']['id']
    saved = client.put(f'/wcapi/workorder/{wo_id}/', {'kind': 'count', 'lines': [
        {'id': -1, 'line_type': 'count', 'item': {'item_id': tire.pk}, 'quantity': {'active': 10},
         'events': [{'id': 'forged', 'kind': 'count', 'qty': 500}]}]}, format='json')
    # Refused either by the role's enumeration (403, when its sets predate the events leaves)
    # or by the line engine (400 events_are_the_record); never saved.
    assert saved.status_code in (400, 403)
    assert saved.json()['error']['code'] in ('events_are_the_record', 'transaction_denied')
    assert _q(tire) == 10
