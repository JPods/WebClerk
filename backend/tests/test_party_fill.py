"""A document takes its party's values when its customer or vendor is set (readme 106 rule 3;
Bill, 2026-11-07: "On assigning a customer, the quote reloads with that customer's values").
The org's values replace the defaulted fields, not only blanks; a field the same payload
carries is the person's; where the org has none, the company default stays. On the server:
transactions/services/party_fill.py; the client-side applyCustomerDefaults is gone."""
import pytest

from apps.core.models import Setting
from apps.core.services.cache import cache_service
from apps.core.services.door import Actor
from apps.core.services.new import new_record
from apps.core.services.save import save_record
from apps.orgs.models import Customer, Vendor
from apps.transactions.models import Purchase, Quote

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='party@example.com', password=None, name_first='Par', name_last='Ty', username='')


@pytest.fixture
def company(chart_of_accounts):
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


def _quote(admin):
    return Quote.objects.get(pk=new_record(_as(admin), 'quote', {}).obj_id)


def _pick(admin, doc, model_key, party, org, **more):
    save_record(_as(admin), {'id': doc.pk, 'version': doc.version, f'{party}_id': org.pk, **more}, model_key=model_key)
    doc.refresh_from_db()
    return doc


BILL = {'contact_id': None, 'company': 'Acme Corp', 'attention': 'Ann Acme',
        'full_address': '1 Main St, Tulsa, OK 74103', 'instructions': 'dock 3'}


def test_a_customer_gives_the_quote_its_blocks_terms_and_level(admin, company):
    acme = Customer.objects.create(company='Acme Corp', terms='N10', price_level='wholesale',
                                   addresses={'bill_to': BILL},
                                   emails={'bill_to': {'email': 'ap@acme.test'}},
                                   phones={'bill_to': {'number': '918-555-0100'}})
    q = _pick(admin, _quote(admin), 'quote', 'customer', acme)
    assert (q.terms, q.price_level, q.attention) == ('N10', 'wholesale', 'Ann Acme')
    assert q.addresses['bill_to'] == BILL
    assert q.addresses['ship_to'] == BILL, 'a ship-to is the bill-to until split'
    assert q.emails == {'bill_to': {'email': 'ap@acme.test'}, 'ship_to': {'email': 'ap@acme.test'}}
    assert q.phones['ship_to']['number'] == '918-555-0100'


def test_an_org_with_empty_blocks_gives_its_own_name_and_attention(admin, company):
    """Rubble Manufacturing on 2026-11-06: its bill_to block was empty, the card showed its
    company and attention — the fallback the client fill had, now the server's."""
    rubble = Customer.objects.create(company='Rubble Manufacturing', attention='Barney Rubble')
    q = _pick(admin, _quote(admin), 'quote', 'customer', rubble)
    assert q.addresses['bill_to']['company'] == 'Rubble Manufacturing'
    assert q.addresses['bill_to']['attention'] == 'Barney Rubble'
    assert (q.terms, q.price_level) == ('N30', 'retail'), "the company's where the org has none"


def test_the_next_customer_replaces_the_last_ones_values_not_only_blanks(admin, company):
    acme = Customer.objects.create(company='Acme Corp', terms='N10', price_level='wholesale', addresses={'bill_to': BILL})
    plain = Customer.objects.create(company='Plain Co')
    q = _pick(admin, _quote(admin), 'quote', 'customer', acme)
    q = _pick(admin, q, 'quote', 'customer', plain)
    assert (q.terms, q.price_level) == ('N30', 'retail')
    assert q.addresses['bill_to']['company'] == 'Plain Co'
    assert q.addresses['ship_to']['company'] == 'Plain Co'


def test_what_the_same_payload_carries_is_the_persons(admin, company):
    acme = Customer.objects.create(company='Acme Corp', terms='N10', price_level='wholesale', addresses={'bill_to': BILL})
    mine = {'bill_to': {**BILL, 'attention': 'My Contact'}}
    q = _pick(admin, _quote(admin), 'quote', 'customer', acme, terms='N30', addresses=mine)
    assert q.terms == 'N30' and q.price_level == 'wholesale'
    assert q.addresses['bill_to']['attention'] == 'My Contact'
    assert 'ship_to' not in q.addresses or not q.addresses['ship_to'].get('company')


def test_a_vendor_gives_a_purchase_its_terms_and_bill_to_only(admin, company):
    seller = Vendor.objects.create(company='Parts Inc', terms='N10', addresses={'bill_to': {**BILL, 'company': 'Parts Inc'}})
    po = Purchase.objects.get(pk=new_record(_as(admin), 'purchase', {}).obj_id)
    po = _pick(admin, po, 'purchase', 'vendor', seller)
    assert po.terms == 'N10'
    assert po.addresses['bill_to']['company'] == 'Parts Inc'
    assert not (po.addresses.get('ship_to') or {}).get('company'), "the ship-to stays the company's own"


def test_an_exempt_customer_carries_no_sales_tax(admin, company):
    church = Customer.objects.create(company='First Church', tax_exempt_code='501c3')
    q = _pick(admin, _quote(admin), 'quote', 'customer', church)
    assert q.finance['sales_tax_rate'] == 0 and q.finance['sales_tax_name'] == 'Exempt'


def test_a_later_save_without_the_party_takes_nothing(admin, company):
    acme = Customer.objects.create(company='Acme Corp', terms='N10', addresses={'bill_to': BILL})
    q = _pick(admin, _quote(admin), 'quote', 'customer', acme)
    acme.terms = 'N30'; acme.save()
    save_record(_as(admin), {'id': q.pk, 'version': q.version, 'comments': {'public': 'later'}}, model_key='quote')
    q.refresh_from_db()
    assert q.terms == 'N10', 'the party fires on the pick, not on every save'
