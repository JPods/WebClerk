#!/usr/bin/env python
"""
Fix EMPTY or MALFORMED ida values across all transaction models.

Only repairs records where ida is:
  - empty string ('')
  - bare numeric (e.g. '42' instead of 'DEV-42')
  - NULL

Records with a valid prefixed ida (e.g. 'DEV-42', 'LOC-15', 'ida-1087')
are LEFT UNTOUCHED to preserve provenance — a record born on another
environment keeps its original ida (see §25 Sync Topologies in data-sync docs).

Uses the IDA_PREFIX from settings / DATA_SET_ID (see common/ida.py).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

import django
django.setup()

from django.db import connection
from common.ida import get_ida_prefix

prefix = get_ida_prefix()
print(f"IDA prefix: {prefix!r}")
print(f"Mode: repair empty/malformed only (valid prefixed idas preserved)\n")

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

        # Expected ida format: "{prefix}-{id}"
        expected_expr = f"'{prefix}-' || CAST(id AS VARCHAR)"

        # Count idas in each category
        cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\" WHERE ida = ''  OR ida IS NULL")
        empty_count = cur.fetchone()[0]

        cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\" WHERE ida ~ '^[0-9]+$'")
        bare_numeric_count = cur.fetchone()[0]

        cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\" WHERE ida LIKE '%%-%%'")
        prefixed_count = cur.fetchone()[0]

        # Only fix empty or bare-numeric idas
        cur.execute(
            f"UPDATE \"{tbl}\" SET ida = {expected_expr} "
            f"WHERE ida = '' OR ida IS NULL OR ida ~ '^[0-9]+$'"
        )
        updated = cur.rowcount
        print(f'{tbl:30s}  total={total}  empty={empty_count}  bare_numeric={bare_numeric_count}  prefixed={prefixed_count}  fixed={updated}')

print(f'\nDone. Empty/malformed idas now follow "{prefix}-{{id}}" format.')
print(f'Valid prefixed idas from other environments were preserved.')
