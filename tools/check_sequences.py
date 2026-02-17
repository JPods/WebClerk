"""Check that each transaction model has its own independent PK sequence and ida."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from django.db import connection
from apps.transactions.models import Order, Invoice, Proposal, Purchase, WorkOrder, Requisition

for Model in [Order, Invoice, Proposal, Purchase, WorkOrder, Requisition]:
    name = Model.__name__
    table = Model._meta.db_table
    count = Model.objects.count()

    if count > 0:
        first = Model.objects.order_by('id').first()
        last = Model.objects.order_by('id').last()
        print(f"{name} (table={table}): {count} rows")
        print(f"  id range: [{first.id} .. {last.id}]")
        print(f"  ida first={first.ida!r}  last={last.ida!r}")
        # Show all id/ida pairs
        for obj in Model.objects.order_by('id').values_list('id', 'ida'):
            print(f"    id={obj[0]}  ida={obj[1]!r}")
    else:
        print(f"{name} (table={table}): 0 rows")

    with connection.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
        seq = cur.fetchone()[0]
        if seq:
            cur.execute(f"SELECT last_value FROM {seq}")
            last_val = cur.fetchone()[0]
            print(f"  sequence: {seq}  last_value={last_val}")
        else:
            print(f"  sequence: NONE")
    print()
