"""An item's margin_pct is its own: list price against the company's cost basis, the one
formula price_resolver uses on a line (readme 104 item 7: 0.00 on every item beside a price
and cost that imply 40%). Unknown when either side is unknown; never 0 for 'not computed'."""
from decimal import Decimal

import pytest

from apps.products.models import Item

pytestmark = pytest.mark.django_db


def test_margin_pct_derives_from_price_and_cost_on_save():
    item = Item.objects.create(ida='MARGIN-1', name='Margin one',
                               price={'base': '11.95'}, cost={'standard': '7.17'})
    assert Item.objects.get(pk=item.pk).margin_pct == Decimal('40.00')


def test_margin_pct_is_unknown_without_a_cost():
    item = Item.objects.create(ida='MARGIN-2', name='Margin two', price={'base': '11.95'})
    assert Item.objects.get(pk=item.pk).margin_pct is None


def test_margin_pct_follows_a_price_change():
    item = Item.objects.create(ida='MARGIN-3', name='Margin three',
                               price={'base': '10.00'}, cost={'standard': '5.00'})
    item.price = {**item.price, 'base': '20.00'}
    item.save()
    assert Item.objects.get(pk=item.pk).margin_pct == Decimal('75.00')
