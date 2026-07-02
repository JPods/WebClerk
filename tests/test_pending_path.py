"""
Test the ONE PATH — all inventory changes through pending records.
Verifies: adjust_item_quantity creates pending, applies if unlocked, queues if locked.
"""
from apps.products.services.inventory_pending import adjust_item_quantity, apply_pending_for_item, get_pending_for_item
from apps.products.models.item import Item
from apps.products.models.inventory_layer import PendingInventoryAdjustment

# Reset item 308
item = Item.objects.get(pk=308)
item.quantity = {'on_hand': 100, 'allocated': 0, 'available': 100, 'on_so': 0, 'on_po': 0, 'on_p': 0, 'on_in': 0, 'on_wo': 0}
item.is_locked = False
item.save(update_fields=['quantity', 'is_locked'])

# Clean old pending records for item 308
PendingInventoryAdjustment.objects.filter(request_ref__item_id=308).delete()

print('=== ONE PATH TEST ===')
print(f'Start: on_hand=100, on_p=0, on_so=0, on_po=0')
print()

# Phase 1: Proposal +15 on_p (item unlocked — should apply immediately)
r = adjust_item_quantity(308, 'on_p', 15, reason='proposal_add', source_type='proposal', source_id=99)
print(f'Proposal +15 on_p: pending_id={r["pending_id"]}, state={r["state"]}, applied={r["applied"]}')

# Phase 2: Order +9 on_so, -9 on_p
r1 = adjust_item_quantity(308, 'on_so', 9, reason='order_add', source_type='order', source_id=99)
r2 = adjust_item_quantity(308, 'on_p', -9, reason='order_transfer', source_type='order', source_id=99)
print(f'Order +9 on_so: state={r1["state"]}, applied={r1["applied"]}')
print(f'Order -9 on_p: state={r2["state"]}, applied={r2["applied"]}')

# Phase 3: PO +6 on_po
r = adjust_item_quantity(308, 'on_po', 6, reason='po_add', source_type='purchase', source_id=99)
print(f'PO +6 on_po: state={r["state"]}, applied={r["applied"]}')

# Check state
item.refresh_from_db()
q = item.quantity
print(f'\nAfter unlocked operations: on_hand={q["on_hand"]}, on_p={q["on_p"]}, on_so={q["on_so"]}, on_po={q["on_po"]}')

# Phase 4: LOCK the item
item.is_locked = True
item.save(update_fields=['is_locked'])
print(f'\n--- ITEM LOCKED ---')

# Phase 5: Invoice -6 on_hand, -6 on_so (while locked — should queue)
r1 = adjust_item_quantity(308, 'on_hand', -6, reason='invoice_ship', source_type='invoice', source_id=99)
r2 = adjust_item_quantity(308, 'on_so', -6, reason='invoice_ship', source_type='invoice', source_id=99)
print(f'Invoice -6 on_hand (locked): state={r1["state"]}, applied={r1["applied"]}')
print(f'Invoice -6 on_so (locked): state={r2["state"]}, applied={r2["applied"]}')

# Phase 6: PO receive +4 on_hand, -4 on_po (while locked — should queue)
r1 = adjust_item_quantity(308, 'on_hand', 4, reason='po_receive', source_type='purchase', source_id=99)
r2 = adjust_item_quantity(308, 'on_po', -4, reason='po_receive', source_type='purchase', source_id=99)
print(f'Receive +4 on_hand (locked): state={r1["state"]}, applied={r1["applied"]}')
print(f'Receive -4 on_po (locked): state={r2["state"]}, applied={r2["applied"]}')

# Check — item should NOT have changed while locked
item.refresh_from_db()
q = item.quantity
print(f'\nWhile locked: on_hand={q["on_hand"]}, on_so={q["on_so"]}, on_po={q["on_po"]} (should be unchanged: 100, 9, 6)')

# Show pending records
pendings = get_pending_for_item(308)
pending_count = len([p for p in pendings if p['state'] == 'pending'])
applied_count = len([p for p in pendings if p['state'] == 'applied'])
print(f'\nPending records: {len(pendings)} total, {applied_count} applied, {pending_count} still pending')

# Phase 7: UNLOCK — apply pending
item.is_locked = False
item.save(update_fields=['is_locked'])
print(f'\n--- ITEM UNLOCKED ---')

result = apply_pending_for_item(308)
print(f'Applied: {result["applied_count"]}, still pending: {result["still_pending"]}')

# Final check
item.refresh_from_db()
q = item.quantity
print(f'\nFINAL: on_hand={q["on_hand"]}, on_p={q["on_p"]}, on_so={q["on_so"]}, on_po={q["on_po"]}, available={q["available"]}')
print(f'EXPECTED: on_hand=98, on_p=6, on_so=3, on_po=2, available=98')

ok = q['on_hand'] == 98 and q['on_p'] == 6 and q['on_so'] == 3 and q['on_po'] == 2
print(f'\n{"ALL PASS ✓" if ok else "FAILURES ✗"}')

# Show full audit trail
print(f'\n=== AUDIT TRAIL ({len(pendings)} records) ===')
for p in get_pending_for_item(308):
    print(f'  #{p["pending_id"]} {p["field"]:8s} {p["delta"]:+.0f}  {p["reason"]:20s} {p["state"]:8s}  {p["source_type"]}')
