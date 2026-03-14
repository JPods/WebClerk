import pytest
from django.core.management import call_command

from apps.communications.models import Address, Domain, Email, Phone
from apps.core.models import Contact


@pytest.mark.django_db
def test_contact_communications_maintenance_creates_and_links_missing_rows():
    c = Contact.objects.create(
        email="maint@example.com",
        phone="(555) 1212",
        domain="example.com",
        address_full="123 Main St",
        name_first="Main",
        name_last="Contact",
    )

    call_command("contact_communications_maintenance", contact_id=c.id)

    c.refresh_from_db()
    assert c.email_id
    assert c.phone_id
    assert c.domain_id
    assert c.address_id

    e = Email.objects.get(pk=c.email_id)
    p = Phone.objects.get(pk=c.phone_id)
    d = Domain.objects.get(pk=c.domain_id)
    a = Address.objects.get(pk=c.address_id)

    assert e.contact_id == c.id
    assert p.contact_id == c.id
    assert d.contact_id == c.id
    assert a.contact_id == c.id

    links = (c.refs or {}).get("links", {})
    assert any(isinstance(item, dict) and item.get("id") == e.id for item in links.get("email", []))
    assert any(isinstance(item, dict) and item.get("id") == p.id for item in links.get("phone", []))
    assert any(isinstance(item, dict) and item.get("id") == d.id for item in links.get("domain", []))
    assert any(isinstance(item, dict) and item.get("id") == a.id for item in links.get("address", []))

    e_links = ((e.refs or {}).get("links") or {}).get("contact", [])
    assert any((isinstance(item, dict) and item.get("id") == c.id) or item == c.id for item in e_links)


@pytest.mark.django_db
def test_contact_communications_maintenance_claims_unowned_matching_records():
    c = Contact.objects.create(
        email="claim@example.com",
        phone="555-3333",
        domain="claim.test",
        address_full="500 Side Ave",
        name_first="Claim",
        name_last="Owner",
    )

    Email.objects.create(email="claim@example.com", contact=None)
    Phone.objects.create(number="5553333", contact=None)
    Domain.objects.create(path="claim.test", contact=None)
    Address.objects.create(full="500 Side Ave", address1="500 Side Ave", contact=None)

    call_command("contact_communications_maintenance", contact_id=c.id)

    c.refresh_from_db()
    assert Email.objects.get(pk=c.email_id).contact_id == c.id
    assert Phone.objects.get(pk=c.phone_id).contact_id == c.id
    assert Domain.objects.get(pk=c.domain_id).contact_id == c.id
    assert Address.objects.get(pk=c.address_id).contact_id == c.id
