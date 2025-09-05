import pytest
from decimal import Decimal
from apps.products.models import Item

pytestmark = pytest.mark.django_db

def make_item(name: str):
    return Item.objects.create(name=name, kind=Item.KIND_PHYSICAL)

@pytest.mark.fast
def test_price_base_history_rotation():
    it = make_item("HistItem1")
    # initial base set
    it.price["base"] = 10
    it.save()
    # mutate base many times (> 55) to trigger rotation trimming to 50 entries
    for i in range(60):
        it.price["base"] = 10 + i + 1  # ensure change
        it.save(update_fields=["price"])
    it.refresh_from_db()
    hist = it.price.get("history") or []
    assert len(hist) <= 50
    # Ensure last change recorded
    assert hist[-1]["new"] == it.price["base"]
    # Ensure ordering preserved (increasing changes)
    olds = [h["old"] for h in hist]
    assert olds == sorted(olds)

@pytest.mark.fast
def test_cost_field_change_tracking_and_rotation():
    it = make_item("HistItem2")
    it.cost.update({"standard": 5, "avg": 5, "last": None, "landed": None})
    it.save()
    # change multiple cost fields repeatedly
    for i in range(70):
        it.cost["standard"] = 5 + i + 1
        it.cost["avg"] = 5 + (i + 1) * 2
        it.save(update_fields=["cost"])
    it.refresh_from_db()
    hist = it.cost.get("history") or []
    assert len(hist) <= 50
    # Each entry contains field, old, new
    assert all(set(e.keys()) >= {"field", "old", "new", "dt_utc"} for e in hist)
    # Final entries reflect most recent modifications for both tracked fields
    last_fields = {e["field"] for e in hist[-2:]}
    assert {"standard", "avg"}.issubset(last_fields)

