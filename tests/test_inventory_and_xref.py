"""Tests for inventory availability and cross-reference lookup services."""
import pytest
from decimal import Decimal

from tests.conftest import ItemFactory, WarehouseFactory


@pytest.mark.django_db
class TestInventoryAvailability:
    """Inventory availability: on_hand - reserved = available."""

    def test_single_layer_availability(self):
        from apps.products.services.inventory_availability import get_item_availability
        from apps.products.models import InventoryLayer

        item = ItemFactory()
        wh = WarehouseFactory()
        InventoryLayer.objects.create(
            item=item,
            warehouse=wh,
            quantity={'on_hand': 100, 'on_so': 20, 'on_po': 50},
        )

        result = get_item_availability(item.pk)
        assert result['on_hand'] == 100.0
        assert result['on_so'] == 20.0
        assert result['on_po'] == 50.0
        assert result['available'] == 100.0  # no reservations

    def test_multiple_layers_aggregate(self):
        from apps.products.services.inventory_availability import get_item_availability
        from apps.products.models import InventoryLayer

        item = ItemFactory()
        wh = WarehouseFactory()
        InventoryLayer.objects.create(
            item=item, warehouse=wh,
            quantity={'on_hand': 50, 'on_so': 10},
        )
        InventoryLayer.objects.create(
            item=item, warehouse=wh,
            quantity={'on_hand': 30, 'on_so': 5},
        )

        result = get_item_availability(item.pk)
        assert result['on_hand'] == 80.0
        assert result['on_so'] == 15.0

    def test_filter_by_warehouse(self):
        from apps.products.services.inventory_availability import get_item_availability
        from apps.products.models import InventoryLayer

        item = ItemFactory()
        wh1 = WarehouseFactory(name="Warehouse A")
        wh2 = WarehouseFactory(name="Warehouse B")
        InventoryLayer.objects.create(
            item=item, warehouse=wh1,
            quantity={'on_hand': 100},
        )
        InventoryLayer.objects.create(
            item=item, warehouse=wh2,
            quantity={'on_hand': 200},
        )

        result_wh1 = get_item_availability(item.pk, warehouse_id=wh1.pk)
        assert result_wh1['on_hand'] == 100.0

        result_wh2 = get_item_availability(item.pk, warehouse_id=wh2.pk)
        assert result_wh2['on_hand'] == 200.0

    def test_no_layers_returns_zeros(self):
        from apps.products.services.inventory_availability import get_item_availability

        item = ItemFactory()
        result = get_item_availability(item.pk)
        assert result['on_hand'] == 0.0
        assert result['available'] == 0.0

    def test_availability_by_warehouse_breakdown(self):
        from apps.products.services.inventory_availability import get_item_availability_by_warehouse
        from apps.products.models import InventoryLayer

        item = ItemFactory()
        wh1 = WarehouseFactory(name="WH-1")
        wh2 = WarehouseFactory(name="WH-2")
        InventoryLayer.objects.create(item=item, warehouse=wh1, quantity={'on_hand': 40})
        InventoryLayer.objects.create(item=item, warehouse=wh2, quantity={'on_hand': 60})

        results = get_item_availability_by_warehouse(item.pk)
        assert len(results) == 2
        wh_ids = {r['warehouse_id'] for r in results}
        assert wh1.pk in wh_ids
        assert wh2.pk in wh_ids


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
