"""A layout field typed select has a list in its definition, or it is not typed select.

0065 dropped every layout's inline options; bill_of_material.is_optional, a boolean drawn as a
checkbox by its behavior, kept a card node typed 'select' and the layout's type wins over the
behavior's — an empty select (the lead's check on 5dda28d). The layout type goes; the behavior
draws the widget. Generic: any select-typed layout field whose definition holds no list.
"""
from django.db import migrations


def _untype(node, lists):
    if isinstance(node, dict):
        if node.get('type') == 'select' and node.get('field') and node['field'] not in lists:
            node = {k: v for k, v in node.items() if k != 'type'}
        return {k: _untype(v, lists) for k, v in node.items()}
    if isinstance(node, list):
        return [_untype(x, lists) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model').iterator():
        if not isinstance(s.config, dict) or s.config.get('layout') is None:
            continue
        layout = _untype(s.config['layout'], set(s.config.get('selectlists') or {}))
        if layout != s.config['layout']:
            Setting.objects.filter(pk=s.pk).update(config={**s.config, 'layout': layout})


class Migration(migrations.Migration):
    dependencies = [('core', '0065_layouts_carry_no_options')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
