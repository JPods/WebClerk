"""Tests for price resolution service.

Validates the price level chain (line > header > customer > default),
quantity breaks, and fallback behavior.
"""
import pytest
from decimal import Decimal

from apps.products.services.pricing import (
    resolve_price_level,
    resolve_unit_price,
    get_price_for_line,
)


class TestResolvePriceLevel:
    """Price level chain: line > header > customer > default."""

    def test_line_overrides_all(self):
        assert resolve_price_level(
            customer_level='retail',
            header_level='wholesale',
            line_level='distributor',
        ) == 'distributor'

    def test_header_overrides_customer(self):
        assert resolve_price_level(
            customer_level='retail',
            header_level='wholesale',
            line_level=None,
        ) == 'wholesale'

    def test_customer_used_when_no_override(self):
        assert resolve_price_level(
            customer_level='wholesale',
            header_level=None,
            line_level=None,
        ) == 'wholesale'

    def test_default_when_nothing_set(self):
        assert resolve_price_level() == 'base'

    def test_invalid_level_falls_through(self):
        assert resolve_price_level(
            customer_level='bogus',
            header_level=None,
            line_level=None,
        ) == 'base'

    def test_empty_string_ignored(self):
        assert resolve_price_level(
            customer_level='',
            header_level='',
            line_level='retail',
        ) == 'retail'


class TestResolveUnitPrice:
    """Unit price resolution from Item.price JSON."""

    def test_exact_level_match(self):
        price = {'base': 100, 'retail': 90, 'wholesale': 75}
        assert resolve_unit_price(price, 'wholesale') == Decimal('75')

    def test_fallback_to_base(self):
        price = {'base': 100, 'retail': None, 'wholesale': None}
        assert resolve_unit_price(price, 'wholesale') == Decimal('100')

    def test_all_none_returns_zero(self):
        price = {'base': None, 'retail': None}
        assert resolve_unit_price(price, 'retail') == Decimal('0')

    def test_empty_dict_returns_zero(self):
        assert resolve_unit_price({}, 'retail') == Decimal('0')

    def test_quantity_break_applied(self):
        price = {
            'base': 100,
            'retail': 90,
            'qty_breaks': [
                {'min_qty': 10, 'unit_price': 85},
                {'min_qty': 50, 'unit_price': 75},
                {'min_qty': 100, 'unit_price': 65},
            ],
        }
        # qty=1 → no break → level price
        assert resolve_unit_price(price, 'retail', quantity=1) == Decimal('90')
        # qty=10 → first break
        assert resolve_unit_price(price, 'retail', quantity=10) == Decimal('85')
        # qty=75 → second break
        assert resolve_unit_price(price, 'retail', quantity=75) == Decimal('75')
        # qty=200 → third break
        assert resolve_unit_price(price, 'retail', quantity=200) == Decimal('65')

    def test_quantity_break_below_minimum_uses_level(self):
        price = {
            'base': 100,
            'qty_breaks': [{'min_qty': 50, 'unit_price': 80}],
        }
        assert resolve_unit_price(price, 'base', quantity=10) == Decimal('100')

    def test_string_prices_converted(self):
        price = {'base': '49.99', 'retail': '44.99'}
        assert resolve_unit_price(price, 'retail') == Decimal('44.99')


@pytest.mark.django_db
class TestGetPriceForLine:
    """Full integration: item + customer + overrides → resolved price."""

    def test_customer_level_applied(self):
        from tests.conftest import CustomerFactory, ItemFactory
        customer = CustomerFactory()
        customer.__class__.objects.filter(pk=customer.pk).update(price_level='wholesale')
        customer.refresh_from_db()

        item = ItemFactory()
        item.__class__.objects.filter(pk=item.pk).update(
            price={'base': 100, 'retail': 90, 'wholesale': 75, 'distributor': 60},
        )
        item.refresh_from_db()

        result = get_price_for_line(item, customer=customer, quantity=5)
        assert result['price_level'] == 'wholesale'
        assert result['unit_price'] == 75.0
        assert result['extended'] == 375.0

    def test_line_override_wins(self):
        from tests.conftest import CustomerFactory, ItemFactory
        customer = CustomerFactory()
        customer.__class__.objects.filter(pk=customer.pk).update(price_level='retail')
        customer.refresh_from_db()

        item = ItemFactory()
        item.__class__.objects.filter(pk=item.pk).update(
            price={'base': 100, 'retail': 90, 'wholesale': 75, 'sample': 50},
        )
        item.refresh_from_db()

        result = get_price_for_line(
            item, customer=customer,
            header_price_level='wholesale',
            line_price_level='sample',
            quantity=2,
        )
        assert result['price_level'] == 'sample'
        assert result['unit_price'] == 50.0
        assert result['extended'] == 100.0
        assert result['chain']['resolved'] == 'sample'
        assert result['chain']['customer'] == 'retail'

    def test_no_customer_uses_base(self):
        from tests.conftest import ItemFactory
        item = ItemFactory()
        item.__class__.objects.filter(pk=item.pk).update(
            price={'base': 42.0},
        )
        item.refresh_from_db()

        result = get_price_for_line(item, quantity=3)
        assert result['price_level'] == 'base'
        assert result['unit_price'] == 42.0
        assert result['extended'] == 126.0

    def test_chain_transparency(self):
        """Result includes the full resolution chain for debugging."""
        from tests.conftest import ItemFactory
        item = ItemFactory()
        item.__class__.objects.filter(pk=item.pk).update(price={'base': 10})
        item.refresh_from_db()

        result = get_price_for_line(
            item,
            header_price_level='retail',
            quantity=1,
        )
        chain = result['chain']
        assert chain['line'] is None
        assert chain['header'] == 'retail'
        assert chain['customer'] is None
        assert chain['resolved'] == 'retail'
