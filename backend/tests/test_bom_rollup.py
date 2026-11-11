"""A BOM's cost rolls up from its parts, on the server, and the screen can ask what it would be with
unsaved changes (Bill, 2026-11-01: "sum.cost by sub.components in a BOM"; send changes back to
the server rather than calculate twice)."""
import secrets
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.core.services.tree_calc import roll_up
from apps.products.models import Item
from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.services.bom_ops import build_cost, expand_tree

pytestmark = pytest.mark.django_db


def _item(ida, cost=None):
    return Item.objects.create(ida=ida, name=ida, kind=Item.KIND_PHYSICAL,
                               cost={'avg': str(cost)} if cost is not None else {})


@pytest.fixture
def cart():
    """zz CART = 2 × zz WHEEL (1 TIRE at 12 + 1 TUBE at 6) + 1 FLOOR at 45 → 81."""
    cart, wheel = _item('t-CART'), _item('t-WHEEL')
    tire, tube, floor = _item('t-TIRE', 12), _item('t-TUBE', 6), _item('t-FLOOR', 45)
    lines = {
        'wheel': BillOfMaterial.objects.create(parent_item=cart, child_item=wheel, quantity=Decimal('2'), sequence=1),
        'floor': BillOfMaterial.objects.create(parent_item=cart, child_item=floor, quantity=Decimal('1'), sequence=2),
        'tire': BillOfMaterial.objects.create(parent_item=wheel, child_item=tire, quantity=Decimal('1'), sequence=1),
        'tube': BillOfMaterial.objects.create(parent_item=wheel, child_item=tube, quantity=Decimal('1'), sequence=2),
    }
    return cart, {'tire': tire, 'wheel': wheel, 'tube': tube, 'floor': floor}, lines


def test_roll_up_sums_children_bottom_first():
    rows = [(1, 0, 2), (2, 12, 1), (2, 6, 1), (1, 45, 1)]          # (level, own, weight)
    got = roll_up(rows, level=lambda r: r[0], own=lambda r: Decimal(r[1]), weight=lambda r: Decimal(r[2]))
    assert got == [Decimal(18), Decimal(12), Decimal(6), Decimal(45)]


def test_a_subassembly_costs_what_its_parts_cost(cart):
    parent, items, _lines = cart
    rows = expand_tree(parent.id)
    assert [r.item_id for r in rows] == [items[k].id for k in ('wheel', 'tire', 'tube', 'floor')]  # depth-first
    wheel = rows[0]
    assert wheel.cost_rollup == Decimal(18) and wheel.cost_extended == Decimal(36)
    assert build_cost(rows) == Decimal(81)                     # each part counted once
    assert build_cost(expand_tree(parent.id, Decimal(3))) == Decimal(243)


def test_what_if_recalculates_without_saving(cart):
    parent, items, lines = cart
    client = APIClient()
    client.force_authenticate(Contact.objects.create_superuser(
        email='t-bom@example.com', password=secrets.token_urlsafe(16)))
    url = f'/wcapi/products/items/{parent.id}/bom/expand/'

    r = client.post(url, {'what_if': {'cost': {items['tire'].id: 20}, 'quantity': {lines['wheel'].id: 3}}},
                    format='json', HTTP_HOST='localhost')
    assert r.status_code == 200, r.content
    assert r.json()['data']['total_cost'] == 3 * (20 + 6) + 45     # 123

    lines['wheel'].refresh_from_db()
    items['tire'].refresh_from_db()
    assert lines['wheel'].quantity == Decimal(2) and Decimal(str(items['tire'].cost['avg'])) == Decimal(12)
    assert client.get(url, HTTP_HOST='localhost').json()['data']['total_cost'] == 81


def test_a_bad_what_if_is_refused(cart):
    parent, _items, _lines = cart
    client = APIClient()
    client.force_authenticate(Contact.objects.create_superuser(
        email='t-bom2@example.com', password=secrets.token_urlsafe(16)))
    r = client.post(f'/wcapi/products/items/{parent.id}/bom/expand/',
                    {'what_if': {'cost': {'1': 'lots'}}}, format='json', HTTP_HOST='localhost')
    assert r.status_code == 400
