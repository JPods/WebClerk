"""/wcapi/_bootstrap/ sends only the dotted paths listed for the user's role
(company profile config.bootstrap_exposure). Unlisted roles get nothing."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Setting

PORTAL = ["currency.*", "company.name", "company.website", "document_text.invoice_comment"]
EXPOSURE = {
    "staff": ["currency.*", "inventory.do_serial_nums", "costing.unit_cost_default",
              "company.name", "company.legal_name", "company.address_full", "company.email",
              "company.website", "company.phone", "document_text.invoice_comment"],
    "user_customer": PORTAL, "user_vendor": PORTAL, "user_manufacturer": PORTAL, "user_rep": PORTAL,
}


@pytest.fixture
def company_profile(db):
    s = Setting.objects.get(ida="company-profile", purpose="wc:company_profile")
    config = dict(s.config or {})
    config["bootstrap_exposure"] = EXPOSURE
    config["company"] = {"name": "Test Co", "legal_name": "Test Co LLC", "phone": "555-0100",
                         "email": "co@example.com", "website": "https://example.com",
                         "address_full": "1 Main St", "tax_id": "00-0000000"}
    config["inventory"] = {"costing_method": "fifo", "unit_cost_default": "last_cost",
                           "unit_cost_precision": 5}
    s.config = config
    s.prefs = {"currency": {"symbol": "$", "code": "USD", "unit_price_precision": 2},
               "inventory": {"do_serial_nums": True},
               "commissions": {"rate": 0.1}, "fiscal": {"year_start": "01-01"},
               "document_text": {"invoice_comment": "Thank you"}}
    s._setting_update_authorized = True
    s.save()
    return s


def _user(email, *, staff=False, roles=None):
    u = get_user_model().objects.create_user(email=email, password=None,
                                             name_first="T", name_last="U", username=email)
    u.is_staff = staff
    u.refs = {"roles": roles or []}
    u.save()
    return u


def _get(user, **params):
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/wcapi/_bootstrap/", params)
    return resp


def _payload(resp):
    assert resp.status_code == 200, resp.content
    body = resp.json()
    while isinstance(body, dict) and "_version" not in body and "data" in body:
        body = body["data"]
    return body


@pytest.mark.django_db
def test_staff_gets_costing_and_phone(company_profile):
    p = _payload(_get(_user("staff@example.com", staff=True)))
    assert p["costing"] == {"unit_cost_default": "last_cost"}
    assert p["company"]["phone"] == "555-0100"
    assert p["inventory"] == {"do_serial_nums": True}
    assert "tax_id" not in p["company"]
    assert "commissions" not in p and "fiscal" not in p


@pytest.mark.django_db
def test_customer_gets_only_portal_paths(company_profile):
    p = _payload(_get(_user("cust@example.com", roles=["user_customer"])))
    assert p["currency"]["code"] == "USD"
    assert p["company"] == {"name": "Test Co", "website": "https://example.com"}
    assert "phone" not in p["company"]
    assert "costing" not in p and "commissions" not in p and "inventory" not in p
    assert p["document_text"] == {"invoice_comment": "Thank you"}


@pytest.mark.django_db
def test_unlisted_role_gets_nothing(company_profile):
    p = _payload(_get(_user("sales@example.com", roles=["user_sales"])))
    assert set(p) == {"_version"}


@pytest.mark.django_db
def test_no_roles_gets_nothing(company_profile):
    p = _payload(_get(_user("none@example.com")))
    assert set(p) == {"_version"}


@pytest.mark.django_db
def test_refs_cannot_claim_staff(company_profile):
    p = _payload(_get(_user("fake@example.com", roles=["staff"])))
    assert set(p) == {"_version"}


@pytest.mark.django_db
def test_version_differs_by_role_and_304_per_role(company_profile):
    staff = _user("staff2@example.com", staff=True)
    cust = _user("cust2@example.com", roles=["user_customer"])
    v_staff = _payload(_get(staff))["_version"]
    v_cust = _payload(_get(cust))["_version"]
    assert v_staff != v_cust
    assert _get(staff, v=v_staff).status_code == 304
    assert _get(cust, v=v_staff).status_code == 200


@pytest.mark.django_db
def test_missing_exposure_section_fails_closed(company_profile):
    s = company_profile
    config = dict(s.config)
    config.pop("bootstrap_exposure")
    s.config = config
    s._setting_update_authorized = True
    s.save()
    p = _payload(_get(_user("staff3@example.com", staff=True)))
    assert set(p) == {"_version"}
