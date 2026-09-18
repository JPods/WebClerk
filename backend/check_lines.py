#!/usr/bin/env python
"""Check recent lines for item 259."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.transactions.models import ProposalLine, OrderLine, InvoiceLine, PurchaseLine
from django.db import connection

print('=== RECENT LINES FOR ITEM 259 ===')

# Use raw SQL to check what columns exist
with connection.cursor() as cursor:
    # Check proposal_lines columns
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'proposal_lines' AND column_name LIKE 'proposal%'")
    cols = cursor.fetchall()
    print(f'\nproposal_lines FK columns: {[c[0] for c in cols]}')
    
    # Check invoice_lines columns  
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'invoice_lines' AND column_name LIKE 'invoice%'")
    cols = cursor.fetchall()
    print(f'invoice_lines FK columns: {[c[0] for c in cols]}')
    
    # Check order_lines columns
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'order_lines' AND column_name LIKE 'order%'")
    cols = cursor.fetchall()
    print(f'order_lines FK columns: {[c[0] for c in cols]}')
    
    # Check purchase_lines columns
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'purchase_lines' AND column_name LIKE 'purchase%'")
    cols = cursor.fetchall()
    print(f'purchase_lines FK columns: {[c[0] for c in cols]}')

# Check order lines (should work - it created pending record)
print('\n--- ORDER LINES for item 259 ---')
try:
    for line in OrderLine.objects.order_by('-id')[:10]:
        item_data = line.item or {}
        item_id = item_data.get('item_id') or item_data.get('id')
        if item_id == 259:
            qty = (line.quantity or {}).get('placed', 0)
            print(f'  #{line.pk}: order_id={line.order_id}, qty={qty}')
except Exception as e:
    print(f'  Error: {e}')

# Check purchase lines
print('\n--- PURCHASE LINES for item 259 ---')  
try:
    for line in PurchaseLine.objects.order_by('-id')[:10]:
        item_data = line.item or {}
        item_id = item_data.get('item_id') or item_data.get('id')
        if item_id == 259:
            qty = (line.quantity or {}).get('placed', 0)
            print(f'  #{line.pk}: purchase_id={line.purchase_id}, qty={qty}')
except Exception as e:
    print(f'  Error: {e}')

# Check proposal lines
print('\n--- PROPOSAL LINES for item 259 ---')
try:
    for line in ProposalLine.objects.order_by('-id')[:10]:
        item_data = line.item or {}
        item_id = item_data.get('item_id') or item_data.get('id')
        if item_id == 259:
            qty = (line.quantity or {}).get('placed', 0)
            print(f'  #{line.pk}: proposal_id={line.proposal_id}, qty={qty}')
except Exception as e:
    print(f'  Error: {e}')

# Check invoice lines
print('\n--- INVOICE LINES for item 259 ---')
try:
    for line in InvoiceLine.objects.order_by('-id')[:10]:
        item_data = line.item or {}
        item_id = item_data.get('item_id') or item_data.get('id')
        if item_id == 259:
            qty = (line.quantity or {}).get('placed', 0)
            print(f'  #{line.pk}: invoice_id={line.invoice_id}, qty={qty}')
except Exception as e:
    print(f'  Error: {e}')
