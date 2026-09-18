# OrgItem removed (Bill, 2026-09-18): Item is the defining model. OrgItem had no rows on
# either database, its min/max already lived on item.quantity, and every reader of it was
# broken. Prune now, bring back if a real per-(org, item) fact needs a home.
#
# DeliveryLine and InventoryCheckLine pointed at OrgItem; they now point at Item.
# Both tables were empty when this was written — the guard refuses to run otherwise,
# because there is no honest way to guess which Item an OrgItem-keyed line meant.

import json

import django.db.models.deletion
from django.db import migrations, models

LINE_SETTINGS = ('wc-model-delivery_line', 'wc-model-inventory_check_line')


def guard_empty(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        for table in ('products_deliveryline', 'products_inventorycheckline', 'products_orgitem'):
            cur.execute(f'select count(*) from "{table}"')
            n = cur.fetchone()[0]
            if n:
                raise RuntimeError(
                    f'{table} has {n} rows — OrgItem removal assumes empty tables. '
                    'Map these rows to Item by hand before migrating.')


def _rename(node):
    """orgitem (field) -> item; org_item (lookup model) -> item. Exact matches only."""
    if isinstance(node, dict):
        return {('item' if k == 'orgitem' else k): _rename(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_rename(v) for v in node]
    if node == 'orgitem' or node == 'org_item':
        return 'item'
    return node


def forward_settings(apps, schema_editor):
    with schema_editor.connection.cursor() as cur:
        cur.execute("delete from settings where ida = 'wc-model-org_item'")
        cur.execute('select id, config from settings where ida = any(%s)', [list(LINE_SETTINGS)])
        for pk, config in cur.fetchall():
            config = json.loads(config) if isinstance(config, str) else config
            new = _rename(config)
            if new != config:
                cur.execute('update settings set config = %s where id = %s', [json.dumps(new), pk])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_item_quantity_min_max'),
    ]

    operations = [
        migrations.RunPython(guard_empty, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='deliveryline', name='uniq_delivery_visit_orgitem'),
        migrations.RemoveConstraint(model_name='inventorycheckline', name='uniq_invchk_orgitem'),
        migrations.RemoveField(model_name='deliveryline', name='orgitem'),
        migrations.RemoveField(model_name='inventorycheckline', name='orgitem'),
        migrations.AddField(
            model_name='deliveryline',
            name='item',
            field=models.ForeignKey(db_column='item_id', default=0, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='delivery_lines', to='products.item'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='inventorycheckline',
            name='item',
            field=models.ForeignKey(db_column='item_id', default=0, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='inventory_check_lines', to='products.item'),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='deliveryline',
            constraint=models.UniqueConstraint(fields=('delivery_visit', 'item'), name='uniq_delivery_visit_item'),
        ),
        migrations.AddConstraint(
            model_name='inventorycheckline',
            constraint=models.UniqueConstraint(fields=('inventory_check', 'item'), name='uniq_invchk_item'),
        ),
        migrations.DeleteModel(name='OrgItem'),
        migrations.RunPython(forward_settings, migrations.RunPython.noop),
    ]
