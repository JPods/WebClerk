#!/usr/bin/env python
"""List all transaction-related tables and their associated PK sequences."""
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
    print(f"{'TABLE':<30s} {'SEQUENCE':<45s} {'MATCH?'}")
    print('-' * 85)
    for tbl in TABLES:
        cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", [tbl])
        row = cur.fetchone()
        seq = row[0] if row and row[0] else '(not found)'
        # Expected: public.<table>_id_seq
        expected = f'public.{tbl}_id_seq'
        match = 'OK' if seq == expected else 'MISMATCH' if seq != '(not found)' else '??'
        print(f'{tbl:<30s} {seq:<45s} {match}')
