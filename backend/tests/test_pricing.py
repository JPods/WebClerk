"""Pricing and costing — one behavior per side (Bill, 2026-10-22).

resolve_price: price_locked → catalog line → level (explicit else the customer's) with
qty breaks and a universal % → list price; each result carries its cost and margin.
resolve_cost: the company basis → standard (not-tracked: standard); each result carries
the list price it feeds. Price levels are retail, wholesale, distributor, sample — only.
"""
from decimal import Decimal

import pytest

from apps.products.services.price_resolver import (
    named_price_level, price_lines, resolve_cost, resolve_price,
)

PRICES = {'base': 100, 'retail': 100, 'wholesale': 75, 'distributor': 60, 'sample': 50}


class TestNamedPriceLevel:

    @pytest.mark.parametrize('given,stored', [
        ('wholesale', 'wholesale'), ('Wholesale', 'wholesale'), (' retail ', 'retail'),
        ('', ''), (None, ''),
    ])
    def test_the_four_words_in_any_case(self, given, stored):
        assert named_price_level(given) == stored

    @pytest.mark.parametrize('given', ['A', 'B', 'employee', 'base', 'msrp'])
    def test_anything_else_is_refused_naming_the_four(self, given):
        with pytest.raises(ValueError, match='retail, wholesale, distributor, sample'):
            named_price_level(given)


def _item(price=None, cost=None, not_tracked=False):
    from tests.conftest import ItemFactory
    item = ItemFactory()
    item.price = dict(PRICES if price is None else price)
    item.cost = dict({'standard': 40, 'last': 45} if cost is None else cost)
    item.is_not_tracked = not_tracked
    item.save()
    return item


def _customer(level=''):
    from tests.conftest import CustomerFactory
    customer = CustomerFactory()
    customer.__class__.objects.filter(pk=customer.pk).update(price_level=level)
    return customer


@pytest.mark.django_db
class TestResolveCost:

    def test_company_default_basis_is_last(self):
        cost = resolve_cost(_item())
        assert (cost.unit, cost.basis) == (Decimal('45'), 'last')

    def test_basis_without_a_cost_falls_to_standard(self):
        cost = resolve_cost(_item(cost={'standard': 40}), basis='avg')
        assert (cost.unit, cost.basis) == (Decimal('40'), 'standard')

    def test_no_basis_and_no_standard_takes_the_cost_it_has(self):
        cost = resolve_cost(_item(cost={'avg': 12}))       # e.g. a BOM rollup
        assert (cost.unit, cost.basis) == (Decimal('12'), 'avg')

    def test_not_tracked_is_its_standard_rate(self):
        cost = resolve_cost(_item(cost={'standard': 30, 'last': 45}, not_tracked=True))
        assert (cost.unit, cost.basis) == (Decimal('30'), 'standard')

    def test_no_cost_is_zero_with_basis_none(self):
        cost = resolve_cost(_item(cost={}))
        assert (cost.unit, cost.basis, cost.margin_pct) == (Decimal('0'), 'none', None)

    def test_cost_names_the_list_price_it_feeds(self):
        cost = resolve_cost(_item())
        assert cost.list_price == Decimal('100')
        assert cost.margin_pct == Decimal('55.00')


