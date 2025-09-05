import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.products.models import Item
from apps.products.models.bom import BillOfMaterial

pytestmark = pytest.mark.django_db


def make_item(name: str, **kwargs):
    return Item.objects.create(name=name, kind=Item.KIND_PHYSICAL, **kwargs)


@pytest.mark.bom
@pytest.mark.fast
def test_bom_cycle_prevention():
    parent = make_item('Parent')
    mid = make_item('Mid')
    leaf = make_item('Leaf')
    # Build linear chain parent -> mid -> leaf
    BillOfMaterial.objects.create(parent=parent, component=mid, quantity=Decimal('1'))
    BillOfMaterial.objects.create(parent=mid, component=leaf, quantity=Decimal('1'))
    # Attempt to introduce cycle leaf -> parent should fail
    cyc = BillOfMaterial(parent=leaf, component=parent, quantity=Decimal('1'))
    with pytest.raises(ValidationError):
        cyc.full_clean()


@pytest.mark.bom
@pytest.mark.fast
def test_bom_cost_rollup_simple():
    # parent with one component cost populated in JSON (avg preferred)
    parent = make_item('P2')
    comp = make_item('C2')
    comp.cost = {"avg": 5, "standard": None, "last": None, "landed": None, "currency": "USD", "history": [], "breaks": []}
    comp.save(update_fields=["cost"])
    line = BillOfMaterial.objects.create(parent=parent, component=comp, quantity=Decimal('2'))
    BillOfMaterial.recalc_parent_cost(parent.id)
    parent.refresh_from_db()
    assert line.cost_snapshot in (Decimal('5'), Decimal('5.0000'))
    assert isinstance(parent.cost, dict)
    assert parent.cost['components'].get('snapshot_total') in (10.0, 10.0000)


@pytest.mark.bom
@pytest.mark.fast
def test_bom_rollup_fallback_when_snapshot_missing():
    parent = make_item('P3')
    comp = make_item('C3')
    # Populate live cost AFTER creating BOM line so snapshot is None
    line = BillOfMaterial.objects.create(parent=parent, component=comp, quantity=Decimal('3'))
    assert line.cost_snapshot is None
    comp.cost = {"avg": None, "standard": 2.5, "last": None, "landed": None, "currency": "USD", "history": [], "breaks": []}
    comp.save(update_fields=["cost"])
    BillOfMaterial.recalc_parent_cost(parent.id)
    parent.refresh_from_db()
    # fallback should pick standard (2.5) * qty 3 = 7.5
    assert abs(parent.cost['components']['snapshot_total'] - 7.5) < 1e-9


@pytest.mark.bom
@pytest.mark.fast
def test_bom_rollup_rounding_quantize():
    parent = make_item('P4')
    comp = make_item('C4')
    # Use float for JSON-serializable avg cost (avoid Decimal serialization in JSONField)
    comp.cost = {"avg": 1.234567, "standard": None, "last": None, "landed": None, "currency": "USD", "history": [], "breaks": []}
    comp.save(update_fields=["cost"])
    BillOfMaterial.objects.create(parent=parent, component=comp, quantity=Decimal('1.5'))
    BillOfMaterial.recalc_parent_cost(parent.id)
    parent.refresh_from_db()
    # 1.234567 * 1.5 = 1.8518505 -> quantized to 4 decimals = 1.8519
    assert parent.cost['components']['snapshot_total'] in (1.8519, 1.8519)
