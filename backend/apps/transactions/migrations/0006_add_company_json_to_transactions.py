# Convert company from varchar to JSONB on all transaction tables.
# Preserves existing varchar value as company.name in the new JSON.

from django.db import migrations


TABLES = ['orders', 'invoices', 'proposals', 'purchases', 'work_orders']


def _column_type(cursor, table, column):
    cursor.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        [table, column],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def convert_company_varchar_to_json(apps, schema_editor):
    """Convert existing varchar company values to JSON objects.

    Idempotent: only a legacy varchar column is converted. On fresh databases built
    from the regenerated 0001_initial there is no company column yet — 0009 adds it.
    """
    from django.db import connection
    cursor = connection.cursor()

    for table in TABLES:
        if _column_type(cursor, table, 'company') != 'character varying':
            continue
        cursor.execute(f'ALTER TABLE {table} RENAME COLUMN company TO company_old')
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN company jsonb DEFAULT '{{}}'::jsonb")
        cursor.execute(f"""
            UPDATE {table}
            SET company = jsonb_build_object('name', COALESCE(company_old, ''))
            WHERE company_old IS NOT NULL AND company_old != ''
        """)
        cursor.execute(f'ALTER TABLE {table} DROP COLUMN company_old')


def reverse_company_json_to_varchar(apps, schema_editor):
    """Reverse: extract company.name back to varchar."""
    from django.db import connection
    cursor = connection.cursor()

    for table in TABLES:
        cursor.execute(f'ALTER TABLE {table} RENAME COLUMN company TO company_json')
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN company varchar(255)')
        cursor.execute(f"UPDATE {table} SET company = company_json->>'name' WHERE company_json IS NOT NULL")
        cursor.execute(f'ALTER TABLE {table} DROP COLUMN company_json')


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0005_cascade_fks_to_values'),
    ]

    operations = [
        migrations.RunPython(convert_company_varchar_to_json, reverse_company_json_to_varchar),
    ]