@pytest.mark.django_db
class TestResolvePrice:

    def test_no_customer_is_list_price(self):
        result = resolve_price(_item())
        assert (result.price, result.resolved_by) == (Decimal('100.00'), 'list_price')

    def test_customer_level_applies(self):
        result = resolve_price(_item(), customer_id=_customer('wholesale').pk, qty=5)
        assert (result.price, result.resolved_by, result.price_level) == (
            Decimal('75.00'), 'price_level', 'wholesale')

    def test_explicit_level_beats_the_customer(self):
        result = resolve_price(_item(), customer_id=_customer('retail').pk, level='sample')
        assert (result.price, result.price_level) == (Decimal('50.00'), 'sample')

    def test_level_without_a_price_is_list_price(self):
        item = _item(price={'retail': 100})
        result = resolve_price(item, level='wholesale')
        assert (result.price, result.resolved_by) == (Decimal('100.00'), 'list_price')

    def test_qty_break_applies_when_lower_than_the_level(self):
        item = _item(price={**PRICES, 'qty_breaks': [
            {'min_qty': 10, 'unit_price': 95},
            {'min_qty': 50, 'unit_price': 70},
        ]})
        assert resolve_price(item, level='retail', qty=9).price == Decimal('100.00')
        assert resolve_price(item, level='retail', qty=10).price == Decimal('95.00')
        assert resolve_price(item, level='wholesale', qty=10).price == Decimal('75.00')
        result = resolve_price(item, level='wholesale', qty=50)
        assert (result.price, result.qty_break['min_qty']) == (Decimal('70.00'), 50)

    def test_price_locked_wins(self):
        result = resolve_price(_item(), level='wholesale', price_locked_value=Decimal('12.5'))
        assert (result.price, result.resolved_by, result.price_locked) == (
            Decimal('12.50'), 'price_locked', True)

    def test_price_names_its_cost_and_margin(self):
        result = resolve_price(_item(), level='wholesale')
        assert (result.unit_cost, result.cost_basis) == (Decimal('45'), 'last')
        assert result.margin_pct == Decimal('40.00')          # (75 - 45) / 75

    def test_below_company_floor_is_flagged_not_blocked(self):
        result = resolve_price(_item(cost={'last': 70}), level='wholesale')
        assert result.price == Decimal('75.00')
        assert result.margin_floor == Decimal('15')
        assert result.below_margin_floor is True


@pytest.mark.django_db
class TestCatalogs:

    def _catalog(self, **kw):
        from apps.products.models.catalog import Catalog
        return Catalog.objects.create(name='Spring', code=kw.pop('code', 'SPR'),
                                      dt_effective_start=0, **kw)

    def test_catalog_line_for_the_assigned_customer(self):
        from apps.products.models.catalog import CatalogLine
        item, customer = _item(), _customer('wholesale')
        catalog = self._catalog(customer_orgbase_id=customer.pk, margin_floor=Decimal('5'))
        CatalogLine.objects.create(catalog=catalog, item=item, adjustment_type='percent_off',
                                   discount_percent=Decimal('10'))
        result = resolve_price(item, customer_id=customer.pk)
        assert (result.price, result.resolved_by, result.catalog_id) == (
            Decimal('67.50'), 'catalog_line', catalog.pk)       # 10% off the wholesale 75
        assert result.margin_floor == Decimal('5')

    def test_unassigned_catalog_applies_to_no_one(self):
        from apps.products.models.catalog import CatalogLine
        item = _item()
        CatalogLine.objects.create(catalog=self._catalog(), item=item,
                                   adjustment_type='fixed_price', price_unit=Decimal('1'))
        result = resolve_price(item, customer_id=_customer('retail').pk)
        assert result.resolved_by == 'price_level'

    def test_universal_pct_rides_on_the_level_price(self):
        item, customer = _item(), _customer('distributor')
        self._catalog(applies_to={'price_levels': ['distributor']},
                      is_universal_pct=True, universal_pct=Decimal('50'))
        result = resolve_price(item, customer_id=customer.pk)
        assert (result.price, result.discount_pct) == (Decimal('30.00'), Decimal('50'))


@pytest.mark.django_db
def test_price_lines_returns_both_figures():
    item = _item()
    out = price_lines([{'item_id': item.pk, 'qty': 2}], customer_id=_customer('wholesale').pk)
    assert out['level'] == 'wholesale'
    line = out['lines'][0]
    assert line['price']['price'] == 75.0 and line['price']['unit_cost'] == 45.0
    assert line['cost']['unit'] == 45.0 and line['cost']['list_price'] == 100.0
