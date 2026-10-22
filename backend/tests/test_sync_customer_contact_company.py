"""sync_customer_contact_company names a customer's contacts after it. Its contacts are the
contacts whose customer FK points at it — the one source (Bill, 2026-10-17); a copy in
either side's refs.links links nothing."""
import pytest
from django.core.management import call_command

from apps.core.models import Contact
from apps.orgs.models import OrgBase, OrgType


@pytest.mark.django_db
def test_sync_customer_contact_company_follows_the_fk_only():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company="Acme New Name",
                                 status="active", refs={"links": {}}, contacts=[])
    via_fk = Contact.objects.create(email="via_fk@example.com", name_first="Via",
                                    name_last="Fk", company="Old Co", customer_id=org.pk)
    via_contact_refs = Contact.objects.create(
        email="via_refs@example.com", name_first="Via", name_last="Refs", company="Old Co",
        refs={"links": {"customer": [{"id": org.pk}]}})
    via_org_refs = Contact.objects.create(email="via_org_refs@example.com", name_first="Via",
                                          name_last="OrgRefs", company="Old Co")
    OrgBase.objects.filter(pk=org.pk).update(
        refs={"links": {"contact": [{"id": via_org_refs.pk}]}})
    Contact.objects.filter(pk=via_fk.pk).update(company="Old Co")

    call_command("sync_customer_contact_company")

    for c in (via_fk, via_contact_refs, via_org_refs):
        c.refresh_from_db()
    assert via_fk.company == "Acme New Name"
    assert via_contact_refs.company == "Old Co"
    assert via_org_refs.company == "Old Co"
