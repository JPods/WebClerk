from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer


class InventoryReservationAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='u1@example.com', password='pass', name_first='Test', name_last='User', username='u1'
        )
        self.item = Item.objects.create(name='APIItem')
        self.wh = Warehouse.objects.create(name='APIWH', code='APIWH')
        self.stack = InventoryLayer.objects.create(
            item=self.item, warehouse=self.wh, quantity={'received': 25}
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_availability_and_reservation_flow(self):
        resp = self.client.get(f'/products/inventory/availability/{self.stack.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(int(resp.json()['data']['available_qty']), 25)

        resp2 = self.client.post(
            '/products/inventory/reservations/',
            {
                'stack_id': self.stack.id,
                'qty': '5',
                'ttl_seconds': 600,
            },
            format='json',
        )
        self.assertEqual(resp2.status_code, 201)
        reservation_id = resp2.json()['data']['id']

        resp3 = self.client.get(f'/products/inventory/availability/{self.stack.id}/')
        self.assertEqual(int(resp3.json()['data']['available_qty']), 20)

        resp4 = self.client.post(
            '/products/inventory/reservations/action/',
            {
                'reservation_id': reservation_id,
                'action': 'commit',
            },
            format='json',
        )
        self.assertEqual(resp4.status_code, 200)

        resp5 = self.client.get(f'/products/inventory/availability/{self.stack.id}/')
        self.assertEqual(int(resp5.json()['data']['available_qty']), 20)
