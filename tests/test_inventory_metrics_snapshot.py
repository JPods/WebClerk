from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryStack
from apps.products.models.metrics import InventoryMetricsSnapshot
from apps.products.services.inventory_reservations import create_reservation


class InventoryMetricsSnapshotTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email='snap@example.com', password='pass', name_first='Snap', name_last='Shot', username='snap')
        self.item = Item.objects.create(name='SnapItem')
        self.wh = Warehouse.objects.create(name='SnapWH', code='SNAP')
        self.stack = InventoryStack.objects.create(item=self.item, warehouse=self.wh, quantity={'received': 15})

    def test_snapshot_creation(self):
        create_reservation(self.stack, Decimal('3'), ttl_seconds=300)
        call_command('snapshot_inventory_metrics', '--samples')
        self.assertGreaterEqual(InventoryMetricsSnapshot.objects.count(), 1)
        snap = InventoryMetricsSnapshot.objects.latest('dt_created')
        self.assertIn('reservations', snap.metrics)
        self.assertIn('active_reserved_qty', snap.metrics['reservations'])