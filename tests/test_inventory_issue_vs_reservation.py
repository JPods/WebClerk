from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryStack, PendingInventoryAdjustment
from apps.products.models.inventory_reservation import InventoryReservation
from apps.products.services.inventory_reservations import create_reservation, release_expired


class IssueVsReservationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email='ivr@example.com', password='pass', name_first='I', name_last='VR', username='ivr')
        self.item = Item.objects.create(name='IVRItem')
        self.wh = Warehouse.objects.create(name='IVRWH', code='IVR')
        self.stack = InventoryStack.objects.create(item=self.item, warehouse=self.wh, quantity={'received': 10})

    def test_issue_respects_reservations(self):
        # Create reservation for 6
        r = create_reservation(self.stack, Decimal('6'), ttl_seconds=300)
        # Attempt to issue 6 (would leave remaining 4 < reserved 6) -> enqueue reserved_conflict
        ok, obj = self.stack.issue_or_enqueue(Decimal('6'), reason='pick')
        self.assertFalse(ok)
        self.assertIsInstance(obj, PendingInventoryAdjustment)
        if isinstance(obj, PendingInventoryAdjustment):
            self.assertEqual(obj.reason, 'reserved_conflict')
        self.assertEqual(self.stack.remaining_qty(), Decimal('10'))  # unchanged
        # Issue 4 (leaves remaining 6 which == reserved) -> allowed
        ok2, obj2 = self.stack.issue_or_enqueue(Decimal('4'), reason='pick')
        self.assertTrue(ok2)
        self.stack.save(update_fields=['quantity'])
        self.assertEqual(self.stack.remaining_qty(), Decimal('6'))
        # Expire reservation then retry pending row
        r.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        r.save(update_fields=['expires_at'])
        release_expired()
        # Manually attempt to apply pending now that reservation gone
        pending = obj if isinstance(obj, PendingInventoryAdjustment) else None
        self.assertIsNotNone(pending)
        if pending is not None:
            self.assertTrue(pending.apply_now())
        self.stack.refresh_from_db()
        # After applying 6 issue, remaining becomes 0
        self.assertEqual(self.stack.remaining_qty(), Decimal('0'))

    def test_processor_skips_until_reservation_expires(self):
        from apps.products.services.inventory_adjustment_processor import process_pending_for_stack
        # Reserve 7 of 10
        r = create_reservation(self.stack, Decimal('7'), ttl_seconds=300)
        ok, pending = self.stack.issue_or_enqueue(Decimal('7'), reason='pick')
        self.assertFalse(ok)
        self.assertIsInstance(pending, PendingInventoryAdjustment)
        if not isinstance(pending, PendingInventoryAdjustment):  # safety for type checkers
            return
        self.assertEqual(pending.reason, 'reserved_conflict')
        # Run processor - should skip due to active reservation
        summary = process_pending_for_stack(self.stack.id)
        pending.refresh_from_db()
        self.assertEqual(pending.state, PendingInventoryAdjustment.STATE_PENDING)
        self.assertEqual(summary.get('applied'), 0)
        self.assertEqual(summary.get('reserved_conflict_skipped'), 1)
        # Expire reservation
        r.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        r.save(update_fields=['expires_at'])
        release_expired()
        # Run again - now should apply
        summary2 = process_pending_for_stack(self.stack.id)
        pending.refresh_from_db()
        self.assertEqual(pending.state, PendingInventoryAdjustment.STATE_APPLIED)
        self.assertEqual(summary2.get('applied'), 1)