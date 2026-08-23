"""
Test the ONE PATH — all inventory changes through Pending records.
Verifies: Pending.save() calls try_apply(), applies if unlocked, queues if locked.
"""
from apps.core.models import Pending
from apps.products.models.item import Item

# Reset item 308
item = Item.objects.get(pk=308)
item.quantity = {'on_hand': 100, 'allocated': 0, 'available': 100, 'on_so': 0, 'on_po': 0, 'on_p': 0, 'on_in': 0, 'on_wo': 0}
item.is_locked = False
item.save(update_fields=['quantity', 'is_locked'])

# Clean old pending records for item 308
Pending.objects.filter(model_name='item', record_id='308').delete()

print('=== ONE PATH TEST (Pending.try_apply) ===')
print(f'Start: on_hand=100, on_p=0, on_so=0, on_po=0')
print()

# Phase 1: Proposal +15 on_p (item unlocked — should apply immediately)
p = Pending.objects.create(model_name='item', record_id='308', purpose='inventory_line_add',
    name='Proposal +15', changes={'on_p': 15, 'item_id': 308, 'reason': 'proposal_add'})
print(f'Proposal +15 on_p: pending_id={p.pk}, applied={p.is_processed()}')

# Phase 2: Order +9 on_so, -9 on_p (single pending with both deltas)
p = Pending.objects.create(model_name='item', record_id='308', purpose='inventory_line_add',
    name='Order +9', changes={'on_so': 9, 'on_p': -9, 'item_id': 308, 'reason': 'order_add'})
print(f'Order +9 on_so, -9 on_p: applied={p.is_processed()}')

# Phase 3: PO +6 on_po
p = Pending.objects.create(model_name='item', record_id='308', purpose='inventory_line_add',
    name='PO +6', changes={'on_po': 6, 'item_id': 308, 'reason': 'po_add'})
print(f'PO +6 on_po: applied={p.is_processed()}')

# Check state
item.refresh_from_db()
q = item.quantity
print(f'\nAfter unlocked operations: on_hand={q["on_hand"]}, on_p={q["on_p"]}, on_so={q["on_so"]}, on_po={q["on_po"]}')

# Phase 4: LOCK the item
item.is_locked = True
item.save(update_fields=['is_locked'])
print(f'\n--- ITEM LOCKED ---')

# Phase 5: Invoice -6 on_hand, -6 on_so (while locked — should queue)
p1 = Pending.objects.create(model_name='item', record_id='308', purpose='inventory_line_add',
    name='Invoice ship', changes={'on_hand': -6, 'on_so': -6, 'item_id': 308, 'reason': 'invoice_ship'})
print(f'Invoice -6 on_hand, -6 on_so (locked): applied={p1.is_processed()}')

# Phase 6: PO receive +4 on_hand, -4 on_po (while locked — should queue)
p2 = Pending.objects.create(model_name='item', record_id='308', purpose='inventory_line_add',
    name='PO receive', changes={'on_hand': 4, 'on_po': -4, 'item_id': 308, 'reason': 'po_receive'})
print(f'Receive +4 on_hand, -4 on_po (locked): applied={p2.is_processed()}')

# Check — item should NOT have changed while locked
item.refresh_from_db()
q = item.quantity
print(f'\nWhile locked: on_hand={q["on_hand"]}, on_so={q["on_so"]}, on_po={q["on_po"]} (should be unchanged: 100, 9, 6)')

# Show pending records
pendings = Pending.objects.filter(model_name='item', record_id='308')
pending_count = pendings.filter(dt_processed=0).count()
applied_count = pendings.exclude(dt_processed=0).count()
print(f'\nPending records: {pendings.count()} total, {applied_count} applied, {pending_count} still pending')

# Phase 7: UNLOCK — process pending via celery path
item.is_locked = False
item.save(update_fields=['is_locked'])
print(f'\n--- ITEM UNLOCKED ---')

from apps.transactions.services.pending_inventory_processor import process_pending_for_item
result = process_pending_for_item(item_id=308)
print(f'Processed: {result["processed"]}, skipped_locked: {result["skipped_locked"]}')

# Final check
item.refresh_from_db()
q = item.quantity
print(f'\nFINAL: on_hand={q["on_hand"]}, on_p={q["on_p"]}, on_so={q["on_so"]}, on_po={q["on_po"]}, available={q["available"]}')
print(f'EXPECTED: on_hand=98, on_p=6, on_so=3, on_po=2, available=98')

ok = q['on_hand'] == 98 and q['on_p'] == 6 and q['on_so'] == 3 and q['on_po'] == 2
print(f'\n{"ALL PASS ✓" if ok else "FAILURES ✗"}')
