"""An org takes a contact's values from its contact card (Bill, 2026-11-05): as its default
bill-to or ship-to, and to fill what it lacks. The values come from the contact's own
records; the server computes them, the card only asks."""
import pytest

from apps.communications.models import Address, Phone
from apps.core.models import Contact
from apps.core.services.door import Actor, Refused
from apps.core.services.verbs import run_command
from apps.orgs.models import Customer

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='party@example.com', password=None, name_first='Par', name_last='Ty', username='')


def _customer_with_contact():
    org = Customer.objects.create(company='Evergreen Works')
    contact = Contact.objects.create(email='sarah@evergreen.fake', name_first='Sarah', name_last='Chen',
                                     company='Evergreen Works', customer_id=org.pk)
    address = Address.objects.create(address1='654 Maple Ct', city='Raleigh', state='NC', zip='27601', contact=contact)
    phone = Phone.objects.create(number='(555) 824-7515', contact=contact)
    Contact.objects.filter(pk=contact.pk).update(address_id=address.pk, phone_id=phone.pk)
    contact.refresh_from_db()
    return org, contact, address, phone


def test_the_contact_becomes_the_default_bill_to_and_ship_to(admin):
    org, contact, address, phone = _customer_with_contact()
    out = run_command(Actor(user=admin, kind='user'), 'from_contact', 'customer', org.pk,
                      {'contact_id': contact.pk, 'bill_to': True, 'ship_to': True})
    org.refresh_from_db()
    assert out['set'] == ['bill_to', 'ship_to'] and out['filled'] == []
    for role in ('bill_to', 'ship_to'):
        assert org.addresses[role] == {'contact_id': contact.pk, 'company': 'Evergreen Works', 'attention': 'Sarah Chen',
                                       'full_address': address.full, 'instructions': ''}
        assert org.emails[role] == {'email_id': contact.email_id, 'email': 'sarah@evergreen.fake'}
        assert org.phones[role] == {'phone_id': phone.pk, 'number': '(555) 824-7515'}
    assert address.full  # the address record's own full text, not a copy made here


def test_fill_takes_only_what_the_org_lacks(admin):
    org, contact, address, phone = _customer_with_contact()
    Customer.objects.filter(pk=org.pk).update(attention='Kept Name', email='')
    out = run_command(Actor(user=admin, kind='user'), 'from_contact', 'customer', org.pk,
                      {'contact_id': contact.pk, 'fill': True})
    org.refresh_from_db()
    assert org.attention == 'Kept Name'                       # had one: kept
    assert org.email == 'sarah@evergreen.fake'                # lacked one: taken
    assert (org.address_id, org.phone_id) == (address.pk, phone.pk)
    assert 'attention' not in out['filled'] and 'email' in out['filled']
    assert org.addresses.get('bill_to', {}).get('full_address', '') == ''   # fill does not set a party


def test_a_contact_of_another_org_is_refused(admin):
    org, _contact, _a, _p = _customer_with_contact()
    stranger = Contact.objects.create(email='other@elsewhere.fake', name_first='O', name_last='Ther')
    with pytest.raises(Refused) as refused:
        run_command(Actor(user=admin, kind='user'), 'from_contact', 'customer', org.pk,
                    {'contact_id': stranger.pk, 'bill_to': True})
    assert refused.value.code == 'not_this_orgs_contact'
