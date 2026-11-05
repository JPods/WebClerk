"""The stored layouts' edit rules take the one spelling too (readme 105, 2026-11-05).

0054 respelled locked_statuses; the transaction layouts also hold open_statuses,
pend_statuses and closed_statuses, and the stored invoice and order still said completed and
cancelled there, so a complete document never read as closed. layouts.json and the bundles
were already right.
"""
from django.db import migrations

MAP = {'cancelled': 'canceled', 'completed': 'complete', 'onhold': 'on_hold', 'hold': 'on_hold'}
KEYS = ('open_statuses', 'pend_statuses', 'closed_statuses', 'locked_statuses')


def _walk(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in KEYS and isinstance(v, list):
                out[k] = list(dict.fromkeys(MAP.get(x, x) if isinstance(x, str) else x for x in v))
            else:
                out[k] = _walk(v)
        return out
    if isinstance(node, list):
        return [_walk(x) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.exclude(config=None).iterator():
        if isinstance(s.config, dict):
            config = _walk(s.config)
            if config != s.config:
                Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0057_lists_code_held_terms_lookup')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
