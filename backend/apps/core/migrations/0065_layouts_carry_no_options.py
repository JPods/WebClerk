"""No layout field carries an option list (Bill, 2026-11-05: "I selected 'low' from the
selectlist. We should not have a difference between the selectlist and approved values").

The form offered what the layout's inline options held; the door checked the definition's
list; they differed. 0062 stripped the inline copy where the definition held the list. The
four lists only a layout held join their definitions (scope on databrowser, gantt, wc;
allocations.method on receipt); bill_of_material.is_optional is a boolean, drawn as one.
Then every layout field in every stored definition drops `options`: one source, the model's
selectlists, read by the form and by the door.
"""
from django.db import migrations

LISTS = {
    'databrowser': {'scope': ['system', 'org', 'role', 'user']},
    'gantt': {'scope': ['system', 'org', 'role', 'user']},
    'wc': {'scope': ['system', 'org', 'role', 'user']},
    'receipt': {'allocations.method': ['value', 'weight', 'quantity']},
}


def _options(values):
    return [{'value': v, 'label': v.replace('_', ' ').title()} for v in values]


def _strip(node):
    if isinstance(node, dict):
        return {k: _strip(v) for k, v in node.items() if not (k == 'options' and node.get('field'))}
    if isinstance(node, list):
        return [_strip(x) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model').iterator():
        if not isinstance(s.config, dict):
            continue
        config = dict(s.config)
        lists = dict(config.get('selectlists') or {})
        for field, values in LISTS.get(s.parent_model, {}).items():
            if not lists.get(field):
                lists[field] = _options(values)
        if lists:
            config['selectlists'] = lists
        if config.get('layout') is not None:
            config['layout'] = _strip(config['layout'])
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0064_company_defaults_plural')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
