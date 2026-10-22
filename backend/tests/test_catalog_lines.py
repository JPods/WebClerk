"""Catalog lines through the door (Bill, 2026-10-22).

A catalog line is its own record: `new` under its catalog, then a save naming an item or a
non-empty scope (all_items, categories, vendors) — a line naming neither is refused — and a
delete. A scope line prices through resolve_price like an item line.
"""
from decimal import Decimal

import pytest

from apps.core.models.contact import Contact
from apps.core.services import verbs
from apps.core.services.door import Actor, Refused
from apps.products.models.catalog import Catalog, CatalogLine
from apps.products.services.price_resolver import resolve_price

pytestmark = pytest.mark.django_db


def _item(**catalog):
    from tests.conftest import ItemFactory
    item = ItemFactory()
    item.price = {'base': 100, 'retail': 100, 'wholesale': 75}
    item.cost = {'standard': 40, 'last': 45}
    item.catalog = catalog or item.catalog
    item.save()
    return item


def _customer(level='wholesale'):
    from tests.conftest import CustomerFactory
    customer = CustomerFactory()
    customer.__class__.objects.filter(pk=customer.pk).update(price_level=level)
    return customer


def _catalog(customer):
    return Catalog.objects.create(name='Spring', code='SPR', dt_effective_start=0,
                                  customer_orgbase_id=customer.pk)


@pytest.fixture
def admin():
    return Actor(user=Contact.objects.create(email='catalog-admin@example.com', role='admin'))


def _add(actor, catalog, **values):
    """What the panel does: `new` with the catalog, then the values as its save."""
    made = verbs.run(actor, 'new', 'catalog_line', {'catalog_id': catalog.pk})
    return verbs.run(actor, 'save', 'catalog_line',
                     {'id': made.obj_id, 'version': made.version, **values})


class TestScopeLinesPrice:

    def test_an_all_items_line_prices_every_item(self, admin):
        customer = _customer()
        line = _add(admin, _catalog(customer), scope={'all_items': True},
                    adjustment_type='percent_off', adjustment_value=20).obj
        assert line.item_id is None
        result = resolve_price(_item(), customer_id=customer.pk)
        assert (result.price, result.resolved_by, result.catalog_line_id) == (
            Decimal('60.00'), 'catalog_line', line.pk)         # 20% off the wholesale 75

    def test_a_category_line_prices_only_its_category(self, admin):
        customer = _customer()
        _add(admin, _catalog(customer), scope={'categories': ['tools']},
             adjustment_type='fixed_price', price_unit=50)
        assert resolve_price(_item(categories=['tools']), customer_id=customer.pk).price == Decimal('50')
        assert resolve_price(_item(categories=['paint']), customer_id=customer.pk).resolved_by == 'price_level'

    def test_an_item_line_wins_over_a_scope_line(self, admin):
        customer, item = _customer(), _item()
        catalog = _catalog(customer)
        _add(admin, catalog, scope={'all_items': True}, adjustment_type='percent_off', adjustment_value=20)
        item_line = _add(admin, catalog, item_id=item.pk, adjustment_type='fixed_price', price_unit=70).obj
        result = resolve_price(item, customer_id=customer.pk)
        assert (result.price, result.catalog_line_id) == (Decimal('70'), item_line.pk)


class TestALineNamesSomething:

    def test_a_line_with_neither_item_nor_scope_is_refused(self, admin):
        with pytest.raises(Refused) as refused:
            _add(admin, _catalog(_customer()), adjustment_value=10)
        assert refused.value.status == 400 and refused.value.code == 'catalog_line_covers_nothing'

    def test_an_empty_scope_is_neither(self, admin):
        with pytest.raises(Refused) as refused:
            _add(admin, _catalog(_customer()),
                 scope={'all_items': False, 'categories': [], 'vendors': []})
        assert refused.value.code == 'catalog_line_covers_nothing'

    def test_new_takes_only_the_catalog(self, admin):
        with pytest.raises(Refused) as refused:
            verbs.run(admin, 'new', 'catalog_line', {})
        assert refused.value.code == 'new_requires'


class TestTheDoor:

    def test_save_then_delete(self, admin):
        item = _item()
        line = _add(admin, _catalog(_customer()), item_id=item.pk,
                    adjustment_type='percent_off', adjustment_value=5).obj
        assert line.item_ida == item.ida and 'is_new' not in (line.config or {})

        saved = verbs.run(admin, 'save', 'catalog_line',
                          {'id': line.pk, 'version': line.version, 'min_qty': 10})
        assert saved.obj.min_qty == Decimal('10')

        verbs.run(admin, 'delete', 'catalog_line', {'id': line.pk})
        assert not CatalogLine.objects.filter(pk=line.pk).exists()

    def test_a_portal_customer_has_no_catalog_lines(self):
        line = CatalogLine.objects.create(catalog=_catalog(_customer()), item=_item())
        buyer = Actor(user=Contact.objects.create(email='buyer@example.com', role='customer'))
        with pytest.raises(Refused):
            verbs.run(buyer, 'save', 'catalog_line', {'id': line.pk, 'min_qty': 1})
        with pytest.raises(Refused):
            verbs.run(buyer, 'delete', 'catalog_line', {'id': line.pk})
        assert CatalogLine.objects.filter(pk=line.pk, min_qty__isnull=True).exists()
