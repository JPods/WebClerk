"""
Test script: Create an Invoice with traced items.
Invoices SHOULD create pending records and update:
- invoiced: increases (qty shipped)
- on_hand: decreases (inventory issued)

Run with: python manage.py shell --command="exec(open('tools/test_invoice_trace.py').read())"
"""

from apps.transactions.services.trace_debug import enable_trace, disable_trace
from apps.transactions.services import LineItemService
from apps.transactions.models import Invoice
from apps.products.models import Item
from apps.core.models import Pending
from django.db import transaction, connection

# Clean up from previous tests
print("\n--- CLEANUP ---")
Pending.objects.filter(model_name='item', record_id__in=['249','250','251']).delete()
with connection.cursor() as cursor:
    for item_id in [249, 250, 251]:
        cursor.execute('''
            UPDATE products_item 
            SET quantity = %s::jsonb
            WHERE id = %s
        ''', ['{"on_hand": 100, "available": 100, "allocated": 0, "sell_default": 1, "purchase_default": 1, "on_po": 0, "on_wo": 0, "on_so": 0, "invoiced": 0}', item_id])
print("Cleaned up pending records and reset items")

# Enable tracing for our test items
print("\n" + "="*70)
print("  INVOICE TEST - Items 249, 250, 251")
print("="*70)

log_path = enable_trace([249, 250, 251])

# Check current item status before
print("\n--- BEFORE: Item Status ---")
for item_id in [249, 250, 251]:
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.ida}): {item.quantity_display}")

# Create a new invoice
invoice = Invoice.objects.create(
    ida="TEST-INV-001",
)
print(f"\n--- Created Invoice #{invoice.pk} ({invoice.ida}) ---")

# Add items using LineItemService
service = LineItemService()

print("\n--- Adding Items to Invoice ---")
line1 = service.add_item_to_transaction(invoice, item_id=249, quantity=5)
print(f"  Added line {line1.pk}: Item 249, qty=5")

line2 = service.add_item_to_transaction(invoice, item_id=250, quantity=10)
print(f"  Added line {line2.pk}: Item 250, qty=10")

line3 = service.add_item_to_transaction(invoice, item_id=251, quantity=3)
print(f"  Added line {line3.pk}: Item 251, qty=3")

# Check for pending records BEFORE processing
pending_qs = Pending.objects.filter(
    model_name="item",
    record_id__in=["249", "250", "251"],
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
from apps.transactions.services.inventory_pending_process import process_line_item_pending

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
# Invoice: invoiced increases, on_hand decreases
print("\n--- VERIFICATION ---")
expected = {
    249: {'invoiced': 5, 'on_hand': 95},
    250: {'invoiced': 10, 'on_hand': 90},
    251: {'invoiced': 3, 'on_hand': 97},
}
all_ok = True
for item_id, exp in expected.items():
    item = Item.objects.get(pk=item_id)
    q = item.quantity
    inv_ok = q.get('invoiced', 0) == exp['invoiced']
    oh_ok = q.get('on_hand', 0) == exp['on_hand']
    inv_status = "✓" if inv_ok else "✗"
    oh_status = "✓" if oh_ok else "✗"
    print(f"  Item #{item_id}: invoiced={q.get('invoiced',0)} (exp {exp['invoiced']}) {inv_status}, on_hand={q.get('on_hand',0)} (exp {exp['on_hand']}) {oh_status}")
    if not (inv_ok and oh_ok):
        all_ok = False

if all_ok:
    print("\n  ✓ ALL CHECKS PASSED")
else:
    print("\n  ✗ SOME CHECKS FAILED")

disable_trace()
print(f"\nLog saved to: {log_path}")
print("="*70 + "\n")
