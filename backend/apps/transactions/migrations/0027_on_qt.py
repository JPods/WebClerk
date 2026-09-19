"""quantity.on_p → quantity.on_qt and pending type PP → QT (Bill, 2026-09-18): the
quote bucket is named for the quote, like on_so / on_po.

on_p is rewritten as a whole word (on_po is untouched) in every text and JSON column
outside Django's own tables; PP only where it is a pending type ("type_id": "PP")."""
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
            expr = (f"""regexp_replace(regexp_replace("{col}"::text, '\\mon_p\\M', 'on_qt', 'g'), """
                    f"""'"type_id": "PP"', '"type_id": "QT"', 'g')""")
            cur.execute(f'update "{table}" set "{col}" = ({expr}){cast} '
                        f"""where "{col}"::text ~ '\\mon_p\\M|"type_id": "PP"'""")


class Migration(migrations.Migration):

    dependencies = [('transactions', '0026_quote_stored_values')]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
