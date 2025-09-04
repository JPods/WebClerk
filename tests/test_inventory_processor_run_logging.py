import pytest
from decimal import Decimal
from apps.products.models import InventoryStack, InventoryAdjustmentProcessorRun
from apps.products.models.inventory_layer import PendingInventoryAdjustment
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
from apps.products.services.inventory_adjustment_processor import process_pending_inventory, process_pending_for_stack

pytestmark = pytest.mark.django_db

def make_stack(qty=10):
    item = Item.objects.create(name="Test Item", sku=None)
    wh = Warehouse.objects.create(name="Main WH", code=f"WH{item.id}")
    stack = InventoryStack.objects.create(item=item, warehouse=wh, quantity={"received": float(qty), "issued": 0})
    return stack


def test_global_processor_creates_run():
    stack = make_stack(qty=5)
    stack.is_locked = True
    stack.save(update_fields=["is_locked"])
    success, pending = stack.issue_or_enqueue(2, reason="issue")
    assert success is False
    assert isinstance(pending, PendingInventoryAdjustment)
    stack.is_locked = False
    stack.save(update_fields=["is_locked"])
    summary = process_pending_inventory(dry_run=False)
    assert summary["attempted"] >= 1
    run = InventoryAdjustmentProcessorRun.objects.order_by('-id').first()
    assert run is not None
    assert run.run_type == InventoryAdjustmentProcessorRun.RUN_GLOBAL
    assert run.attempted == summary["attempted"]
    assert run.applied == summary["applied"]
    assert isinstance(run.duration_s, (float, int, Decimal))
    assert run.summary.get("attempted") == summary["attempted"]


def test_stack_processor_creates_run():
    stack = make_stack(qty=8)
    success, pending = stack.issue_or_enqueue(20, reason="issue")
    assert success is False
    assert isinstance(pending, PendingInventoryAdjustment)
    assert pending.reason == "insufficient_issue"
    pending.qty = Decimal('3')
    pending.reason = "issue"
    pending.save(update_fields=["qty", "reason"])
    summary = process_pending_for_stack(stack.id, dry_run=False)
    run = InventoryAdjustmentProcessorRun.objects.filter(stack_id=stack.id).order_by('-id').first()
    assert run is not None
    assert run.run_type == InventoryAdjustmentProcessorRun.RUN_STACK
    assert run.stack_id == stack.id
    assert run.applied == summary["applied"]
    assert run.summary.get("stack_id") == stack.id
