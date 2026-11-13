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
                         'addresses': {'ship_to': {'contact_id': None, 'company': 'Home Co Dock', 'attention': 'Receiving',
                                                   'full_address': '3 Dock Rd, Tulsa, OK 74135', 'instructions': ''}},
                         'phones': {'ship_to': {'number': '918-555-0002'}}}
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


def test_a_new_purchase_ships_to_the_companys_ship_to(admin, company):
    po = _new(admin, 'purchase', Purchase)
    assert po.addresses['ship_to']['company'] == 'Home Co Dock'
    assert po.addresses['ship_to']['attention'] == 'Receiving'
    assert po.addresses['ship_to']['full_address'] == '3 Dock Rd, Tulsa, OK 74135'
    assert po.phones['ship_to']['number'] == '918-555-0002'
    assert po.emails['ship_to']['email'] == 'dock@home.test', "no ship-to email: the bill-to's"


def test_a_new_purchase_is_billed_to_the_company(admin, company):
    """No bill_to block in the profile: the company's name and main address."""
    po = _new(admin, 'purchase', Purchase)
    assert po.addresses['bill_to']['company'] == 'Home Co'
    assert po.addresses['bill_to']['full_address'] == '1 Office Way, Tulsa, OK 74135'
    assert po.phones['bill_to']['number'] == '918-555-0001'


def test_the_companys_own_bill_to_block_wins_and_a_blank_ship_to_is_the_bill_to(admin, company):
    from apps.core.services.cache import cache_service
    company.refresh_from_db()
    config = dict(company.config)
    config['company'] = {**config['company'], 'addresses': {'bill_to': {
        'contact_id': None, 'company': 'Home Co AP', 'attention': 'Payables',
        'full_address': 'PO Box 7, Tulsa, OK 74101', 'instructions': ''}}, 'phones': {}}
    Setting.objects.filter(pk=company.pk).update(config=config)
    cache_service.delete(cache_service.make_key(COMPANY_CACHE, 'company'))
    po = _new(admin, 'purchase', Purchase)
    assert po.addresses['bill_to']['company'] == 'Home Co AP'
    assert po.addresses['bill_to']['attention'] == 'Payables'
    assert po.addresses['ship_to']['full_address'] == 'PO Box 7, Tulsa, OK 74101'


def test_picking_the_vendor_fills_the_vendor_block_and_leaves_the_companys(admin, company):
    vendor = Vendor.objects.create(company='Parts Inc', addresses={'bill_to': {
        'contact_id': None, 'company': 'Parts Inc', 'attention': '', 'full_address': '9 Mill St, Denver, CO 80201',
        'instructions': ''}})
    po = _save(admin, _new(admin, 'purchase', Purchase), 'purchase', vendor_id=vendor.pk)
    assert po.addresses['vendor']['company'] == 'Parts Inc'
    assert po.addresses['vendor']['full_address'] == '9 Mill St, Denver, CO 80201'
    assert po.addresses['bill_to']['company'] == 'Home Co'
    assert po.addresses['ship_to']['full_address'] == '3 Dock Rd, Tulsa, OK 74135'


def test_the_migration_moves_the_vendor_out_of_bill_to(admin, company):
    """0054: an old purchase's bill_to held the vendor; the stored layout and the profile follow."""
    import importlib
    from types import SimpleNamespace
    m = importlib.import_module('apps.transactions.migrations.0054_purchase_vendor_block')
    old = SimpleNamespace(addresses={'bill_to': {'company': 'Parts Inc', 'full_address': '9 Mill St'}, 'ship_to': {}},
                          emails={'bill_to': {'email': 'ap@parts.test'}}, phones={})
    moved = m.vendor_block(old)
    assert moved['addresses'] == {'vendor': {'company': 'Parts Inc', 'full_address': '9 Mill St'}, 'ship_to': {}}
    assert moved['emails'] == {'vendor': {'email': 'ap@parts.test'}} and 'phones' not in moved
    assert m.vendor_block(SimpleNamespace(**moved, phones={})) == {}, 'done once'

    columns = [{'title': 'bill_to', 'title_ida': True, 'fields': [
        {'type': 'readonly', 'field': 'addresses.bill_to.company', 'label': 'company'}]}, {'title': 'ship_to', 'fields': []}]
    layout = m.vendor_layout({'form': {'default': {'sections': [{'type': 'header', 'columns': columns}]}}})
    out = layout['form']['default']['sections'][0]['columns']
    assert [c['title'] for c in out] == ['vendor', 'bill_to', 'ship_to']
    assert out[0]['fields'][0]['field'] == 'addresses.vendor.company' and out[0]['title_ida']
    assert out[1]['fields'][0] == {'field': 'addresses.bill_to.company', 'label': 'company'}
    assert m.vendor_layout(layout) == layout, 'done once'

    config = m.company_ship_to({'company': {'name': 'Home Co', 'address_receiving': '3 Dock Rd'}})
    assert 'address_receiving' not in config['company']
    assert config['company']['addresses']['ship_to']['full_address'] == '3 Dock Rd'
    assert config['company']['addresses']['ship_to']['company'] == 'Home Co'


def test_the_shipped_purchase_layout_names_the_vendor(db):
    import json, pathlib
    from django.conf import settings
    layouts = json.loads((pathlib.Path(settings.BASE_DIR) / 'apps/core/layouts/layouts.json').read_text())
    columns = layouts['purchase']['form']['default']['sections'][0]['columns']
    assert [c['title'] for c in columns][:2] == ['vendor', 'ship_to']     # bill_to column removed 2026-11-12
    assert columns[0]['fields'][0]['field'] == 'addresses.vendor.company'


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


def test_the_form_can_read_the_vendor_block(admin, company):
    """The wire, not the row: the door projects out any leaf the definition's access set does
    not name, and the form then draws the block's title over blanks (found 2026-11-12, after
    0054 went out with the rows right and the screen empty)."""
    from rest_framework.test import APIClient
    vendor = Vendor.objects.create(company='Parts Inc', addresses={'bill_to': {
        'contact_id': None, 'company': 'Parts Inc', 'attention': 'Sal', 'full_address': '9 Mill St, Denver, CO 80201',
        'instructions': ''}}, phones={'bill_to': {'number': '303-555-0100'}})
    po = _save(admin, _new(admin, 'purchase', Purchase), 'purchase', vendor_id=vendor.pk)
    client = APIClient()
    client.force_authenticate(admin)
    body = client.get(f'/wcapi/purchase/{po.pk}/', HTTP_HOST='localhost').json()
    record = body.get('data', body)
    record = record.get('record', record)
    for role, company_name in (('vendor', 'Parts Inc'), ('bill_to', 'Home Co'), ('ship_to', 'Home Co Dock')):
        assert record['addresses'][role]['company'] == company_name, role
    assert record['addresses']['vendor']['full_address'] == '9 Mill St, Denver, CO 80201'
    assert record['phones']['vendor']['number'] == '303-555-0100'
