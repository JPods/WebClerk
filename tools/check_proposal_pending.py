#!/usr/bin/env python
"""Check proposals and pending inventory records."""

from apps.transactions.models import Proposal, ProposalLine
from apps.products.models import Item
from apps.core.models import Pending

# Check recent proposals
proposals = Proposal.objects.order_by('-dt_created')[:5]
print(f'Recent proposals: {proposals.count()}')
for p in proposals:
    lines = p.lines.all()
    print(f'  Proposal #{p.pk} ({p.ida or "no-ida"}): {lines.count()} lines, status={p.status}')
    for ln in lines[:3]:
        item_id = ln.item.get('item_id') if isinstance(ln.item, dict) else None
        qty = ln.quantity.get('placed') if isinstance(ln.quantity, dict) else None
        print(f'    - Line {ln.pk}: item_id={item_id}, qty.placed={qty}')

print()
# Check items 248, 249, 250, 251 quantity
print('Item quantities:')
for item_id in [248, 249, 250, 251]:
    try:
        item = Item.objects.get(pk=item_id)
        print(f'  Item {item_id} ({item.name[:30]}): {item.quantity_display}')
    except Item.DoesNotExist:
        print(f'  Item {item_id}: NOT FOUND')

print()
# Check for all pending records related to proposals
pending_pp = Pending.objects.filter(
    model_name='item'
).filter(data__type_id='PP').order_by('-dt_created')[:10]

print(f'Proposal pending records (PP type): {pending_pp.count()}')
for p in pending_pp:
    data = p.data or {}
    print(f'  [{p.pk}] {p.purpose}: item_id={data.get("item_id")}, processed={p.dt_processed}')
    print(f'       on_p={data.get("on_p", "N/A")}, qty_delta={data.get("quantity_delta", "N/A")}')
