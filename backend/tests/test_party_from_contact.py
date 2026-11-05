"""An org takes a contact's values from its contact card (Bill, 2026-11-05): as its default
bill-to or ship-to, and to fill what it lacks. The values come from the contact's own
records; the server computes them, the card only asks. The write goes through the save door,
so a save's gates hold: edit rights, the edit hold, the version, the role's edit enumeration."""
import pytest
from django.utils.crypto import get_random_string

from apps.communications.models import Address, Phone
from apps.core.models import Contact, Setting
from apps.core.services import access
from apps.core.services.door import Actor, Refused
from apps.core.services.edit_hold import take as take_hold
from apps.core.services.verbs import run_command
from apps.orgs.models import Customer
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='party@example.com', password=None, name_first='Par', name_last='Ty', username='')


def _person(django_user_model, role, **flags):
    return django_user_model.objects.create_user(
        email=f'{get_random_string(8).lower()}@example.com', password=get_random_string(20),
        name_first=role.title(), name_last='Person', role=role, **flags)


def _customer_with_contact(primary=False):
    org = Customer.objects.create(company='Evergreen Works')
    contact = Contact.objects.create(email='sarah@evergreen.fake', name_first='Sarah', name_last='Chen',
                                     company='Evergreen Works', customer_id=org.pk)
    address = Address.objects.create(address1='654 Maple Ct', city='Raleigh', state='NC', zip='27601', contact=contact)
    phone = Phone.objects.create(number='(555) 824-7515', contact=contact)
    Contact.objects.filter(pk=contact.pk).update(address_id=address.pk, phone_id=phone.pk)
    contact.refresh_from_db()
    if primary:
        Customer.objects.filter(pk=org.pk).update(contact_id=contact.pk)
        org.refresh_from_db()
    return org, contact, address, phone


def _customer_access(roles: dict):
    """The customer definition's access block for this test: {role: {view, edit, ...}}."""
    Setting.objects.filter(purpose='wc:model', parent_model='customer').delete()
    make_setting(purpose='wc:model', parent_model='customer', name='customer', config={
        'access': {'sets': access.default_access('customer')['sets'], 'roles': roles}})
    access.clear_cache()


def _as(user):
    return Actor(user=user, kind='user', source='wcapi')


@pytest.fixture(autouse=True)
def _access_cache_per_test():
    """A test's access block must not be the next test's (the definition cache is in-process)."""
    access.clear_cache()
    yield
    access.clear_cache()


def _visible_to_staff(org):
    """A record made outside the door starts at level 0, which only a superuser sees."""
    Customer.objects.filter(pk=org.pk).update(security_level=1)


def test_the_contact_becomes_the_default_bill_to_and_ship_to(admin):
    org, contact, address, phone = _customer_with_contact()
    out = run_command(_as(admin), 'from_contact', 'customer', org.pk,
                      {'contact_id': contact.pk, 'version': org.version, 'bill_to': True, 'ship_to': True})
    org.refresh_from_db()
    assert out['set'] == ['bill_to', 'ship_to'] and out['filled'] == [] and out['version'] == org.version
    for role in ('bill_to', 'ship_to'):
        assert org.addresses[role] == {'contact_id': contact.pk, 'company': 'Evergreen Works', 'attention': 'Sarah Chen',
                                       'full_address': address.full, 'instructions': ''}
        assert org.emails[role] == {'email_id': contact.email_id, 'email': 'sarah@evergreen.fake'}
        assert org.phones[role] == {'phone_id': phone.pk, 'number': '(555) 824-7515'}
    assert address.full  # the address record's own full text, not a copy made here


def test_fill_makes_the_contact_primary_when_the_org_has_none(admin):
    org, contact, address, phone = _customer_with_contact()
    out = run_command(_as(admin), 'from_contact', 'customer', org.pk,
                      {'contact_id': contact.pk, 'version': org.version, 'fill': True})
    org.refresh_from_db()
    assert org.contact_id == contact.pk
    assert (org.attention, org.email) == ('Sarah Chen', 'sarah@evergreen.fake')   # the primary's, by the hook
    assert (org.address_id, org.phone_id) == (address.pk, phone.pk)
    assert 'contact_id' in out['filled']
    assert org.addresses.get('bill_to', {}).get('full_address', '') == ''   # fill sets no party


