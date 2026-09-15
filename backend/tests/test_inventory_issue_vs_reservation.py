from decimal import Decimal
from django.test import TestCase
from apps.core.models import Pending
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer


class IssueVsReservationTests(TestCase):
    """Tests for issue_or_enqueue producing Pending records."""

    def setUp(self):
        self.item = Item.objects.create(name='TestItem', quantity={
            'on_hand': 100, 'available': 100, 'on_so': 0, 'on_po': 0, 'on_p': 0,
        })
        self.wh = Warehouse.objects.create(name='Main', code='MAIN')
        self.stack = InventoryLayer.objects.create(
            item=self.item, warehouse=self.wh,
            quantity={'received': 100, 'issued': 0},
        )

    def test_issue_creates_pending(self):
        ok, obj = self.stack.issue_or_enqueue(Decimal('6'), reason='pick')
        self.assertIsInstance(obj, Pending)
        self.assertTrue(ok)
        self.assertTrue(obj.is_processed())

    def test_issue_updates_item_quantity(self):
        ok, obj = self.stack.issue_or_enqueue(Decimal('6'), reason='pick')
        self.assertTrue(ok)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity.get('on_hand'), 94)
