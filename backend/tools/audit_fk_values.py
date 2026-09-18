#!/usr/bin/env python
"""Audit transaction FK fields for invalid values (zero, negative)."""
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from django.db import connection

c = connection.cursor()
tables = [
    'transactions_order',
    'transactions_invoice',
    'transactions_proposal',
    'transactions_purchase',
]
fk_cols = ['customer_id', 'vendor_id', 'manufacturer_id', 'contact_id']

for t in tables:
    c.execute(f'SELECT count(*) FROM {t}')
    total = c.fetchone()[0]
    parts = []
    for col in fk_cols:
        c.execute(f'SELECT count(*) FROM {t} WHERE {col} = 0')
        zeros = c.fetchone()[0]
        c.execute(f'SELECT count(*) FROM {t} WHERE {col} < 0')
        negs = c.fetchone()[0]
        if zeros or negs:
            parts.append(f'{col}: {zeros}z/{negs}n')
            c.execute(f'SELECT id, {col} FROM {t} WHERE {col} <= 0 LIMIT 5')
            for row in c.fetchall():
                parts.append(f'  id={row[0]} {col}={row[1]}')
    bad_str = ' | '.join(parts) if parts else 'clean'
    print(f'{t}: {total} total -- {bad_str}')

# Check OrgBase __str__
from apps.orgs.models import OrgBase
org = OrgBase.objects.get(id=82)
print(f'OrgBase #82: display_name={org.display_name}, __str__={str(org)}')
