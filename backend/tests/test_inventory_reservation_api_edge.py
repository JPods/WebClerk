from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer


class InventoryReservationAPIEdgeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='edge@example.com', password='pass', name_first='Edge', name_last='Case', username='edge'
        )
        self.item = Item.objects.create(name='EdgeItem')
        self.wh = Warehouse.objects.create(name='EdgeWH', code='EWH')
        self.stack = InventoryLayer.objects.create(
            item=self.item, warehouse=self.wh, quantity={'received': 3}
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_insufficient_reservation_rejected(self):
        # reserve all 3
        ok = self.client.post('/products/inventory/reservations/', {
            'stack_id': self.stack.id,
            'qty': '3'
        }, format='json')
        self.assertEqual(ok.status_code, 201)
        # attempt another should fail
        bad = self.client.post('/products/inventory/reservations/', {
            'stack_id': self.stack.id,
            'qty': '1'
        }, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertIn('insufficient', bad.json().get('message', ''))

    def test_release_restores_availability(self):
        r = self.client.post('/products/inventory/reservations/', {
            'stack_id': self.stack.id,
            'qty': '2'
        }, format='json')
        self.assertEqual(r.status_code, 201)
        rid = r.json()['data']['id']
        avail_after = self.client.get(f'/products/inventory/availability/{self.stack.id}/')
        self.assertEqual(int(avail_after.json()['data']['available_qty']), 1)
        rel = self.client.post('/products/inventory/reservations/action/', {
            'reservation_id': rid,
            'action': 'release',
            'reason': 'user_cancel'
        }, format='json')
        self.assertEqual(rel.status_code, 200)
        avail_final = self.client.get(f'/products/inventory/availability/{self.stack.id}/')
        self.assertEqual(int(avail_final.json()['data']['available_qty']), 3)