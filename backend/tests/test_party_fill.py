"""A document takes its party's values when its customer or vendor is set (readme 106 rule 3;
Bill, 2026-11-07: "On assigning a customer, the quote reloads with that customer's values").
The org's values replace the defaulted fields, not only blanks; a field the same payload
carries is the person's; where the org has none, the company default stays. On the server:
transactions/services/party_fill.py; the client-side applyCustomerDefaults is gone."""
import pytest

from apps.core.models import Setting
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
def company(model_defaults):
    """Each model's definition carries the shipped defaults (readme 106 A); N10 is a Term too."""
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N10', defaults={'name': 'N10', 'is_active': True})
    return Setting.objects.get(purpose='wc:company_profile')


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


def test_a_ship_via_from_the_org_lands_in_the_lists_own_spelling(admin, company):
    """Riverside Supplies' config said 'USPS'; the quote list says 'usps'. A spelling the list
    lacks is not written: code writing an unlisted value is refused, and the fill is code."""
    from apps.core.services import select_lists
    select_lists.replace_list('quote', 'ship_via', [{'value': 'usps'}, {'value': 'ups'}], actor=_as(admin))
    loud = Customer.objects.create(company='Loud Co', config={'defaults': {'fields': {'ship_via': 'USPS'}}})
    assert loud.config['defaults']['fields']['ship_via'] == 'usps', "the org's save stores the lists' spelling"
    q = _pick(admin, _quote(admin), 'quote', 'customer', loud)
    assert q.ship_via == 'usps'
    plain = Customer.objects.create(company='Plain Co')
    q = _pick(admin, q, 'quote', 'customer', plain)
    assert q.ship_via == 'usps', 'where the org has none the value stays (rule 3)'


def test_an_orgs_own_defaults_hold_only_what_it_has_no_column_for(admin, company):
    """The lead, readme 106: a column describes the org and party_fill copies it; config.defaults.fields
    is for the document fields the org has no column for. Never a value in both."""
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match='columns'):
        Customer.objects.create(company='Twice Co', config={'defaults': {'fields': {'terms': 'N10'}}})
    with pytest.raises(ValidationError, match='nothing else'):
        Customer.objects.create(company='Loose Co', config={'defaults': {'ship_via': 'ups'}})
    from importlib import import_module
    migrate_org_config = import_module('apps.orgs.migrations.0014_org_defaults_in_config').migrate_org_config
    assert migrate_org_config({'ship_via': 'USPS'}) == {'defaults': {'fields': {'ship_via': 'usps'}, 'formatting': {}}}
    assert migrate_org_config({'credit_limit': 5}) == {'credit_limit': 5}


def test_an_orgs_priority_and_days_reach_its_quote_over_the_models(admin, company):
    rush = Customer.objects.create(company='Rush Co', config={'defaults': {'fields': {'priority': 'urgent', 'dt_needed_days': 2}}})
    q = _quote(admin)
    born = q.dt_needed
    q = _pick(admin, q, 'quote', 'customer', rush)
    assert q.priority == 'urgent'
    assert q.dt_needed < born, 'two days out, not the model\'s fourteen'
    q = _pick(admin, q, 'quote', 'customer', rush, priority='low')
    assert q.priority == 'low', 'the payload wins'


def test_a_customers_source_name_reaches_the_quote(admin, company):
    """Readme 106 B: source_name on every org, copied to a document like terms."""
    from apps.core.services import select_lists
    select_lists.replace_list('quote', 'source_name', [{'value': 'referral'}, {'value': 'website'}], actor=_as(admin))
    fair = Customer.objects.create(company='Fair Co', source_name='Referral')
    q = _pick(admin, _quote(admin), 'quote', 'customer', fair)
    assert q.source_name == 'referral'