def test_fill_takes_only_the_pointers_the_org_lacks_when_it_has_a_primary(admin):
    org, primary, _a, _p = _customer_with_contact(primary=True)
    # The primary's own pointers, as the hook would have copied them — all but the address it lacks.
    Customer.objects.filter(pk=org.pk).update(address_id=None, attention='Kept Name', email_id=primary.email_id,
                                              phone_id=primary.phone_id, domain_id=primary.domain_id)
    other = Contact.objects.create(email='pat@evergreen.fake', name_first='Pat', name_last='Abbott', customer_id=org.pk)
    other_address = Address.objects.create(address1='1 Elm', city='Boise', state='ID', zip='83701', contact=other)
    Contact.objects.filter(pk=other.pk).update(address_id=other_address.pk)
    org.refresh_from_db()
    out = run_command(_as(admin), 'from_contact', 'customer', org.pk,
                      {'contact_id': other.pk, 'version': org.version, 'fill': True})
    org.refresh_from_db()
    assert org.contact_id == primary.pk and org.attention == 'Kept Name'   # the primary stays
    assert org.address_id == other_address.pk and out['filled'] == ['address_id']


def test_a_contact_of_another_org_is_refused(admin):
    org, _contact, _a, _p = _customer_with_contact()
    stranger = Contact.objects.create(email='other@elsewhere.fake', name_first='O', name_last='Ther')
    with pytest.raises(Refused) as refused:
        run_command(_as(admin), 'from_contact', 'customer', org.pk, {'contact_id': stranger.pk, 'bill_to': True})
    assert refused.value.code == 'not_this_orgs_contact'


# ── the door's gates ──

def test_a_role_that_may_not_edit_the_customer_is_refused(django_user_model):
    org, contact, _a, _p = _customer_with_contact()
    _customer_access({'employee': {'view': ['@all'], 'edit': [], 'scope': {}, 'create': False, 'delete': False}})
    _visible_to_staff(org)
    viewer = _person(django_user_model, 'employee')
    with pytest.raises(Refused) as refused:
        run_command(_as(viewer), 'from_contact', 'customer', org.pk, {'contact_id': contact.pk, 'bill_to': True})
    assert refused.value.code == 'edit_not_permitted'


def test_someone_elses_edit_hold_refuses_the_command(admin, django_user_model):
    org, contact, _a, _p = _customer_with_contact()
    other = _person(django_user_model, 'admin', is_staff=True)
    take_hold(_as(other), 'customer', org.pk)
    with pytest.raises(Refused) as refused:
        run_command(_as(admin), 'from_contact', 'customer', org.pk,
                    {'contact_id': contact.pk, 'version': org.version, 'bill_to': True})
    assert refused.value.status == 423 and refused.value.code == 'held'
    org.refresh_from_db()
    assert not org.addresses.get('bill_to', {}).get('contact_id')


def test_a_stale_version_is_refused(admin):
    org, contact, _a, _p = _customer_with_contact()
    with pytest.raises(Refused) as refused:
        run_command(_as(admin), 'from_contact', 'customer', org.pk,
                    {'contact_id': contact.pk, 'version': org.version - 1, 'bill_to': True})
    assert refused.value.status == 412 and refused.value.code == 'version_conflict'


def test_a_role_whose_edit_enumeration_lacks_the_parties_is_refused_not_ignored(django_user_model):
    org, contact, _a, _p = _customer_with_contact()
    _customer_access({'employee': {'view': ['@all'], 'edit': ['company', 'attention'], 'scope': {},
                                   'create': False, 'delete': False}})
    _visible_to_staff(org)
    clerk = _person(django_user_model, 'employee')
    with pytest.raises(Refused) as refused:
        run_command(_as(clerk), 'from_contact', 'customer', org.pk,
                    {'contact_id': contact.pk, 'version': org.version, 'bill_to': True})
    assert refused.value.code == 'field_not_permitted'
    assert refused.value.details['fields'] == ['addresses', 'emails', 'phones']
    org.refresh_from_db()
    assert not org.addresses.get('bill_to', {}).get('contact_id')
