import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer


class APISchemaAndInventoryCommitFailureTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='schema@example.com', password='pass', name_first='Schema', name_last='User', username='schema'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_schema_endpoints(self):
        r_schema = self.client.get('/wcapi/schema/')
        self.assertEqual(r_schema.status_code, 200)
        text = r_schema.content.decode('utf-8')
        self.assertIn('openapi', text)
        # Swagger / Redoc HTML pages
        r_swagger = self.client.get('/wcapi/swagger/')
        self.assertEqual(r_swagger.status_code, 200)
        r_redoc = self.client.get('/wcapi/redoc/')
        self.assertEqual(r_redoc.status_code, 200)

    @pytest.mark.skip(reason="Inventory reservation endpoints not yet implemented")
    def test_reservation_commit_after_external_issue(self):
        item = Item.objects.create(name='CommitFailItem')
        wh = Warehouse.objects.create(name='CFWH', code='CFWH')
        stack = InventoryLayer.objects.create(item=item, warehouse=wh, quantity={'received': 5})
        # create reservation for 5
        res = self.client.post('/products/inventory/reservations/', {
            'stack_id': stack.id,
            'qty': '5'
        }, format='json')
        self.assertEqual(res.status_code, 201)
        rid = res.json()['data']['id']
        # Simulate external issue reducing remaining to 0
        stack.mark_issue(5)
        stack.save(update_fields=['quantity', 'dt_modified', 'version'])
        # Attempt commit -> current behavior commits even if no quantity is issued (idempotent commit)
        commit_resp = self.client.post(
            '/products/inventory/reservations/action/',
            {
                'reservation_id': rid,
                'action': 'commit'
            },
            format='json'
        )
        self.assertEqual(commit_resp.status_code, 200)
        body = commit_resp.json()
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['data']['state'], 'committed')
        # Remaining qty unchanged (already issued externally)
        stack.refresh_from_db()
        self.assertEqual(float(stack.remaining_qty()), 0.0)