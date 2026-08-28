from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.inventory_reservation import InventoryReservation
from apps.products.services.inventory.inventory_reserve import (
    create_reservation,
    availability_for_layer,
    release_expired,
)


class InventoryReservationTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name='ResvItem')
        self.wh = Warehouse.objects.create(name='RSV', code='RSV')
        self.stack = InventoryLayer.objects.create(item=self.item, warehouse=self.wh, quantity={'received': 40})

    def test_create_and_commit(self):
        r = create_reservation(self.stack, 5)
        self.assertEqual(availability_for_layer(self.stack), Decimal('35'))
        committed = r.commit()
        self.assertTrue(committed)
        self.stack.refresh_from_db()
        self.assertEqual(self.stack.remaining_qty(), 35)
        # availability after commit (no longer reserved; issued instead)
        self.assertEqual(availability_for_layer(self.stack), Decimal('35'))

    def test_release(self):
        r = create_reservation(self.stack, 4)
        self.assertEqual(availability_for_layer(self.stack), Decimal('36'))
        r.release('user_cancel')
        self.assertEqual(availability_for_layer(self.stack), Decimal('40'))
        self.assertEqual(r.state, InventoryReservation.STATE_CANCELED)

    def test_expire(self):
        r = create_reservation(self.stack, 6, ttl_seconds=1)
        self.assertEqual(availability_for_layer(self.stack), Decimal('34'))
        # simulate time lapse
        r.expires_at = timezone.now() - timedelta(seconds=5)
        r.save(update_fields=['expires_at'])
        release_expired()
        r.refresh_from_db()
        self.assertEqual(r.state, InventoryReservation.STATE_EXPIRED)
        self.assertEqual(availability_for_layer(self.stack), Decimal('40'))

    def test_insufficient(self):
        create_reservation(self.stack, 30)
        self.assertRaises(ValueError, create_reservation, self.stack, 15)
