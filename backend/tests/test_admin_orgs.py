import pytest
from django.contrib.admin.sites import site
from apps.orgs.models import OrgBase

@pytest.mark.django_db
def test_orgbase_registered_in_admin():
    assert site.is_registered(OrgBase)
    # Basic sanity: get model admin and verify list_display includes version
    ma = site._registry[OrgBase]
    assert 'version' in ma.list_display
