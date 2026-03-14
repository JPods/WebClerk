import pytest

from apps.orgs.models.constants import (
    default_financial,
    flatten_financial_for_type,
    inflate_flat_financial_for_type,
)


@pytest.mark.django_db
def test_flatten_financial_for_customer_merges_common_and_customer_fields():
    financial = default_financial()
    financial["common"]["settings"]["tax_exempt"] = True
    financial["customer"]["balances"]["due"] = 123.45

    flat = flatten_financial_for_type(financial, "customer")

    assert flat["settings"]["tax_exempt"] is True
    assert flat["balances"]["due"] == pytest.approx(123.45)
    assert flat["_org_type"] == "customer"
    assert "common" not in flat
    assert "customer" not in flat


@pytest.mark.django_db
def test_inflate_flat_financial_updates_type_section_and_preserves_common():
    existing = default_financial()
    existing["common"]["settings"]["tax_exempt"] = True

    flat = {
        "balances": {"due": 250},
        "settings": {"tax_exempt": False},
        "custom_metric": {"score": 9},
        "_org_type": "customer",
    }

    inflated = inflate_flat_financial_for_type(flat, "customer", existing=existing)

    assert inflated["customer"]["balances"]["due"] == 250
    assert inflated["common"]["settings"]["tax_exempt"] is False
    assert inflated["customer"]["custom_metric"]["score"] == 9
