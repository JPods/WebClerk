import pytest
from django.utils import timezone
from apps.orgs.models import OrgBase, OrgType

@pytest.mark.django_db
def test_aspect_prune_contacts_limit():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Prune Co', status='active')
    # Add over limit
    for i in range(org.ASPECT_LIMITS['contacts'] + 5):
        org.add_contact(contact_id=i, name=f'Contact {i}')
    v = org.version
    org.save(expected_version=v)
    assert len(org.contacts) == org.ASPECT_LIMITS['contacts']

@pytest.mark.django_db
def test_refresh_aspects_updates_metadata_counts():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Meta Co', status='active')
    org.add_contact(contact_id=1, name='A')
    v = org.version
    org.refresh_and_save(expected_version=v)
    aspects = org.metadata.get('versioning', {}).get('aspects', {})
    assert 'contacts' in aspects and aspects['contacts']['count'] >= 1
