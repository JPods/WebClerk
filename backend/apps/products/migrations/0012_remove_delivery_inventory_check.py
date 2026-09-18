# DeliveryVisit/DeliveryLine and InventoryCheck/InventoryCheckLine removed (Bill, 2026-09-18):
# redundant to receipts. All four tables were empty on both databases, with no services and
# no views; they survived 0011 only because OrgItem's removal needed a target.
# The guard refuses to run if any rows appeared since.

from django.db import migrations

TABLES = ('products_deliveryvisit', 'products_deliveryline',
          'products_inventorycheck', 'products_inventorycheckline')
SETTINGS = ('wc-model-delivery_visit', 'wc-model-delivery_line',
            'wc-model-inventory_check', 'wc-model-inventory_check_line')


def guard_empty(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        for table in TABLES:
            cur.execute(f'select count(*) from "{table}"')
            n = cur.fetchone()[0]
            if n:
                raise RuntimeError(
                    f'{table} has {n} rows — removal assumes empty tables. '
                    'Move these rows onto receipts by hand before migrating.')


def delete_settings(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute('delete from settings where ida = any(%s)', [list(SETTINGS)])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_remove_orgitem'),
    ]

    operations = [
        migrations.RunPython(guard_empty, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='deliveryvisit',
            name='catalog',
        ),
        migrations.RemoveField(
            model_name='deliveryvisit',
            name='orgbase',
        ),
        migrations.RemoveField(
            model_name='inventorycheck',
            name='catalog',
        ),
        migrations.RemoveField(
            model_name='inventorycheck',
            name='orgbase',
        ),
        migrations.RemoveField(
            model_name='inventorycheck',
            name='user',
        ),
        migrations.RemoveField(
            model_name='inventorycheckline',
            name='inventory_check',
        ),
        migrations.RemoveField(
            model_name='inventorycheckline',
            name='item',
        ),
        migrations.DeleteModel(
            name='DeliveryLine',
        ),
        migrations.DeleteModel(
            name='DeliveryVisit',
        ),
        migrations.DeleteModel(
            name='InventoryCheck',
        ),
        migrations.DeleteModel(
            name='InventoryCheckLine',
        ),
        migrations.RunPython(delete_settings, migrations.RunPython.noop),
    ]
