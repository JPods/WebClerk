"""A line's cost.tax_code_id is a number, not a lookup on nothing (definition_scan, 2026-11-06).

The seeded leaf behavior on the seven line models read {'type': 'lookup'} with no model: a
search that could never find. No tax code model is registered (tax_jurisdiction is the tax
table); the leaf is the id a tax setup wrote, shown as the number it is.
"""
from django.db import migrations

LINES = ('invoice_line', 'order_line', 'purchase_line', 'quote_line', 'receipt_line', 'requisition_line', 'workorder_line')


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__in=LINES):
        if not isinstance(s.config, dict):
            continue
        behaviors = dict(s.config.get('behaviors') or {})
        beh = behaviors.get('cost.tax_code_id')
        if beh and beh.get('type') == 'lookup' and not beh.get('model'):
            behaviors['cost.tax_code_id'] = {**beh, 'type': 'number'}
            Setting.objects.filter(pk=s.pk).update(config={**s.config, 'behaviors': behaviors})


class Migration(migrations.Migration):
    dependencies = [('core', '0067_starter_lists_address_and_tax_exempt')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
