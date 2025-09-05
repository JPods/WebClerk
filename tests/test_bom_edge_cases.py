import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.products.models import Item
from apps.products.models.bom import BillOfMaterial

pytestmark = pytest.mark.django_db


def make_item(name: str):
    return Item.objects.create(name=name, kind=Item.KIND_PHYSICAL)


@pytest.mark.bom
@pytest.mark.fast
def test_alternate_requires_group():
    parent = make_item('AltParent')
    comp = make_item('AltComp')
    bom = BillOfMaterial(parent=parent, component=comp, quantity=Decimal('1'), is_alternate=True)
    with pytest.raises(ValidationError):
        bom.full_clean()
    bom.alternate_group = 'G1'
    # Now should validate
    bom.full_clean()
    bom.save()
    assert bom.is_alternate and bom.alternate_group == 'G1'


@pytest.mark.bom
@pytest.mark.fast
def test_scrap_factor_range_and_yield_derivation():
    parent = make_item('ScrapParent')
    comp = make_item('ScrapComp')
    # invalid negative
    bom = BillOfMaterial(parent=parent, component=comp, quantity=Decimal('1'), scrap_factor=Decimal('-0.1'))
    with pytest.raises(ValidationError):
        bom.full_clean()
    # invalid >=1
    bom.scrap_factor = Decimal('1')
    with pytest.raises(ValidationError):
        bom.full_clean()
    # valid
    bom.scrap_factor = Decimal('0.25')
    bom.full_clean()
    bom.save()
    assert bom.yield_pct == Decimal('0.75')  # 1 - scrap


@pytest.mark.bom
@pytest.mark.fast
def test_effective_date_window_validation():
    parent = make_item('DateParent')
    comp = make_item('DateComp')
    from datetime import date, timedelta
    today = date.today()
    yesterday = today - timedelta(days=1)
    bom = BillOfMaterial(parent=parent, component=comp, quantity=Decimal('1'), effective_from=today, effective_to=yesterday)
    with pytest.raises(ValidationError):
        bom.full_clean()
    # swap to valid
    bom.effective_to = today + timedelta(days=5)
    bom.full_clean()  # should pass


@pytest.mark.bom
@pytest.mark.fast
def test_unique_parent_component_constraint():
    parent = make_item('UniParent')
    comp = make_item('UniComp')
    BillOfMaterial.objects.create(parent=parent, component=comp, quantity=Decimal('1'))
    with pytest.raises(IntegrityError):
        BillOfMaterial.objects.create(parent=parent, component=comp, quantity=Decimal('2'))


@pytest.mark.bom
@pytest.mark.fast
def test_parent_cannot_equal_component():
    item = make_item('SelfItem')
    bom = BillOfMaterial(parent=item, component=item, quantity=Decimal('1'))
    with pytest.raises(ValidationError):
        bom.full_clean()


@pytest.mark.bom
@pytest.mark.fast
def test_bom_alternate_and_scrap_factor_rollup_interaction():
    parent = make_item('RollParent')
    comp_primary = make_item('RollCompPrimary')
    comp_alt = make_item('RollCompAlt')
    # Populate costs
    for c, v in ((comp_primary, 2), (comp_alt, 3)):
        c.cost.update({"avg": v, "currency": "USD"})
        c.save(update_fields=["cost"])
    # Primary line with scrap factor 0.10 (qty 5 -> effective 5 * 1.10)
    l1 = BillOfMaterial.objects.create(parent=parent, component=comp_primary, quantity=Decimal('5'), scrap_factor=Decimal('0.10'))
    # Alternate line in same group (should not alter roll-up since alternates are not auto-excluded here but both counted unless later logic filters)
    l2 = BillOfMaterial.objects.create(parent=parent, component=comp_alt, quantity=Decimal('5'), is_alternate=True, alternate_group='G1')
    BillOfMaterial.recalc_parent_cost(parent.id)
    parent.refresh_from_db()
    total = parent.cost['components']['snapshot_total']
    # Expected: (primary 2 * 5 * 1.10) + (alt 3 * 5) = 11 + 15 = 26 (approx)
    assert abs(total - 26) < 1e-6
    # Document assumption: alternates currently included; future exclusion logic would change expected total
