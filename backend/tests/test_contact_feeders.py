"""Feeders on the contact form (Bill, 2026-11-03, flight-simulator walk).

phone, address_full and domain are computed from the contact's communication records
(PJPV). Typed on the contact form, each makes that record and points the contact at it;
attention fills from the names. Before this, the save was refused: "domain: not a field
of contact".
"""
import pytest
from django.contrib.auth import get_user_model

from apps.communications.models import Address, Domain, Phone
from apps.core.models import Contact
from apps.core.services.door import Actor
from apps.core.services.save import save_record

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def actor():
    user = User.objects.create_superuser(email='feeders@example.com', password=None,
                                         name_first='Feed', name_last='Er', username='')
    return Actor(user=user)


def test_typed_phone_address_and_domain_become_records_and_the_primary(actor):
    c = Contact.objects.create(email='sally@test.com', name_first='Sally', name_last='Smith')
    save_record(actor, {'phone': '(918) 414-4211',
                        'address_full': '123 Maple Street, River City, OK 74111',
                        'domain': 'www.sallytest.com', 'version': c.version},
                model_key='contact', record_id=c.id)
    c = Contact.objects.get(pk=c.pk)
    assert Phone.objects.get(contact=c).number == '(918) 414-4211'
    assert c.phone == '(918) 414-4211' and c.phone_id == Phone.objects.get(contact=c).id
    addr = Address.objects.get(contact=c)
    assert (addr.city, addr.state, addr.zip) == ('River City', 'OK', '74111')
    assert addr.address1.startswith('123 Maple')
    assert c.address_full == addr.full and 'River City' in c.address_full
    # The email's domain was made at create; the typed one is a second record, now primary.
    typed = Domain.objects.get(contact=c, path='www.sallytest.com')
    assert c.domain_id == typed.id and c.domain == 'www.sallytest.com'


def test_the_same_value_again_makes_no_second_record_and_blank_deletes_nothing(actor):
    c = Contact.objects.create(email='sally@test.com', name_first='Sally', name_last='Smith')
    save_record(actor, {'phone': '555-0100', 'version': c.version}, model_key='contact', record_id=c.id)
    c = Contact.objects.get(pk=c.pk)
    save_record(actor, {'phone': '555-0100', 'version': c.version}, model_key='contact', record_id=c.id)
    assert Phone.objects.filter(contact=c).count() == 1
    c = Contact.objects.get(pk=c.pk)
    save_record(actor, {'phone': '', 'version': c.version}, model_key='contact', record_id=c.id)
    c = Contact.objects.get(pk=c.pk)
    assert Phone.objects.filter(contact=c).count() == 1 and c.phone == '555-0100'


def test_attention_fills_from_the_names_on_save(actor):
    c = Contact.objects.create(email='new@test.com')
    save_record(actor, {'name_first': 'Sally', 'name_last': 'Smith', 'version': c.version},
                model_key='contact', record_id=c.id)
    assert Contact.objects.get(pk=c.pk).attention == 'Sally Smith'
