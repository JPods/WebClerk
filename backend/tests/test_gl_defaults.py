"""A new org gets its GL defaults.

One test for the rule, not five for the machinery. The rule Bill kept: a new
org comes out with the GL accounts the company's role map assigns it, and a
value the owner set is never overwritten.

The second test is the same rule as the tally reports, on the other half of the
system: an installation with no role map has not failed, it has not been given
one yet. It asks WC_HQ for bundle_gls.json — the chart and the role map that
points into it, together, because a map pointing at accounts that do not exist
produces the same blank field by a longer route.
"""
import pytest
from django.core.management import call_command

from apps.accounts.services import chart
from apps.core.models.setting import Setting
from apps.core.services import installation_init
from apps.orgs.models import OrgBase, OrgType
from apps.products.models import Item

pytestmark = pytest.mark.django_db


def test_new_org_and_item_get_their_gl_defaults():
    """The company role map reaches new records; an owner's value stands."""
    item = Item.objects.create(name="Seed Item", sku="SEED-GL-001", gls={})
    rep = OrgBase.objects.create(company="Seed Rep", org_type=OrgType.REP, gl_accounts={})

    kept_item = Item.objects.create(
        name="Preserve Item", sku="SEED-GL-002", gls={"revenue": "CUSTOM-REV-001"})
    kept_rep = OrgBase.objects.create(
        company="Preserve Rep", org_type=OrgType.REP,
        gl_accounts={"commission": "CUSTOM-COMM-001"})

    call_command("seed_gl_defaults")

    for obj in (item, rep, kept_item, kept_rep):
        obj.refresh_from_db()

    # Filled from the role map.
    assert item.gls.get("revenue")
    assert item.gls.get("inventory")
    assert item.gls.get("cogs")
    assert item.gls.get("purchase")
    assert rep.gl_accounts.get("commission")

    # Never overwritten.
    assert kept_item.gls.get("revenue") == "CUSTOM-REV-001"
    assert kept_rep.gl_accounts.get("commission") == "CUSTOM-COMM-001"


def test_an_installation_with_no_role_map_asks_hq(monkeypatch):
    """An unmapped role sends for bundle_gls.json before it reports anything."""
    company = Setting.objects.filter(purpose="wc:company_profile", is_active=True).first()
    assert company is not None, "the company profile Setting is missing"

    config = dict(company.config or {})
    recommended = dict(config.get("gl_defaults") or {})
    assert recommended.get("sales_revenue"), "no role map to recommend"

    # An installation that has not been given a role map.
    config.pop("gl_defaults", None)
    company.config = config
    company._setting_update_authorized = True
    company.save()
    installation_init.reset_asked()

    asked = {}

    def _bundle_for(name, **kwargs):
        asked["name"] = name
        return ({"settings": [{
            "uuid": str(company.uuid),
            "ida": company.ida or "",
            "name": company.name or "",
            "purpose": "wc:company_profile",
            "config": {"gl_defaults": recommended},
            "metadata": {"foundational": True},
        }]}, "")

    monkeypatch.setattr(installation_init, "fetch_from_hq", _bundle_for)

    code = chart.role_account("sales_revenue", used_by="test")

    assert asked["name"] == "gls", "it asked for the wrong bundle"
    assert code == recommended["sales_revenue"]

    company.refresh_from_db()
    assert (company.config or {}).get("gl_defaults", {}).get("sales_revenue")
