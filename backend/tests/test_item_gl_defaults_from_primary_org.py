import pytest

from apps.orgs.models import OrgBase, OrgType
from apps.orgs.services.primary_org import set_primary_org
from apps.products.models import Item

pytestmark = pytest.mark.django_db


def _setup_primary_org() -> OrgBase:
    org = OrgBase.objects.create(
        org_type=OrgType.CUSTOMER,
        company="Primary Defaults Co",
        status="active",
        gl_accounts={
            "sales": "REV-SALES-000",
            "inventory": "ASSET-INVENTORY-000",
            "cogs": "COGS-PRODUCTS-000",
            "purchase": "LIAB-AP-000",
            "variance": "COGS-VARIANCE-000",
        },
    )
    set_primary_org(org)
    return org


def test_item_save_seeds_missing_gls_from_primary_org_setting():
    _setup_primary_org()

    item = Item.objects.create(name="Default GL Item", kind=Item.KIND_PHYSICAL, gls={})

    assert item.gls.get("revenue") == "REV-SALES-000"
    assert item.gls.get("inventory") == "ASSET-INVENTORY-000"
    assert item.gls.get("cogs") == "COGS-PRODUCTS-000"
    assert item.gls.get("purchase") == "LIAB-AP-000"
    assert item.gls.get("variance") == "COGS-VARIANCE-000"


def test_item_save_does_not_overwrite_existing_gls_values():
    _setup_primary_org()

    item = Item.objects.create(
        name="Preserve GL Item",
        kind=Item.KIND_PHYSICAL,
        gls={"revenue": "CUSTOM-REV-001"},
    )

    assert item.gls.get("revenue") == "CUSTOM-REV-001"
    assert item.gls.get("inventory") == "ASSET-INVENTORY-000"
    assert item.gls.get("cogs") == "COGS-PRODUCTS-000"
    assert item.gls.get("purchase") == "LIAB-AP-000"
