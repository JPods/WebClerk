"""The receipt form heads its freight field "freight", the stored name, not "vendor_invoice_freight"
(Bill, 2026-11-25: "For users to learn the data, we need consistency"). The field is
allocations.freight; the old label came from a column that no longer exists. Only a label still
reading the old text is changed.
"""
from django.db import migrations

OLD, NEW = 'vendor_invoice_freight', 'freight'


def relabel(node):
    """Returns (node, changed) with every allocations.freight field labelled OLD relabelled NEW."""
    if isinstance(node, dict):
        changed = False
        out = {}
        for key, value in node.items():
            out[key], c = relabel(value)
            changed = changed or c
        if out.get('field') == 'allocations.freight' and out.get('label') == OLD:
            out['label'] = NEW
            changed = True
        return out, changed
    if isinstance(node, list):
        pairs = [relabel(v) for v in node]
        return [p[0] for p in pairs], any(p[1] for p in pairs)
    return node, False


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='receipt'):
        config, changed = relabel(s.config)
        if changed:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('transactions', '0062_line_landed_shares')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
