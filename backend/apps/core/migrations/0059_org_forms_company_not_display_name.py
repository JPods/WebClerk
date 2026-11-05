"""An org's form edits company, the field, not display_name, the property (2026-11-05).

The identity column of the customer, vendor, manufacturer, rep and employee forms named
display_name — OrgBase.COMPUTED_FIELDS, computed from company — as its editable name, so a typed
name was refused by the door (unknown_field) and a customer could not be named from its form
(Bill: "saving customer is not working"). The field is company.
"""
from django.db import migrations

ORGS = ('customer', 'vendor', 'manufacturer', 'rep', 'employee')


def _fix(node):
    if isinstance(node, dict):
        if node.get('field') == 'display_name':
            return {**node, 'field': 'company', 'label': 'company'}
        return {k: _fix(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_fix(x) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__in=ORGS):
        if isinstance(s.config, dict) and 'layout' in s.config:
            layout = _fix(s.config['layout'])
            if layout != s.config['layout']:
                Setting.objects.filter(pk=s.pk).update(config={**s.config, 'layout': layout})


class Migration(migrations.Migration):
    dependencies = [('core', '0058_edit_rules_one_spelling')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
