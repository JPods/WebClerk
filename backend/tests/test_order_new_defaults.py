"""A new order is born with the company's defaults and takes its customer's (Bill, 2026-11-05):
price_level retail when no one says, terms from the customer or the company's defaults.terms,
dt_needed = born + defaults.order_new.days, priority = defaults.order_new.priority. The server
computes them in the save door's hook; the form shows what the save returns."""
import time

import pytest

from apps.core.models import Setting
from apps.core.services.cache import cache_service
from apps.core.services.door import Actor, Refused
from apps.core.services.new import new_record
from apps.core.services.save import save_record
from apps.orgs.models import Customer
from apps.transactions.models import Order

pytestmark = pytest.mark.django_db

DAY_MS = 86_400_000


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='orders@example.com', password=None, name_first='Or', name_last='Der', username='')


@pytest.fixture
def company(chart_of_accounts):
    """The company profile with Bill's default section; N30 and N10 are Term records."""
    from apps.accounts.models import Term
    for ida in ('N30', 'N10'):
        Term.objects.get_or_create(ida=ida, defaults={'name': ida, 'is_active': True})
    setting = Setting.objects.get(purpose='wc:company_profile')
    setting.config = {**(setting.config or {}),
                      'defaults': {'terms': 'N30', 'order_new': {'days': 14, 'priority': 'medium'}}}
    setting.save()
    cache_service.invalidate_namespace('company_profile')
    return setting


def _as(user):
    return Actor(user=user, kind='user', source='wcapi')


def _born(admin, **payload):
    return Order.objects.get(pk=new_record(_as(admin), 'order', dict(payload)).obj_id)


def test_an_order_is_born_with_the_company_defaults(admin, company):
    before = int(time.time() * 1000)
    order = _born(admin)
    assert order.priority == 'medium'
    assert order.price_level == 'retail'
    assert before + 14 * DAY_MS <= order.dt_needed <= before + 14 * DAY_MS + 60_000
    assert order.terms in (None, '')   # no customer yet: the customer decides the terms


def test_a_customer_with_terms_and_a_level_gives_them_to_the_order(admin, company):
    buyer = Customer.objects.create(company='Terms Buyer', terms='N10', price_level='wholesale')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.price_level) == ('N10', 'wholesale')


def test_a_customer_without_them_leaves_the_company_terms_and_retail(admin, company):
    buyer = Customer.objects.create(company='Plain Buyer')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.price_level) == ('N30', 'retail')


def test_what_the_person_types_in_the_same_save_is_theirs(admin, company):
    buyer = Customer.objects.create(company='Terms Buyer', terms='N10', price_level='wholesale')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk,
                             'terms': 'N30', 'price_level': 'retail', 'priority': 'high'}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.price_level, order.priority) == ('N30', 'retail', 'high')


def test_a_later_save_does_not_rewrite_the_defaults(admin, company):
    buyer = Customer.objects.create(company='Terms Buyer', terms='N10')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    order.refresh_from_db()
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'terms': 'N30', 'priority': 'low'}, model_key='order')
    order.refresh_from_db()
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'comments': {'public': 'unrelated'}}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.priority) == ('N30', 'low')


def test_a_company_default_terms_that_is_no_term_is_refused_where_it_bites(admin, company):
    company.config['defaults']['terms'] = 'net45'
    company.save()
    cache_service.invalidate_namespace('company_profile')
    buyer = Customer.objects.create(company='Plain Buyer')
    order = _born(admin)
    with pytest.raises(Refused) as refused:
        save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    assert refused.value.code == 'invalid_terms' and 'defaults.terms' in refused.value.message
