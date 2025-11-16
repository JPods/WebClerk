import pytest
from apps.orgs.models import OrgBase, Customer, OrgType

@pytest.mark.django_db
def test_create_orgbase_and_proxy():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Proto Cust', status='active')
    assert org.pk is not None
    assert org.org_type == OrgType.CUSTOMER
    # proxy manager should see it
    assert Customer.objects.count() == 1

@pytest.mark.django_db
def test_add_contact_helper_marks_keywords_dirty():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Has Contacts', status='active')
    org.add_contact(contact_id=123, name='Jane Contact', role='decision')
    v_before = org.version
    org.save(expected_version=v_before)
    # contact appended
    assert any(c.get('name') == 'Jane Contact' for c in org.contacts)
    # keywords should be flagged dirty for later refresh
    flags = org.metadata.get('flags', {})
    assert flags.get('keywords_pending') is True

@pytest.mark.django_db
def test_credit_utilization_computation():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Credit Co', status='active')
    org.financial['credit'] = {'limit': 1000, 'used': 250}
    v = org.version
    org.save(expected_version=v)
    assert abs(org.credit_utilization() - 0.25) < 1e-9

@pytest.mark.django_db
def test_primary_domain_none_and_then_set():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Domainless', status='active')
    assert org.primary_domain() is None
    org.domains.append({'domain': 'example.com', 'verified': True})
    v = org.version
    org.save(expected_version=v)
    assert org.primary_domain() == 'example.com'
