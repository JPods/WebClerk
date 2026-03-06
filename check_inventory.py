#!/usr/bin/env python
"""Check inventory state for item 259."""
import os
import sys
import django

sys.path.insert(0, '/Users/williamjames/Documents/CommerceExpert/webClerk3')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.products.models import Item
from apps.core.models import Pending
from apps.transactions.models import ProposalLine, OrderLine, InvoiceLine, PurchaseLine

item = Item.objects.get(pk=259)
print('=== ITEM 259 QUANTITY ===')
for k, v in sorted(item.quantity.items()):
    print(f'  {k}: {v}')

print()
print('=== PENDING RECORDS FOR ITEM 259 ===')
pendings = Pending.objects.filter(model_name='item', record_id='259').order_by('-dt_created')
for p in pendings:
    data = p.data or {}
    print(f'  #{p.pk}: {p.purpose} ({data.get("type_id", "?")})')
    print(f'    on_so={data.get("on_so", 0)}, on_po={data.get("on_po", 0)}, on_p={data.get("on_p", 0)}, on_in={data.get("on_in", 0)}')
    print(f'    processed: {p.dt_processed}')

print()
print('=== LINES FOR ITEM 259 ===')
print('Proposal lines:')
for line in ProposalLine.objects.order_by('-id')[:10]:
    item_data = line.item or {}
    if item_data.get('item_id') == 259 or item_data.get('id') == 259:
        qty = (line.quantity or {}).get('staged', 0) or (line.quantity or {}).get('active', 0)
        print(f'  #{line.pk}: proposal={line.proposal_id}, qty={qty}')

print('Order lines:')
for line in OrderLine.objects.order_by('-id')[:10]:
    item_data = line.item or {}
    if item_data.get('item_id') == 259 or item_data.get('id') == 259:
        qty = (line.quantity or {}).get('staged', 0) or (line.quantity or {}).get('active', 0)
        print(f'  #{line.pk}: order={line.order_id}, qty={qty}')

print('Invoice lines:')
for line in InvoiceLine.objects.order_by('-id')[:10]:
    item_data = line.item or {}
    if item_data.get('item_id') == 259 or item_data.get('id') == 259:
        qty = (line.quantity or {}).get('staged', 0) or (line.quantity or {}).get('active', 0)
        print(f'  #{line.pk}: invoice={line.invoice_id}, qty={qty}')

print('Purchase lines:')
for line in PurchaseLine.objects.order_by('-id')[:10]:
    item_data = line.item or {}
    if item_data.get('item_id') == 259 or item_data.get('id') == 259:
        qty = (line.quantity or {}).get('staged', 0) or (line.quantity or {}).get('active', 0)
        print(f'  #{line.pk}: purchase={line.purchase_id}, qty={qty}')
