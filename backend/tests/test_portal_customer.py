"""What a customer may do (Bill, 2026-09-28).

"Customers should only be able to place new orders, pay for them, and add a limited number of
action records to request support" — plus their own contact (editable), their own customer
record, their quotes and invoices, and the published catalog with images. Everything else:
no block, no rows. The table is access.PORTAL_CUSTOMER_ACCESS; narrow_portal_access puts it
on the wc:model Settings.
"""
import pytest
from django.core.management import call_command

from apps.core.models import Action, Contact
from apps.core.services import access
from apps.core.services.door import Actor, Refused
from apps.core.services.record_serialize import visible_queryset
from apps.core.services.save import save_record
from apps.core.services.verbs import run_command
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Order

pytestmark = pytest.mark.django_db


@pytest.fixture
def world():
    call_command('narrow_portal_access', '--apply')
    mine = OrgBase.objects.create(company='Acme', org_type='customer', security_level=1)
    theirs = OrgBase.objects.create(company='Globex', org_type='customer', security_level=1)
    me = Contact.objects.create(email='buyer@acme.example', role='customer', customer_id=mine.pk,
                                security_level=1)
    other = Contact.objects.create(email='buyer@globex.example', role='customer',
                                   customer_id=theirs.pk)
    my_order = Order.objects.create(customer_id=mine.pk, security_level=1)
    their_order = Order.objects.create(customer_id=theirs.pk, security_level=1)
    return {'me': Actor(user=me), 'me_contact': me, 'other': other, 'mine': mine,
            'theirs': theirs, 'my_order': my_order, 'their_order': their_order}


def _visible(actor, model_key):
    return set(visible_queryset(model_key, actor=actor)[1].values_list('pk', flat=True))


def test_a_customer_sees_their_own_orders_only(world):
    seen = _visible(world['me'], 'order')
    assert world['my_order'].pk in seen and world['their_order'].pk not in seen


def test_a_customer_sees_their_own_contact_and_customer_only(world):
    assert _visible(world['me'], 'contact') == {world['me_contact'].pk}
    assert _visible(world['me'], 'customer') == {world['mine'].pk}


@pytest.mark.parametrize('model_key', ['setting', 'project', 'purchase', 'ledger', 'gl_journal',
                                       'pending'])
def test_a_customer_sees_nothing_else(world, model_key):
    assert _visible(world['me'], model_key) == set()


@pytest.mark.parametrize('model_key', ['sync_bundle', 'project_association'])
def test_models_they_read_in_full_have_no_block_now(world, model_key):
    """Both had customer blocks with no scope, which read every row."""
    assert access.block_for(world['me'], model_key) is None


def test_a_new_order_is_stamped_with_their_customer(world):
    """Audit A3-M-6: without the stamp a portal `new` order was refused outside_scope."""
    result = save_record(world['me'], {'model_name': 'order'}, new=True)
    order = Order.objects.get(pk=result.obj_id)
    assert order.customer_id == world['mine'].pk
    assert order.contact_id == world['me_contact'].pk


def test_a_customer_cannot_order_for_another_customer(world):
    result = save_record(world['me'], {'model_name': 'order'}, new=True)
    save_record(world['me'], {'model_name': 'order', 'id': result.obj_id,
                              'customer_id': world['theirs'].pk})
    assert Order.objects.get(pk=result.obj_id).customer_id == world['mine'].pk


def test_a_customers_cash_is_a_card_payment_for_them(world):
    result = save_record(world['me'], {'model_name': 'cash'}, new=True)
    cash = Cash.objects.get(pk=result.obj_id)
    from apps.transactions.services.cash.cash_commands import PAYSERVICE
    assert cash.purpose == PAYSERVICE and cash.customer_id == world['mine'].pk
    with pytest.raises(Refused) as refused:
        save_record(world['me'], {'model_name': 'cash', 'id': cash.pk, 'purpose': 'deposit'})
    assert refused.value.code == 'portal_cash_is_payservice'


