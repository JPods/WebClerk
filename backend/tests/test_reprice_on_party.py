"""Assigning a customer reprices the lines (readme 106 rule 5; Bill, 2026-11-07: "if there are
lines already built into a quote at retail pricing, assigning a customer that is wholesale
price_level would update the quote to that customer settings and be returned from the
backend"). transactions/services/reprice.py in the document's after_save."""
import pytest

from apps.core.models import Setting
from apps.core.services.door import Actor, Refused
from apps.core.services.new import new_record
from apps.core.services.save import save_record
from apps.orgs.models import Customer
from apps.transactions.models import Order, Quote
from apps.transactions.services.line_manage import add_item_to_transaction

pytestmark = pytest.mark.django_db

PRICES = {'base': 100, 'retail': 100, 'wholesale': 75, 'distributor': 60, 'sample': 50}


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='reprice@example.com', password=None, name_first='Re', name_last='Price', username='')


@pytest.fixture
def company(model_defaults):
    """Each model's definition carries the shipped defaults (readme 106 A); N10 is a Term too."""
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N10', defaults={'name': 'N10', 'is_active': True})
    return Setting.objects.get(purpose='wc:company_profile')


@pytest.fixture
def item():
    from tests.conftest import ItemFactory
    it = ItemFactory()
    it.price = dict(PRICES)
    it.cost = {'standard': 40, 'last': 45}
    it.save()
    return it


def _as(user):
    return Actor(user=user, kind='user', source='wcapi')


def _customer(level):
    return Customer.objects.create(company=f'{level.title()} Buyer', price_level=level)


def _quote(admin):
    return Quote.objects.get(pk=new_record(_as(admin), 'quote', {}).obj_id)


def _save(admin, doc, model_key, **fields):
    result = save_record(_as(admin), {'id': doc.pk, 'version': doc.version, **fields}, model_key=model_key)
    doc.refresh_from_db()
    return result


def _detail(result):
    return next((m for m in result.messages if isinstance(m, dict) and 'repriced' in m), None)


def test_a_wholesale_customer_reprices_retail_lines_and_the_save_says_so(admin, company, item):
    q = _quote(admin)
    line = add_item_to_transaction(q, item.pk, quantity=2)
    assert (q.price_level, line.price['unit']) == ('retail', 100.0)
    before = (line.version, line.dt_modified)
    result = _save(admin, q, 'quote', customer_id=_customer('wholesale').pk)
    line.refresh_from_db()
    assert (q.price_level, line.price['unit'], line.price_level) == ('wholesale', 75.0, 'wholesale')
    assert line.version > before[0] and line.dt_modified >= before[1], 'a stale open form meets the version check, never overwrites'
    assert float(q.totals['amount']) == 150.0, 'the totals follow the repriced lines in the same save'
    detail = _detail(result)
    assert detail['price_level'] == 'wholesale' and detail['kept'] == []
    assert [(r['line'], r['old'], r['new'], r['resolved_by']) for r in detail['repriced']] == [(line.pk, 100.0, 75.0, 'price_level')]


def test_a_hand_fixed_line_keeps_its_price(admin, company, item):
    q = _quote(admin)
    fixed = add_item_to_transaction(q, item.pk, quantity=1)
    fixed.price = {**fixed.price, 'unit': 90.0, 'is_fixed': True}
    fixed.save()
    free = add_item_to_transaction(q, item.pk, quantity=1)
    result = _save(admin, q, 'quote', customer_id=_customer('wholesale').pk)
    fixed.refresh_from_db(); free.refresh_from_db()
    assert (fixed.price['unit'], free.price['unit']) == (90.0, 75.0)
    detail = _detail(result)
    assert [k['line'] for k in detail['kept']] == [fixed.pk] and detail['kept'][0]['why'] == 'fixed'


def test_a_line_a_child_document_already_took_keeps_its_price(admin, company, item):
    q = _quote(admin)
    taken = add_item_to_transaction(q, item.pk, quantity=4)
    type(taken).objects.filter(pk=taken.pk).update(quantity={**taken.quantity, 'remaining': 1.0})   # 3 went to an order
    result = _save(admin, q, 'quote', customer_id=_customer('wholesale').pk)
    taken.refresh_from_db()
    assert taken.price['unit'] == 100.0
    assert _detail(result)['kept'] == [{'line': taken.pk, 'line_number': taken.line_number, 'why': 'consumed'}]


def test_changing_the_price_level_by_hand_reprices_too(admin, company, item):
    q = _quote(admin)
    line = add_item_to_transaction(q, item.pk, quantity=1)
    _save(admin, q, 'quote', price_level='distributor')
    line.refresh_from_db()
    assert line.price['unit'] == 60.0


def test_a_save_that_changes_neither_leaves_the_prices_alone(admin, company, item):
    q = _quote(admin)
    line = add_item_to_transaction(q, item.pk, quantity=1)
    result = _save(admin, q, 'quote', comments={'public': 'unrelated'})
    line.refresh_from_db()
    assert line.price['unit'] == 100.0 and _detail(result) is None


def test_a_conversions_birth_keeps_the_prices_its_source_gave(admin, company, item):
    """The order is born with its customer and its parent in one payload (convert_command):
    its lines come priced from the quote, and are not priced again."""
    buyer = _customer('wholesale')
    q = _quote(admin)
    add_item_to_transaction(q, item.pk, quantity=1)
    result = save_record(_as(admin), {
        'model_name': 'order', 'customer_id': buyer.pk, 'parent_id': q.pk, 'parent_model': 'quote',
        'lines': [{'_dirty': True, 'item': {'item_id': item.pk}, 'quantity': {'active': 1}, 'price': {'unit': 100.0}}],
    }, model_key='order')
    order = Order.objects.get(pk=result.obj_id)
    assert [l.price['unit'] for l in order.lines.all()] == [100.0]
    assert _detail(result) is None


def test_a_locked_quote_refuses_the_customer_change(admin, company, item):
    q = _quote(admin)
    add_item_to_transaction(q, item.pk, quantity=1)
    Quote.objects.filter(pk=q.pk).update(metadata={**(q.metadata or {}), 'health': {'lock': {'by': {'id': 1, 'name': 'Someone'}, 'at': 1, 'reason': 'audit'}}})
    q.refresh_from_db()
    with pytest.raises(Refused) as refused:
        _save(admin, q, 'quote', customer_id=_customer('wholesale').pk)
    assert refused.value.status == 409 and 'locked' in refused.value.message
