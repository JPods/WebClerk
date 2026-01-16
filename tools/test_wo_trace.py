"""
Test Work Order line creation with tracing.
WO should create pending records with 'on_wo' bucket.
on_wo should INCREASE (in production).
on_hand should NOT change until WO is completed.
"""
from django.db import transaction
from apps.transactions.models import WorkOrder, WorkOrderLine
from apps.products.models import Item
from apps.transactions.services.line_item_service import LineItemService
from apps.transactions.services.pending_inventory_processor import process_line_item_pending
from apps.transactions.services.trace_debug import enable_trace, disable_trace

# Test items
ITEM_IDS = [249, 250, 251]

print("\n" + "="*60)
print("WORK ORDER TRACE TEST")
print("="*60)

# 1. Reset items to clean state
print("\n[SETUP] Resetting items to clean state...")
for item_id in ITEM_IDS:
    Item.objects.filter(pk=item_id).update(
        quantity={
            'on_hand': 100,
            'on_so': 0,
            'on_po': 0,
            'on_wo': 0,
            'invoiced': 0,
            'committed': 0
        }
    )
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.sku or item.name[:20]}): on_hand=100, all buckets=0")

# 2. Clean up any existing test WO
print("\n[SETUP] Cleaning up existing test data...")
WorkOrder.objects.filter(id=50).delete()

# 3. Create test Work Order
print("\n[SETUP] Creating Work Order #50...")
wo = WorkOrder.objects.create(
    id=50,
    status='open'
)
print(f"  Created WO #{wo.id}")

# 4. Enable tracing for our items
print("\n[TRACE] Enabling trace for items:", ITEM_IDS)
enable_trace(ITEM_IDS)

# 5. Add lines using LineItemService
print("\n[TEST] Adding WO lines via LineItemService...")
service = LineItemService()

line1 = service.add_item_to_transaction(
    transaction=wo,
    item_id=249,
    quantity=8,  # Building 8 units
    unit_cost=12.00
)
print(f"  Line 1 created: item=249, qty=8")

line2 = service.add_item_to_transaction(
    transaction=wo,
    item_id=250,
    quantity=25,  # Building 25 units
    unit_cost=7.00
)
print(f"  Line 2 created: item=250, qty=25")

line3 = service.add_item_to_transaction(
    transaction=wo,
    item_id=251,
    quantity=12,  # Building 12 units
    unit_cost=15.00
)
print(f"  Line 3 created: item=251, qty=12")

# 6. Process pending records
print("\n[TEST] Processing pending records...")
with transaction.atomic():
    process_line_item_pending(249)
with transaction.atomic():
    process_line_item_pending(250)
with transaction.atomic():
    process_line_item_pending(251)

# 7. Disable tracing
disable_trace()

# 8. Verify results
print("\n[VERIFY] Checking item quantities...")
print("-" * 50)

all_passed = True
expected = {
    249: {'on_wo': 8, 'on_hand': 100},  # on_hand unchanged
    250: {'on_wo': 25, 'on_hand': 100},
    251: {'on_wo': 12, 'on_hand': 100},
}

for item_id, expect in expected.items():
    item = Item.objects.get(pk=item_id)
    qty = item.quantity
    
    on_wo_ok = qty.get('on_wo', 0) == expect['on_wo']
    on_hand_ok = qty.get('on_hand', 0) == expect['on_hand']
    
    status = "✓" if (on_wo_ok and on_hand_ok) else "✗"
    if not (on_wo_ok and on_hand_ok):
        all_passed = False
    
    print(f"  Item #{item_id}: on_wo={qty.get('on_wo', 0)} {'✓' if on_wo_ok else '✗'}, "
          f"on_hand={qty.get('on_hand', 0)} {'✓' if on_hand_ok else '✗'}")

print("-" * 50)
if all_passed:
    print("✓ ALL CHECKS PASSED")
else:
    print("✗ SOME CHECKS FAILED")
print("="*60 + "\n")
