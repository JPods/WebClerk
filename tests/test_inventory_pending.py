from decimal import Decimal
from django.test import TestCase
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.models.inventory_layer import InventoryStack, PendingInventoryAdjustment
from apps.products.services.inventory_adjustment_processor import (
    process_pending_inventory,
    process_pending_for_stack,
)


class PendingInventoryTests(TestCase):
    """Tests for pending inventory adjustment processing."""

    def setUp(self):
        self.item = Item.objects.create(name='TestItem')
        self.wh = Warehouse.objects.create(name='Main', code='MAIN')

    def _make_stack(self, received=100, locked=False):
        return InventoryStack.objects.create(
            item=self.item,
            warehouse=self.wh,
            quantity={'received': received},
            is_locked=locked,
        )

    def test_issue_or_enqueue_locked_then_process(self):
        stack = self._make_stack(locked=True)
        ok, pending = stack.issue_or_enqueue(Decimal('5'), reason='pick')
        self.assertFalse(ok)
        self.assertIsInstance(pending, PendingInventoryAdjustment)
        self.assertEqual(pending.state, PendingInventoryAdjustment.STATE_PENDING)
        stack.is_locked = False
        stack.save(update_fields=['is_locked'])
        process_pending_for_stack(stack.id)
        stack.refresh_from_db()
        self.assertEqual(stack.remaining_qty(), 95)
        self.assertEqual(
            PendingInventoryAdjustment.objects.get(pk=pending.pk).state,
            PendingInventoryAdjustment.STATE_APPLIED,
        )

    def test_global_processor_applies_multiple(self):
        stack = self._make_stack(locked=True)
        for _ in range(3):
            stack.issue_or_enqueue(5)
        self.assertEqual(
            PendingInventoryAdjustment.objects.filter(stack=stack, state='pending').count(),
            3,
        )
        stack.is_locked = False
        stack.save(update_fields=['is_locked'])
        summary = process_pending_inventory(limit=10)
        self.assertEqual(summary['applied'], 3)
        stack.refresh_from_db()
        self.assertEqual(stack.remaining_qty(), 85)

    def test_process_single_stack_insufficient_and_force(self):
        stack = self._make_stack(locked=True)
        stack.issue_or_enqueue(10)
        stack.is_locked = False
        stack.save(update_fields=['is_locked'])
        process_pending_for_stack(stack.id)
        ok, pending_row = stack.issue_or_enqueue(200)  # insufficient
        self.assertFalse(ok)
        self.assertEqual(pending_row.state, 'pending')
        result = process_pending_for_stack(stack.id)
        self.assertEqual(result['applied'], 0)
        self.assertEqual(
            PendingInventoryAdjustment.objects.get(pk=pending_row.pk).state,
            'pending',
        )
        forced = process_pending_for_stack(stack.id, apply_insufficient=True)
        self.assertEqual(forced['applied'], 1)
        self.assertEqual(
            PendingInventoryAdjustment.objects.get(pk=pending_row.pk).state,
            'applied',
        )

