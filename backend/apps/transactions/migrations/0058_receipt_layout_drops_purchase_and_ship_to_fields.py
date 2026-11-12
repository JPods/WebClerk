"""The receipt form's ``receiving`` column loses four fields that showed nothing (Bill,
2026-11-12: "Remove them"): ``purchase.ida`` (the server sends no ``purchase`` object — it drew
a dash) and ``config.ship_to.company / .address1 / .city_state_zip`` (a receipt has no ship-to).
"""
from django.db import migrations

GONE = ('purchase.ida', 'config.ship_to.company', 'config.ship_to.address1', 'config.ship_to.city_state_zip')


def trimmed(node):
    if isinstance(node, list):
        return [trimmed(item) for item in node
                if not (isinstance(item, dict) and item.get('field') in GONE)]
    if isinstance(node, dict):
        return {k: trimmed(v) for k, v in node.items()}
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='receipt'):
        if isinstance(s.config, dict) and 'layout' in s.config:
            layout = trimmed(s.config['layout'])
            if layout != s.config['layout']:
                Setting.objects.filter(pk=s.pk).update(config={**s.config, 'layout': layout})


class Migration(migrations.Migration):
    dependencies = [('transactions', '0057_receipt_vendor_block')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
