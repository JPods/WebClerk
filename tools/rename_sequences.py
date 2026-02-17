#!/usr/bin/env python
"""
Rename legacy PostgreSQL sequences to match current table names.

Before:                              After:
  sales_orders_id_seq          →  orders_id_seq
  purchase_orders_id_seq       →  purchases_id_seq
  sales_order_lines_id_seq     →  order_lines_id_seq
  purchase_order_lines_id_seq  →  purchase_lines_id_seq
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

import django
django.setup()

from django.db import connection

RENAMES = [
    ('sales_orders_id_seq',         'orders_id_seq'),
    ('purchase_orders_id_seq',      'purchases_id_seq'),
    ('sales_order_lines_id_seq',    'order_lines_id_seq'),
    ('purchase_order_lines_id_seq', 'purchase_lines_id_seq'),
]

with connection.cursor() as cur:
    for old_name, new_name in RENAMES:
        sql = f'ALTER SEQUENCE "{old_name}" RENAME TO "{new_name}"'
        print(f'  {sql}')
        cur.execute(sql)
        print(f'    ✓ done')

print('\nAll sequences renamed successfully.')
