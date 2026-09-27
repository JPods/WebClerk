"""Tests for inventory availability and cross-reference lookup services."""
import pytest
from decimal import Decimal

from tests.conftest import ItemFactory, WarehouseFactory


@pytest.mark.django_db
class TestInventoryAvailability:
    """Availability reads the item's leaves: available = on_hand − allocated (Bill, 2026-09-26:
    "Needs to read the leaf, item.quantity.on_hand"). No reservation; no per-warehouse figures
    until the warehouse review (action 31277)."""

    def test_the_leaves_are_the_answer(self):
        from apps.products.services.inventory.inventory_available import get_item_availability
        item = ItemFactory(quantity={'on_hand': 100, 'on_so': 20, 'on_po': 50, 'allocated': 10,
                                     'available': 90})
        result = get_item_availability(item.pk)
        assert (result['on_hand'], result['on_so'], result['on_po']) == (100.0, 20.0, 50.0)
        assert (result['allocated'], result['available']) == (10.0, 90.0)

    def test_layers_do_not_answer_for_the_item(self):
        """A layer holds received/issued, not on_hand: the item's leaf is the book."""
        from apps.products.models import InventoryLayer
        from apps.products.services.inventory.inventory_available import get_item_availability
        item = ItemFactory(quantity={'on_hand': 7, 'allocated': 0})
        InventoryLayer.objects.create(item=item, warehouse=WarehouseFactory(), quantity={'received': 100})
        assert get_item_availability(item.pk)['on_hand'] == 7.0

    def test_an_item_with_no_quantity_is_all_zeros(self):
        from apps.products.services.inventory.inventory_available import get_item_availability
        item = ItemFactory(quantity={})
        result = get_item_availability(item.pk)
        assert result['on_hand'] == 0.0 and result['available'] == 0.0


@pytest.mark.django_db
class TestXRefLookup:
    """Cross-reference lookup by external SKU, GTIN, UPC, etc."""

    def _create_xref(self, item, external_sku, source='manufacturer', **kwargs):
        from apps.products.models import ItemXRef
        return ItemXRef.objects.create(
            item=item,
            external_sku=external_sku,
            source=source,
            source_name=kwargs.pop('source_name', ''),
            is_preferred=kwargs.pop('is_preferred', False),
            **kwargs,
        )

    def test_lookup_by_external_sku(self):
        from apps.products.services.xref_lookup import lookup_by_external_sku

        item = ItemFactory(ida='WIDGET-100')
        self._create_xref(item, 'MFR-12345', source='manufacturer', source_name='Acme')

        results = lookup_by_external_sku('MFR-12345')
        assert len(results) == 1
        assert results[0]['item_id'] == item.pk
        assert results[0]['external_sku'] == 'MFR-12345'
        assert results[0]['source'] == 'manufacturer'

    def test_lookup_by_sku_with_source_filter(self):
        from apps.products.services.xref_lookup import lookup_by_external_sku

        item = ItemFactory()
        self._create_xref(item, 'SKU-AAA', source='manufacturer')
        self._create_xref(item, 'SKU-AAA', source='wholesaler')

        mfr_results = lookup_by_external_sku('SKU-AAA', source='manufacturer')
        assert len(mfr_results) == 1
        assert mfr_results[0]['source'] == 'manufacturer'

    def test_lookup_by_code_gtin(self):
        from apps.products.services.xref_lookup import lookup_by_code

        item = ItemFactory()
        xref = self._create_xref(item, 'EXT-001')
        xref.set_codes(gtin='00012345678905')
        xref.save()

        results = lookup_by_code('00012345678905', code_type='gtin')
        assert len(results) == 1
        assert results[0]['item_id'] == item.pk
        assert results[0]['code_type'] == 'gtin'

    def test_lookup_by_code_any_type(self):
        from apps.products.services.xref_lookup import lookup_by_code

        item = ItemFactory()
        xref = self._create_xref(item, 'EXT-002')
        xref.set_codes(upc='123456789012')
        xref.save()

        results = lookup_by_code('123456789012')
        assert len(results) == 1
        assert results[0]['code_type'] == 'upc'

    def test_find_item_by_ida(self):
        from apps.products.services.xref_lookup import find_item_by_any_identifier

        item = ItemFactory(ida='BOLT-M10')
        result = find_item_by_any_identifier('BOLT-M10')
        assert result is not None
        assert result['item_id'] == item.pk
        assert result['matched_via'] == 'ida'

    def test_find_item_by_external_sku(self):
        from apps.products.services.xref_lookup import find_item_by_any_identifier

        item = ItemFactory(ida='BOLT-M10')
        self._create_xref(item, 'VENDOR-999', source='wholesaler', is_preferred=True)

        result = find_item_by_any_identifier('VENDOR-999')
        assert result is not None
        assert result['item_id'] == item.pk
        assert result['matched_via'] == 'xref:wholesaler'

    def test_find_item_prefers_preferred_xref(self):
        from apps.products.services.xref_lookup import find_item_by_any_identifier

        item = ItemFactory()
        self._create_xref(item, 'SHARED-SKU', source='wholesaler', is_preferred=False)
        self._create_xref(item, 'SHARED-SKU', source='manufacturer', is_preferred=True)

        result = find_item_by_any_identifier('SHARED-SKU')
        assert result is not None
        assert result['is_preferred'] is True

    def test_find_item_not_found(self):
        from apps.products.services.xref_lookup import find_item_by_any_identifier

        result = find_item_by_any_identifier('NONEXISTENT-XYZ')
        assert result is None
