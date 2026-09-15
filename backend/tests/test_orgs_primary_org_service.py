from types import SimpleNamespace

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.orgs.models import OrgBase, OrgType
from apps.orgs.services.primary_org import (
    PRIMARY_ORG_SETTING_NAME,
    PRIMARY_ORG_SETTING_PARENT_MODEL,
    PRIMARY_ORG_SETTING_PURPOSE,
    get_primary_org,
    get_primary_org_id,
    set_primary_org,
)


@pytest.mark.django_db
def test_set_primary_org_creates_setting_and_getters_work():
    org = OrgBase.objects.create(
        org_type=OrgType.CUSTOMER,
        company="Primary Co",
        status="active",
        gl_accounts={
            "sales": "REV-SALES-000",
            "inventory": "ASSET-INVENTORY-000",
            "cogs": "COGS-PRODUCTS-000",
        },
    )

    setting = set_primary_org(org)

    assert setting.purpose == PRIMARY_ORG_SETTING_PURPOSE
    assert setting.name == PRIMARY_ORG_SETTING_NAME
    assert setting.parent_model == PRIMARY_ORG_SETTING_PARENT_MODEL
    assert setting.data["org_id"] == org.pk
    assert setting.data["default_gl_accounts"]["revenue"] == "REV-SALES-000"
    assert setting.data["default_gl_accounts"]["inventory"] == "ASSET-INVENTORY-000"
    assert setting.data["default_gl_accounts"]["cogs"] == "COGS-PRODUCTS-000"
    assert get_primary_org_id() == org.pk
    assert get_primary_org().pk == org.pk


@pytest.mark.django_db
def test_set_primary_org_requires_superuser_actor():
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company="Actor Co", status="active")
    actor = SimpleNamespace(is_superuser=False)

    with pytest.raises(PermissionDenied):
        set_primary_org(org, actor=actor)


@pytest.mark.django_db
def test_set_primary_org_rejects_inactive_org():
    org = OrgBase.objects.create(
        org_type=OrgType.CUSTOMER,
        company="Inactive Co",
        status="active",
        is_active=False,
    )

    with pytest.raises(ValidationError):
        set_primary_org(org)
