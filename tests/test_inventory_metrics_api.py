from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer
from apps.products.services.inventory_reservations import create_reservation


class InventoryMetricsAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='metrics@example.com', password='pass', name_first='Met', name_last='Rics', username='metrics'
        )
        self.item = Item.objects.create(name='MetricsItem')
        self.wh = Warehouse.objects.create(name='MetricsWH', code='MET')
        self.stack = InventoryLayer.objects.create(item=self.item, warehouse=self.wh, quantity={'received': 40})
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_metrics_endpoint_enveloped_and_samples(self):
        create_reservation(self.stack, Decimal('5'), ttl_seconds=600)
        resp = self.client.get('/products/inventory/metrics/?samples=1')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('data', body)
        reservations = body['data']['reservations']
        self.assertGreaterEqual(reservations['active_reserved_qty'], 5.0)
        self.assertIn('avg_pending_ttl_s', reservations)
        self.assertIn('soonest_expiry_in_s', reservations)
        self.assertIn('samples', body['data'])

    def test_metrics_endpoint_raw(self):
        create_reservation(self.stack, Decimal('2'), ttl_seconds=300)
        resp = self.client.get('/products/inventory/metrics/?raw=1')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('data', body)  # transitional raw still wrapped
        reservations = body['data']['reservations']
        self.assertIn('avg_pending_ttl_s', reservations)
        self.assertIn('soonest_expiry_in_s', reservations)
