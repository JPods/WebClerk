#!/usr/bin/env python
"""
Fix all ida values across all transaction models to use "ida-{id}" format.

Updates: orders, invoices, proposals, purchases, work_orders, requisitions,
         order_lines, invoice_lines, proposal_lines, purchase_lines,
         work_order_lines, requisition_lines
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

import django
django.setup()

from django.db import connection

TABLES = [
    'orders', 'invoices', 'proposals', 'purchases',
    'work_orders', 'requisitions',
    'order_lines', 'invoice_lines', 'proposal_lines',
    'purchase_lines', 'work_order_lines', 'requisition_lines',
]

with connection.cursor() as cur:
    for tbl in TABLES:
        # Check how many exist
        cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
        total = cur.fetchone()[0]
        if total == 0:
            print(f'{tbl:30s}  (empty)')
            continue

        # Count how many already have correct ida
        cur.execute(
            f"SELECT COUNT(*) FROM \"{tbl}\" WHERE ida = 'ida-' || CAST(id AS VARCHAR)"
        )
        already_ok = cur.fetchone()[0]

        # Update all that don't match
        cur.execute(
            f"UPDATE \"{tbl}\" SET ida = 'ida-' || CAST(id AS VARCHAR) "
            f"WHERE ida != 'ida-' || CAST(id AS VARCHAR)"
        )
        updated = cur.rowcount
        print(f'{tbl:30s}  total={total}  already_ok={already_ok}  updated={updated}')

print('\nDone. All ida values now follow "ida-{id}" format.')
