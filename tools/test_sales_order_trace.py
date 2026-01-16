"""
Test script: Create a Sales Order with traced items.
Sales Orders SHOULD create pending records and update on_so.

Run with: python manage.py shell --command="exec(open('tools/test_sales_order_trace.py').read())"
"""

from apps.transactions.services.trace_debug import enable_trace, disable_trace
from apps.transactions.services import LineItemService
from apps.transactions.models import SalesOrder
from apps.products.models import Item
from apps.core.models import Pending

# Enable tracing for our test items
print("\n" + "="*70)
print("  SALES ORDER TEST - Items 249, 250, 251")
print("="*70)

log_path = enable_trace([249, 250, 251])

# Check current item status before
print("\n--- BEFORE: Item Status ---")
for item_id in [249, 250, 251]:
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.ida}): {item.quantity_display}")

# Create a new sales order
sales_order = SalesOrder.objects.create(
    ida="TEST-SO-001",
)
print(f"\n--- Created Sales Order #{sales_order.pk} ({sales_order.ida}) ---")

# Add items using LineItemService
service = LineItemService()

print("\n--- Adding Items to Sales Order ---")
line1 = service.add_item_to_transaction(sales_order, item_id=249, quantity=5)
print(f"  Added line {line1.pk}: Item 249, qty=5")

line2 = service.add_item_to_transaction(sales_order, item_id=250, quantity=10)
print(f"  Added line {line2.pk}: Item 250, qty=10")

line3 = service.add_item_to_transaction(sales_order, item_id=251, quantity=3)
print(f"  Added line {line3.pk}: Item 251, qty=3")

# Check for pending records BEFORE processing
pending_qs = Pending.objects.filter(
    model_name="item",
    id_record__in=["249", "250", "251"],
    dt_processed=0
)
print(f"\n--- Unprocessed Pending Records: {pending_qs.count()} ---")
for p in pending_qs:
    data = p.data or {}
    buckets = {k: data.get(k, 0) for k in ['on_so', 'on_po', 'on_wo', 'invoiced'] if data.get(k, 0) != 0}
    print(f"  Pending #{p.pk}: item={data.get('item_id')} {buckets}")

# Item status BEFORE processing (should still be unchanged)
print("\n--- AFTER ADDING (before processing): Item Status ---")
for item_id in [249, 250, 251]:
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.ida}): {item.quantity_display}")

# Now process the pending records
print("\n--- PROCESSING PENDING RECORDS ---")
from apps.transactions.services.pending_inventory_processor import process_line_item_pending
from django.db import transaction

# Need to wrap in transaction for select_for_update to work
with transaction.atomic():
    summary = process_line_item_pending(item_id=249)
with transaction.atomic():
    summary = process_line_item_pending(item_id=250)
with transaction.atomic():
    summary = process_line_item_pending(item_id=251)

# Check item status AFTER processing
print("\n--- AFTER PROCESSING: Item Status ---")
for item_id in [249, 250, 251]:
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.ida}): {item.quantity_display}")

# Verify expected values
print("\n--- VERIFICATION ---")
expected = {249: 5, 250: 10, 251: 3}
all_ok = True
for item_id, expected_on_so in expected.items():
    item = Item.objects.get(pk=item_id)
    actual = item.quantity.get('on_so', 0)
    status = "✓" if actual == expected_on_so else "✗"
    print(f"  Item #{item_id}: on_so={actual} (expected {expected_on_so}) {status}")
    if actual != expected_on_so:
        all_ok = False

if all_ok:
    print("\n  ✓ ALL CHECKS PASSED")
else:
    print("\n  ✗ SOME CHECKS FAILED")

disable_trace()
print(f"\nLog saved to: {log_path}")
print("="*70 + "\n")
