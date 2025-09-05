import pytest
from decimal import Decimal
from apps.products.models import Item
from apps.products.models.bom import BillOfMaterial

pytestmark = pytest.mark.django_db

def make_item(name: str):
    return Item.objects.create(name=name, kind=Item.KIND_PHYSICAL)

@pytest.mark.bom
@pytest.mark.fast
def test_multilevel_bom_rollup():
    # Structure: Parent -> Mid (qty2), Parent -> LeafA (qty1)
    # Mid -> LeafB (qty3)
    parent = make_item('MLParent')
    mid = make_item('MLMid')
    leaf_a = make_item('MLLeafA')
    leaf_b = make_item('MLLeafB')
    # Assign component costs
    for itm, cost_val in ((leaf_a, 4), (leaf_b, 2), (mid, None)):
        if cost_val is not None:
            itm.cost.update({"avg": cost_val, "currency": "USD"})
            itm.save(update_fields=["cost"])
    # Build BOM
    BillOfMaterial.objects.create(parent=parent, component=mid, quantity=Decimal('2'))
    BillOfMaterial.objects.create(parent=parent, component=leaf_a, quantity=Decimal('1'))
    BillOfMaterial.objects.create(parent=mid, component=leaf_b, quantity=Decimal('3'))
    # First roll-up mid: should capture leaf_b cost snapshot (2 * 3 = 6) via fallback since mid cost_snapshot lines use component snapshots only.
    BillOfMaterial.recalc_parent_cost(mid.id)
    mid.refresh_from_db()
    # mid aggregated component cost
    mid_total = mid.cost['components']['snapshot_total']
    assert abs(mid_total - 6) < 1e-6
    # Now roll-up parent (mid snapshot cost used, not recomputed inline)
    BillOfMaterial.recalc_parent_cost(parent.id)
    parent.refresh_from_db()
    parent_total = parent.cost['components']['snapshot_total']
    # With propagation: mid avg cost populated from its roll-up (6) then used in parent roll-up: 6 * qty2 + 4 * 1 = 16
    assert abs(parent_total - 16) < 1e-6
