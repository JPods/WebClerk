"""Settings stop naming is_locked (Bill, 2026-09-28: dt_journaled is the one journal lock).

is_locked left every model in the *_is_locked_deleted migrations. The wc:model Settings named
it in role access lists, layouts, field groups and behaviors (as a list entry or a dict key);
left there, the door's leaf check and the layouts would name a field that no longer exists.
Only an exact 'is_locked' list entry or dict key is removed.
"""
from django.db import migrations

GONE = 'is_locked'


def prune(value):
    if isinstance(value, dict):
        return {k: prune(v) for k, v in value.items() if k != GONE}
    if isinstance(value, list):
        return [prune(v) for v in value if v != GONE]
    return value


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for pk, config in (Setting.objects.filter(config__icontains=GONE)
                       .values_list('pk', 'config').iterator()):
        new = prune(config)
        if new != config:
            Setting.objects.filter(pk=pk).update(config=new)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_is_locked_deleted'),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
