#!/usr/bin/env python
"""Compare FK relation vs refs.links for getting sales order lines."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.transactions.models.sales_order import SalesOrder
from apps.transactions.models.sales_order_line import SalesOrderLine

print('=== COMPARISON: FK Relation vs refs.links ===')
print()

for so_id in [22, 28, 30]:
    so = SalesOrder.objects.get(pk=so_id)
    
    # Method 1: Standard FK relation (salesorder.lines via related_name)
    fk_lines = list(so.lines.values_list('id', flat=True))
    
    # Method 2: refs.links shortcut
    refs = so.refs or {}
    links = refs.get('links', {})
    ref_entries = links.get('sales_order_line', [])
    ref_ids = [e.get('id') if isinstance(e, dict) else e for e in ref_entries]
    
    # Method 3: Direct query by FK column
    direct_lines = list(SalesOrderLine.objects.filter(salesorder_id_id=so_id).values_list('id', flat=True))
    
    print(f'Sales Order {so_id}:')
    print(f'  FK relation (so.lines):     {len(fk_lines)} lines: {sorted(fk_lines)}')
    print(f'  refs.links:                 {len(ref_ids)} lines: {sorted(ref_ids)}')
    print(f'  Direct FK query:            {len(direct_lines)} lines: {sorted(direct_lines)}')
    
    # Check for mismatches
    fk_set = set(fk_lines)
    ref_set = set(ref_ids)
    direct_set = set(direct_lines)
    
    if fk_set != ref_set or fk_set != direct_set:
        print(f'  ⚠️  MISMATCH DETECTED!')
        print(f'      In FK but not refs: {fk_set - ref_set}')
        print(f'      In refs but not FK: {ref_set - fk_set}')
        print(f'      In direct but not FK: {direct_set - fk_set}')
    else:
        print(f'  ✓ All methods match')
    print()
