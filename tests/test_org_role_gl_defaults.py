import pytest

from apps.orgs.models import OrgBase, OrgType

pytestmark = pytest.mark.django_db


def test_new_rep_gets_default_activity_gl_account():
    rep = OrgBase.objects.create(org_type=OrgType.REP, display_name="Rep A", gl_accounts={})

    assert isinstance(rep.gl_accounts, dict)
    assert rep.gl_accounts.get("activity")
    assert rep.gl_accounts.get("commission")


def test_new_vendor_and_manufacturer_get_purchase_activity_gl_account():
    vendor = OrgBase.objects.create(org_type=OrgType.VENDOR, display_name="Vendor A", gl_accounts={})
    manufacturer = OrgBase.objects.create(org_type=OrgType.MANUFACTURER, display_name="Manufacturer A", gl_accounts={})

    assert vendor.gl_accounts.get("activity")
    assert vendor.gl_accounts.get("purchase")
    assert manufacturer.gl_accounts.get("activity")
    assert manufacturer.gl_accounts.get("purchase")


def test_new_employee_gets_default_activity_gl_account():
    employee = OrgBase.objects.create(org_type=OrgType.EMPLOYEE, display_name="Employee A", gl_accounts={})

    assert employee.gl_accounts.get("activity")
    assert employee.gl_accounts.get("expense")
