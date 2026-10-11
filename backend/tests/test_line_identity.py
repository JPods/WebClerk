"""A line's identity never changes, and a line changes only through its document.

A3-H-1 (FAULT 20260928T175045): `{"id": 5, "pk": 9999}` passed the lookup as line 5, then the
copy set its pk to 9999 and the save wrote over line 9999 of any document. Bill, 2026-10-07:
the fix is the server's — only a line's own fields are written, any other key is refused; a
line's item id, ida and uuid never change; and "we should block line record changes": a line
is not saved, made or deleted as a record of its own.
"""
import pytest

from apps.core.services.door import Actor, Refused

pytestmark = pytest.mark.django_db


def _item(ida):
    from apps.products.models import Item
    return Item.objects.create(ida=ida, name=ida)


def _order_with_line(item, quantity=5):
    from apps.transactions.models import Order, OrderLine
    order = Order.objects.create(status='open')
    line = OrderLine.objects.create(order=order, item_fk=item,
                                    item={'item_id': item.pk, 'ida_item': item.ida,
                                          'uuid_item': str(item.uuid)},
                                    quantity={'active': quantity}, status='open')
    return order, line


def _save(order, lines):
    from tests.utils import save_document
    return save_document('order', {'id': order.pk, 'status': 'open'}, lines)


def test_pk_in_a_line_is_refused_and_the_other_line_is_untouched():
    from apps.transactions.models import OrderLine
    item = _item('LID-1')
    order, mine = _order_with_line(item, 5)
    _other_order, theirs = _order_with_line(item, 7)

    with pytest.raises(Refused) as refused:
        _save(order, [{'id': mine.pk, 'pk': theirs.pk, '_dirty': True, 'quantity': {'active': 99}}])
    assert refused.value.code == 'unknown_field'
    theirs.refresh_from_db()
    assert theirs.order_id == _other_order.pk
    assert float(theirs.quantity['active']) == 7
    assert OrderLine.objects.get(pk=mine.pk).quantity['active'] == 5


def test_a_key_that_is_no_field_is_refused_not_dropped():
    item = _item('LID-2')
    order, line = _order_with_line(item)
    with pytest.raises(Refused) as refused:
        _save(order, [{'id': line.pk, '_dirty': True, 'qty': 3}])
    assert refused.value.code == 'unknown_field'
    assert 'qty' in refused.value.message


def test_an_echo_of_the_line_as_read_saves():
    """What the screen read comes back with an edit: the FK by name, the document, the ida."""
    item = _item('LID-3')
    order, line = _order_with_line(item)
    _save(order, [{'id': line.pk, '_dirty': True, 'order': order.pk, 'item_fk': item.pk,
                   'ida': line.ida, 'version': line.version,
                   'item': dict(line.item), 'quantity': {'active': 6}}])
    line.refresh_from_db()
    assert float(line.quantity['active']) == 6


@pytest.mark.parametrize('change', [
    {'item_fk': 'OTHER'},
    {'item': {'item_id': 'OTHER'}},
    {'item': {'ida_item': 'SOMETHING-ELSE'}},
    {'item': {'uuid_item': '00000000-0000-0000-0000-000000000000'}},
])
def test_a_saved_lines_item_never_changes(change):
    item, other = _item('LID-4'), _item('LID-4B')
    order, line = _order_with_line(item)
    payload = {'id': line.pk, '_dirty': True}
    for key, value in change.items():
        payload[key] = ({k: (other.pk if v == 'OTHER' else v) for k, v in value.items()}
                        if isinstance(value, dict) else (other.pk if value == 'OTHER' else value))
    with pytest.raises(Refused) as refused:
        _save(order, [payload])
    assert refused.value.code == 'line_item_change'
    line.refresh_from_db()
    assert line.item_fk_id == item.pk and line.item['ida_item'] == 'LID-4'


def test_a_line_cannot_move_to_another_document():
    from apps.transactions.models import Order
    item = _item('LID-5')
    order, line = _order_with_line(item)
    elsewhere = Order.objects.create(status='open')
    with pytest.raises(Refused) as refused:
        _save(order, [{'id': line.pk, '_dirty': True, 'order_id': elsewhere.pk}])
    assert refused.value.code == 'line_parent_change'


def test_a_lines_party_ids_are_its_headers_echo_saves_another_is_refused():
    """Bill, 2026-10-10: refused like the parent, not silently replaced."""
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Order
    acme = OrgBase.objects.create(company='Acme', org_type='customer')
    globex = OrgBase.objects.create(company='Globex', org_type='customer')
    item = _item('LID-5P')
    order, line = _order_with_line(item)
    Order.objects.filter(pk=order.pk).update(customer_id=acme.pk)
    order.refresh_from_db()
    _save(order, [{'id': line.pk, '_dirty': True, 'customer_id': acme.pk}])
    with pytest.raises(Refused) as refused:
        _save(order, [{'id': line.pk, '_dirty': True, 'customer_id': globex.pk}])
    assert refused.value.code == 'line_party_derived'


def test_a_stale_line_is_refused_412():
    item = _item('LID-6')
    order, line = _order_with_line(item)
    with pytest.raises(Refused) as refused:
        _save(order, [{'id': line.pk, '_dirty': True, 'version': (line.version or 0) + 5,
                       'quantity': {'active': 2}}])
    assert refused.value.status == 412


def test_a_new_line_takes_its_items_ida_and_uuid_from_the_item():
    from apps.transactions.models import Order, OrderLine
    item = _item('LID-7')
    order = Order.objects.create(status='open')
    created = _save(order, [{'id': None, 'item': {'item_id': item.pk}, 'quantity': {'active': 1}}])
    line = OrderLine.objects.get(pk=created['lines'][0]['id'])
    assert line.item_fk_id == item.pk
    assert line.item['ida_item'] == 'LID-7' and line.item['uuid_item'] == str(item.uuid)


def test_a_new_line_naming_two_items_is_refused():
    from apps.transactions.models import Order
    item, other = _item('LID-8'), _item('LID-8B')
    order = Order.objects.create(status='open')
    with pytest.raises(Refused) as refused:
        _save(order, [{'id': None, 'item': {'item_id': item.pk, 'ida_item': 'LID-8B'},
                       'quantity': {'active': 1}}])
    assert refused.value.code == 'line_item_mismatch'


@pytest.mark.parametrize('verb', ['save', 'new', 'delete'])
def test_a_line_is_not_a_record_of_its_own(verb):
    from apps.core.services.verbs import run
    item = _item(f'LID-9-{verb}')
    order, line = _order_with_line(item)
    payload = {'id': line.pk, 'quantity': {'active': 1}} if verb != 'new' else {'order_id': order.pk}
    with pytest.raises(Refused) as refused:
        run(Actor.system(source='test'), verb, 'order_line', payload)
    assert refused.value.code == 'line_through_document'
    line.refresh_from_db()
    assert line.quantity['active'] == 5
