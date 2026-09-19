"""Receipt bucket → quantity.on_rc (Bill, 2026-09-18). Code wrote on_r, the item schema
said on_reciept (misspelled), so the two never lined up. Every bucket is now on_ + its
pending code: on_qt/QT, on_so/SO, on_po/PO, on_wo/WO, on_in/IN, on_rc/RC.

on_r and on_reciept are rewritten as whole words in every text and JSON column outside
Django's own tables."""
from django.db import migrations

SKIP_TABLE_PREFIXES = ('django_', 'auth_')


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute("""
            select c.table_name, c.column_name, c.data_type
            from information_schema.columns c
            join information_schema.tables t on t.table_name = c.table_name and t.table_schema = c.table_schema
            where c.table_schema = 'public' and t.table_type = 'BASE TABLE'
              and c.data_type in ('text', 'character varying', 'json', 'jsonb')
        """)
        for table, col, dtype in cur.fetchall():
            if table.startswith(SKIP_TABLE_PREFIXES):
                continue
            cast = '::jsonb' if dtype == 'jsonb' else ('::json' if dtype == 'json' else '')
            cur.execute(f"""update "{table}" set "{col}" =
                (regexp_replace("{col}"::text, '\\m(on_r|on_reciept)\\M', 'on_rc', 'g')){cast}
                where "{col}"::text ~ '\\m(on_r|on_reciept)\\M'""")


class Migration(migrations.Migration):

    dependencies = [('transactions', '0027_on_qt')]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