def test_a_customer_may_pay_but_not_refund(world):
    cash = Cash.objects.get(pk=save_record(world['me'], {'model_name': 'cash'}, new=True).obj_id)
    with pytest.raises(Refused) as refused:
        run_command(world['me'], 'refund', 'cash', cash.pk, {})
    assert refused.value.code == 'command_not_permitted'
    with pytest.raises(Refused) as refused:
        run_command(world['me'], 'pay', 'cash', cash.pk, {})
    assert refused.value.code != 'command_not_permitted'   # admitted; pay itself asks for a token


def test_support_requests_are_theirs_and_capped(world):
    for _ in range(access.PORTAL_OPEN_ACTIONS):
        result = save_record(world['me'], {'model_name': 'action'}, new=True)
        action = Action.objects.get(pk=result.obj_id)
        assert action.contact_id == world['me_contact'].pk
        assert action.refs['links']['customer'][0]['id'] == world['mine'].pk
    with pytest.raises(Refused) as refused:
        save_record(world['me'], {'model_name': 'action'}, new=True)
    assert refused.value.status == 409 and refused.value.code == 'too_many_open_requests'


def test_a_closed_request_frees_a_place(world):
    ids = [save_record(world['me'], {'model_name': 'action'}, new=True).obj_id
           for _ in range(access.PORTAL_OPEN_ACTIONS)]
    Action.objects.filter(pk=ids[0]).update(status='complete')
    save_record(world['me'], {'model_name': 'action'}, new=True)


def test_the_catalog_shows_images():
    call_command('narrow_portal_access', '--apply')
    block = access.portal_customer_block('item')
    assert {'metadata.images.tn', 'metadata.images.md', 'metadata.images.hr'} <= set(block['view'])


def test_a_customer_fills_their_new_order_and_the_server_prices_it(world):
    """The console's order flow: `new`, then the lines as the next save."""
    from apps.products.models import Item
    item = Item.objects.create(name='Widget', sku='W-1', security_level=1,
                               price={'base': 12.5, 'retail': 12.5})
    order_id = save_record(world['me'], {'model_name': 'order'}, new=True).obj_id
    order = Order.objects.get(pk=order_id)
    save_record(world['me'], {'model_name': 'order', 'id': order_id, 'version': order.version,
                              'lines': [{'item': {'item_id': item.pk},
                                         'quantity': {'active': 2}}]})
    line = Order.objects.get(pk=order_id).lines.get()
    assert (line.item or {}).get('item_id') == item.pk or line.item_fk_id == item.pk
    assert (line.quantity or {}).get('active') in (2, '2', 2.0)
    assert float(line.price['unit']) == 12.5, line.price


def test_a_customer_cannot_price_a_line_or_order_an_unpublished_item(world):
    from apps.products.models import Item
    hidden = Item.objects.create(name='Prototype', sku='P-0', price={'base': 1.0})   # level 0
    shown = Item.objects.create(name='Widget', sku='W-2', security_level=1, price={'base': 20.0})
    order_id = save_record(world['me'], {'model_name': 'order'}, new=True).obj_id
    with pytest.raises(Refused) as refused:
        save_record(world['me'], {'model_name': 'order', 'id': order_id,
                                  'lines': [{'item': {'item_id': hidden.pk}, 'quantity': {'active': 1}}]})
    assert refused.value.code == 'item_not_available'
    with pytest.raises(Refused):                  # a price they send is refused, not dropped
        save_record(world['me'], {'model_name': 'order', 'id': order_id,
                                  'lines': [{'item': {'item_id': shown.pk}, 'quantity': {'active': 1},
                                             'price': {'unit': 0.01}}]})
    save_record(world['me'], {'model_name': 'order', 'id': order_id,
                              'lines': [{'item': {'item_id': shown.pk}, 'quantity': {'active': 1}}]})
    assert float(Order.objects.get(pk=order_id).lines.get().price['unit']) == 20.0
