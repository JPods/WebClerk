"""A layout field names no status options of its own (readme 105, 2026-11-04).

The model's selectlists is the one source of a status list; a layout's inline options were a
fourth. 0054 rewrote lists, records and locks; this drops `options` from every layout field
named status inside a Setting config, and respells any other option list a config still holds
(the company profile's select_lists among them).
"""
from django.db import migrations

MAP = {'cancelled': 'canceled', 'completed': 'complete', 'onhold': 'on_hold'}
LABEL = {'canceled': 'Canceled', 'complete': 'Complete', 'on_hold': 'On Hold'}


def _options(options, status):
    out = []
    for o in options:
        if isinstance(o, str):
            out.append(MAP.get(o, 'on_hold' if status and o == 'hold' else o))
        elif isinstance(o, dict) and isinstance(o.get('value'), str):
            v = MAP.get(o['value'], 'on_hold' if status and o['value'] == 'hold' else o['value'])
            o = {**o, 'value': v}
            if v in LABEL and 'label' in o:
                o['label'] = LABEL[v]
            out.append(o)
        else:
            out.append(o)
    return out


def _walk(node, under_status=False):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == 'options' and isinstance(v, list):
                if node.get('field') == 'status':
                    continue
                out[k] = _options(v, under_status or node.get('field') == 'status')
            else:
                out[k] = _walk(v, k == 'status')
        return out
    if isinstance(node, list):
        return [_walk(x, under_status) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for setting in Setting.objects.exclude(config=None).iterator():
        if not isinstance(setting.config, dict):
            continue
        config = _walk(setting.config)
        if config != setting.config:
            Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0054_status_one_spelling')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
