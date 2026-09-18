import pytest
from django.core.exceptions import ValidationError
from apps.products.models import Item

pytestmark = pytest.mark.django_db

def make_item(name: str):
    return Item.objects.create(name=name, kind=Item.KIND_PHYSICAL)

@pytest.mark.fast
def test_price_qty_break_negative_min_qty():
    it = make_item("NegQty1")
    it.price["qty_breaks"] = [{"min_qty": -1, "unit_price": 10}]
    with pytest.raises(ValidationError):
        it.full_clean()

@pytest.mark.fast
def test_cost_break_negative_min_qty():
    it = make_item("NegQty2")
    it.cost["breaks"] = [{"min_qty": -5, "unit_cost": 3}]
    with pytest.raises(ValidationError):
        it.full_clean()

@pytest.mark.fast
def test_set_quantity_negative_on_hand_not_blocked_but_no_available_derivation():
    it = make_item("NegQty3")
    # Directly set negative on_hand to see it persists (business rule may later forbid)
    it.set_quantity(on_hand=-10, allocated=0)
    it.save()
    it.refresh_from_db()
    assert it.quantity.get("on_hand") == -10
    # available derived = on_hand - allocated (-10)
    assert it.quantity.get("available") == -10

