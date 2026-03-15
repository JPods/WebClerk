import pytest
from django.core.management import call_command

from apps.orgs.models import OrgBase, OrgType
from apps.products.models import Item
from apps.transactions.models import PaymentMethod


@pytest.mark.django_db
def test_seed_gl_defaults_backfills_items_reps_payment_methods():
    item = Item.objects.create(name="Seed Item", sku="SEED-GL-001", gls={})
    rep = OrgBase.objects.create(display_name="Seed Rep", org_type=OrgType.REP, gl_accounts={})
    method = PaymentMethod.objects.create(name="Cash", metadata={})

    call_command("seed_gl_defaults")

    item.refresh_from_db()
    rep.refresh_from_db()
    method.refresh_from_db()

    assert isinstance(item.gls, dict)
    assert item.gls.get("revenue")
    assert item.gls.get("inventory")
    assert item.gls.get("cogs")
    assert item.gls.get("purchase")

    assert isinstance(rep.gl_accounts, dict)
    assert rep.gl_accounts.get("commission")

    assert isinstance(method.metadata, dict)
    method_gl = (method.metadata or {}).get("gl_accounts") or {}
    assert method_gl.get("receipt")


@pytest.mark.django_db
def test_seed_gl_defaults_does_not_overwrite_existing_values():
    item = Item.objects.create(
        name="Preserve Item",
        sku="SEED-GL-002",
        gls={"revenue": "CUSTOM-REV-001"},
    )
    rep = OrgBase.objects.create(
        display_name="Preserve Rep",
        org_type=OrgType.REP,
        gl_accounts={"commission": "CUSTOM-COMM-001"},
    )
    method = PaymentMethod.objects.create(
        name="Wire Transfer",
        metadata={"gl_accounts": {"receipt": "CUSTOM-REC-001"}},
    )

    call_command("seed_gl_defaults")

    item.refresh_from_db()
    rep.refresh_from_db()
    method.refresh_from_db()

    assert item.gls.get("revenue") == "CUSTOM-REV-001"
    assert rep.gl_accounts.get("commission") == "CUSTOM-COMM-001"
    assert ((method.metadata or {}).get("gl_accounts") or {}).get("receipt") == "CUSTOM-REC-001"
