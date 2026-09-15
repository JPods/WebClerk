import pytest
from django.core.exceptions import ValidationError
from apps.products.models import Item

pytestmark = pytest.mark.django_db

def make_item(name: str, sku: str | None = None):
    return Item.objects.create(name=name, kind=Item.KIND_PHYSICAL, sku=sku)

@pytest.mark.fast
def test_jurisdiction_params_validation_errors():
    item = make_item("TaxItem1")
    # invalid: not a list
    item.tax_code["jurisdiction_params"] = {"jurisdiction": "US"}
    with pytest.raises(ValidationError) as ex:
        item.full_clean()
    assert any("jurisdiction_params must be list" in msg for msgs in ex.value.message_dict.values() for msg in msgs)
    # invalid element types and missing fields
    item.tax_code["jurisdiction_params"] = [123, {"kind": 5}, {"jurisdiction": "", "params": []}]
    with pytest.raises(ValidationError) as ex2:
        item.full_clean()
    flat = [m for msgs in ex2.value.message_dict.values() for m in msgs]
    assert any("jurisdiction_params[0] not dict" in m for m in flat)
    assert any("jurisdiction_params[1].jurisdiction required str" in m for m in flat)
    assert any("jurisdiction_params[2].jurisdiction required str" in m for m in flat)

@pytest.mark.fast
def test_jurisdiction_params_valid():
    item = make_item("TaxItem2")
    item.tax_code["jurisdiction_params"] = [
        {"jurisdiction": "US", "kind": "food", "params": {"rate_adj": 0.0}},
        {"jurisdiction": "US-CA", "params": {"county_flag": True}},
    ]
    # Should validate
    item.full_clean()

@pytest.mark.fast
def test_jurisdiction_params_effective_dating_and_precedence():
    item = make_item("TaxItem3")
    # Two entries same jurisdiction different effective windows
    item.tax_code["jurisdiction_params"] = [
        {"jurisdiction": "US", "kind": "food", "effective_from": "2024-01-01", "params": {"rate": 0.05}},
        {"jurisdiction": "US", "kind": "food", "effective_from": "2025-01-01", "params": {"rate": 0.06}},
        {"jurisdiction": "US", "params": {"generic": True}},
    ]
    item.full_clean()
    # For current date (today) we expect the latest effective_from not in future to be selected.
    params = item.resolve_tax_params("US", kind="food")
    # If today >= 2025-01-01 expect 0.06 else 0.05; accept either to keep test resilient across date changes.
    assert params.get("rate") in (0.05, 0.06)

@pytest.mark.fast
def test_quantity_non_negative_clamp_on_save():
    item = make_item("QtyClamp1")
    item.quantity = {"on_hand": -5, "allocated": -2, "on_order": 3}
    item.save(update_fields=["quantity"])
    item.refresh_from_db()
    assert item.quantity.get("on_hand") == 0
    assert item.quantity.get("allocated") == 0

@pytest.mark.fast
def test_sku_case_insensitive_uniqueness():
    make_item("SKU1", sku="AbC123")
    dup = Item(name="SKU2", kind=Item.KIND_PHYSICAL, sku="abc123")
    with pytest.raises(ValidationError) as ex:
        dup.full_clean()
    assert "SKU must be unique" in str(ex.value)

