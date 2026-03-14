import pytest
from django.core.management import call_command

from apps.core.models import Contact
from apps.orgs.models import OrgBase, OrgType


@pytest.mark.django_db
def test_sync_customer_contact_company_uses_fk_and_refs_links():
    org = OrgBase.objects.create(
        org_type=OrgType.CUSTOMER,
        company="Acme New Name",
        status="active",
        refs={"links": {}},
        contacts=[],
    )

    via_fk = Contact.objects.create(
        email="via_fk@example.com",
        name_first="Via",
        name_last="Fk",
        company="Old Co",
        customer_id=org.pk,
    )

    via_contact_refs = Contact.objects.create(
        email="via_refs@example.com",
        name_first="Via",
        name_last="Refs",
        company="Old Co",
        refs={"links": {"customer": [{"id": org.pk}]}},
    )

    via_org_refs = Contact.objects.create(
        email="via_org_refs@example.com",
        name_first="Via",
        name_last="OrgRefs",
        company="Old Co",
    )

    unlinked = Contact.objects.create(
        email="unlinked@example.com",
        name_first="No",
        name_last="Link",
        company="Unchanged Co",
    )

    org.refs = {"links": {"contact": [{"id": via_org_refs.pk}]}}
    org.save()

    call_command("sync_customer_contact_company")

    via_fk.refresh_from_db()
    via_contact_refs.refresh_from_db()
    via_org_refs.refresh_from_db()
    unlinked.refresh_from_db()

    assert via_fk.company == "Acme New Name"
    assert via_contact_refs.company == "Acme New Name"
    assert via_org_refs.company == "Acme New Name"
    assert unlinked.company == "Unchanged Co"
