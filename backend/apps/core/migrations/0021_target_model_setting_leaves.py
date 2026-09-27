"""Settings follow the model_name → target_model field rename (Bill, 2026-09-26).

The six models whose ``model_name`` field meant "the model this record is about" now call
it ``target_model`` (core 0020, docs 0007, ai_assistant 0010). Their Settings named the
field: role access lists (config.access.roles.<role>.view/edit/create), layouts (card,
panel, detail), field_groups and behaviors keyed by field name. Without this the leaf prune
would strip every role's access to the renamed field and layouts would show an empty column.

Only Settings whose parent_model is one of the six are touched, and inside them only an
exact ``'model_name'`` string or dict key: any other mention (a hook body, a help text)
is not a field reference. System models (ledger, pending, linkage, sync_bundle, ...)
keep ``model_name``.
"""
from django.db import migrations

SIX = ('report', 'notification', 'document', 'tag', 'alice_observation', 'alice_preset')
OLD, NEW = 'model_name', 'target_model'


def rename(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            k = NEW if k == OLD else k
            v = rename(v)
            if k == NEW and isinstance(v, dict) and v.get('label') == 'model name':
                v = {**v, 'label': 'target model'}           # behaviors.<field>.label
            out[k] = v
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            v = rename(v)
            if v == NEW and NEW in out:              # a list naming both: keep one
                continue
            out.append(v)
        return out
    return NEW if value == OLD else value


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for pk, config in (Setting.objects.filter(parent_model__in=SIX)
                       .values_list('pk', 'config').iterator()):
        new = rename(config)
        if new != config:
            Setting.objects.filter(pk=pk).update(config=new)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_target_model_rename'),
        ('docs', '0007_target_model_rename'),
        ('ai_assistant', '0010_target_model_rename'),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
