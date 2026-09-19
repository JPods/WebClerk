"""Clear tax rates left on lines by the old engine (recheck 2).

eb6836e wrote the resolved rate onto each line's tax envelope. 0030 stripped
tax.sales and the rate_source marker, leaving sales_rate behind, so 39 legacy lines
looked as though a user had typed a rate. Only a rate with rate_source 'line' is a
user's, and the engine now reads only that; these leftovers are removed.
"""
from django.db import migrations

LINE_TABLES = ('quote_lines', 'order_lines', 'invoice_lines',
               'purchase_lines', 'work_order_lines', 'requisition_lines', 'receipt_line')


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        for table in LINE_TABLES:
            cur.execute("select 1 from information_schema.tables where table_name=%s", [table])
            if not cur.fetchone():
                continue
            cur.execute(f"""
                update {table} set tax = tax - 'sales_rate'
                 where jsonb_typeof(tax) = 'object' and tax ? 'sales_rate'
                   and coalesce(tax->>'rate_source', '') <> 'line'
            """)


class Migration(migrations.Migration):
    dependencies = [('transactions', '0030_line_totals_allocations')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
