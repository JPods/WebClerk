"""A document's ship-to (Bill, 2026-11-11): a purchase with none takes the company's receiving
address; the form's ship-to search sets it from any contact or customer through the signal
``_ship_to_from`` — a drop shipment. transactions/services/party_fill.py."""
import pytest

from apps.communications.models import Address
from apps.core.models import Contact, Setting
from apps.core.services.company_profile import COMPANY_CACHE
from apps.core.services.door import Actor, Refused
from apps.core.services.new import new_record
from apps.core.services.save import save_record
from apps.orgs.models import Customer, Vendor
from apps.transactions.models import Purchase, Quote

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='shipto@example.com', password=None, name_first='Shi', name_last='Pto', username='')


@pytest.fixture
def company(model_defaults):
    from apps.core.services.cache import cache_service
    profile = Setting.objects.get(purpose='wc:company_profile')
    config = dict(profile.config or {})
    config['company'] = {**(config.get('company') or {}), 'name': 'Home Co', 'phone': '918-555-0001',
                         'email': 'dock@home.test', 'address_full': '1 Office Way, Tulsa, OK 74135',
                         'address_receiving': '3 Dock Rd, Tulsa, OK 74135'}
    Setting.objects.filter(pk=profile.pk).update(config=config)
    cache_service.delete(cache_service.make_key(COMPANY_CACHE, 'company'))
    yield profile
    cache_service.delete(cache_service.make_key(COMPANY_CACHE, 'company'))


def _as(user):
    return Actor(user=user, kind='user', source='wcapi')


def _new(admin, model_key, cls):
    return cls.objects.get(pk=new_record(_as(admin), model_key, {}).obj_id)


def _save(admin, doc, model_key, **fields):
    save_record(_as(admin), {'id': doc.pk, 'version': doc.version, **fields}, model_key=model_key)
    doc.refresh_from_db()
    return doc


def test_a_new_purchase_ships_to_the_companys_receiving_address(admin, company):
    po = _new(admin, 'purchase', Purchase)
    assert po.addresses['ship_to']['company'] == 'Home Co'
    assert po.addresses['ship_to']['full_address'] == '3 Dock Rd, Tulsa, OK 74135'
    assert po.phones['ship_to']['number'] == '918-555-0001'
    assert po.emails['ship_to']['email'] == 'dock@home.test'


def test_picking_the_vendor_leaves_the_companys_ship_to(admin, company):
    vendor = Vendor.objects.create(company='Parts Inc', addresses={'bill_to': {
        'contact_id': None, 'company': 'Parts Inc', 'attention': '', 'full_address': '9 Mill St, Denver, CO 80201',
        'instructions': ''}})
    po = _save(admin, _new(admin, 'purchase', Purchase), 'purchase', vendor_id=vendor.pk)
    assert po.addresses['bill_to']['company'] == 'Parts Inc'
    assert po.addresses['ship_to']['full_address'] == '3 Dock Rd, Tulsa, OK 74135'


def test_a_ship_to_someone_typed_is_kept(admin, company):
    po = _new(admin, 'purchase', Purchase)
    typed = {**po.addresses, 'ship_to': {**po.addresses['ship_to'], 'company': 'Job Site', 'full_address': '5 Site Ln'}}
    po = _save(admin, po, 'purchase', addresses=typed)
    po = _save(admin, po, 'purchase', attention='again')
    assert po.addresses['ship_to']['company'] == 'Job Site'
    assert po.addresses['ship_to']['full_address'] == '5 Site Ln'


def test_a_sale_does_not_take_the_companys_ship_to(admin, company):
    q = _new(admin, 'quote', Quote)
    assert not ((q.addresses or {}).get('ship_to') or {}).get('full_address')


def test_the_search_ships_a_purchase_to_a_customer(admin, company):
    acme = Customer.objects.create(company='Acme Corp', addresses={'ship_to': {
        'contact_id': None, 'company': 'Acme Corp', 'attention': 'Ann Acme',
        'full_address': '1 Main St, Tulsa, OK 74103', 'instructions': 'dock 3'}},
        phones={'ship_to': {'number': '918-555-0100'}})
    po = _save(admin, _new(admin, 'purchase', Purchase), 'purchase',
               _ship_to_from={'model': 'customer', 'id': acme.pk})
    assert po.addresses['ship_to']['company'] == 'Acme Corp'
    assert po.addresses['ship_to']['full_address'] == '1 Main St, Tulsa, OK 74103'
    assert po.addresses['ship_to']['instructions'] == 'dock 3'
    assert po.phones['ship_to']['number'] == '918-555-0100'


def test_the_search_ships_a_quote_to_a_contact(admin, company):
    pat = Contact.objects.create(name_first='Pat', name_last='Lee', email='pat@lee.test', company='Lee Farms')
    address = Address.objects.create(contact=pat, address1='7 Elm St', full='7 Elm St, Austin, TX 78701')
    Contact.objects.filter(pk=pat.pk).update(address_id=address.pk)
    q = _save(admin, _new(admin, 'quote', Quote), 'quote', _ship_to_from={'model': 'contact', 'id': pat.pk})
    ship = q.addresses['ship_to']
    assert (ship['company'], ship['attention'], ship['contact_id']) == ('Lee Farms', 'Pat Lee', pat.pk)
    assert ship['full_address'] == Address.objects.get(pk=address.pk).full and '7 Elm St' in ship['full_address']
    assert q.emails['ship_to']['email'] == 'pat@lee.test'


@pytest.mark.parametrize('signal', [{'model': 'vendor', 'id': 1}, {'model': 'customer'}, {'model': 'customer', 'id': 'x'}])
def test_a_wrong_signal_is_refused_not_dropped(admin, company, signal):
    po = _new(admin, 'purchase', Purchase)
    with pytest.raises(Refused) as e:
        save_record(_as(admin), {'id': po.pk, 'version': po.version, '_ship_to_from': signal}, model_key='purchase')
    assert e.value.status == 400


def test_a_record_that_is_not_there_is_refused(admin, company):
    po = _new(admin, 'purchase', Purchase)
    with pytest.raises(Refused) as e:
        save_record(_as(admin), {'id': po.pk, 'version': po.version,
                                 '_ship_to_from': {'model': 'customer', 'id': 987654}}, model_key='purchase')
    assert e.value.status == 404
