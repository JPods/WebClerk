"""
Test Purchase Order line creation with tracing.
PO should create pending records with 'on_po' bucket.
on_po should INCREASE (incoming inventory expected).
on_hand should NOT change (PO is commitment, not receipt).
"""
from django.db import transaction
from apps.transactions.models import PurchaseOrder, PurchaseOrderLine
from apps.products.models import Item
from apps.transactions.services.line_item_service import LineItemService
from apps.transactions.services.pending_inventory_processor import process_line_item_pending
from apps.transactions.services.trace_debug import enable_trace, disable_trace

# Test items
ITEM_IDS = [249, 250, 251]

print("\n" + "="*60)
print("PURCHASE ORDER TRACE TEST")
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

# 2. Clean up any existing test PO
print("\n[SETUP] Cleaning up existing test data...")
PurchaseOrder.objects.filter(id=40).delete()

# 3. Create test Purchase Order
print("\n[SETUP] Creating Purchase Order #40...")
po = PurchaseOrder.objects.create(
    id=40,
    vendor_id=1,  # Assuming vendor 1 exists
    status='open'
)
print(f"  Created PO #{po.id}")

# 4. Enable tracing for our items
print("\n[TRACE] Enabling trace for items:", ITEM_IDS)
enable_trace(ITEM_IDS)

# 5. Add lines using LineItemService
print("\n[TEST] Adding PO lines via LineItemService...")
service = LineItemService()

line1 = service.add_item_to_transaction(
    transaction=po,
    item_id=249,
    quantity=20,  # Ordering 20 units
    unit_cost=5.00
)
print(f"  Line 1 created: item=249, qty=20")

line2 = service.add_item_to_transaction(
    transaction=po,
    item_id=250,
    quantity=50,  # Ordering 50 units
    unit_cost=3.00
)
print(f"  Line 2 created: item=250, qty=50")

line3 = service.add_item_to_transaction(
    transaction=po,
    item_id=251,
    quantity=15,  # Ordering 15 units
    unit_cost=8.00
)
print(f"  Line 3 created: item=251, qty=15")

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
    249: {'on_po': 20, 'on_hand': 100},  # on_hand unchanged
    250: {'on_po': 50, 'on_hand': 100},
    251: {'on_po': 15, 'on_hand': 100},
}

for item_id, expect in expected.items():
    item = Item.objects.get(pk=item_id)
    qty = item.quantity
    
    on_po_ok = qty.get('on_po', 0) == expect['on_po']
    on_hand_ok = qty.get('on_hand', 0) == expect['on_hand']
    
    status = "✓" if (on_po_ok and on_hand_ok) else "✗"
    if not (on_po_ok and on_hand_ok):
        all_passed = False
    
    print(f"  Item #{item_id}: on_po={qty.get('on_po', 0)} {'✓' if on_po_ok else '✗'}, "
          f"on_hand={qty.get('on_hand', 0)} {'✓' if on_hand_ok else '✗'}")

print("-" * 50)
if all_passed:
    print("✓ ALL CHECKS PASSED")
else:
    print("✗ SOME CHECKS FAILED")
print("="*60 + "\n")
