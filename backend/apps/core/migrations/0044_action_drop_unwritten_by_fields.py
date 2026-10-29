"""Action drops five *_by fields nothing writes (core.models audit C-9): start_by, deadline_by,
expected_by, completed_by, end_by. Only one row held a value (a seed stamp from a system login).
They leave the action definition first: its layout, access field sets, field groups and
behaviours.
"""

from django.db import migrations

DROPPED = {'start_by', 'deadline_by', 'expected_by', 'completed_by', 'end_by'}


def out_of_definition(apps, schema_editor):
    from apps.core.layouts import without_fields
    Setting = apps.get_model('core', 'Setting')
    for d in Setting.objects.filter(purpose='wc:model', parent_model='action'):
        config = without_fields(dict(d.config or {}), DROPPED)
        config['behaviors'] = {k: v for k, v in (config.get('behaviors') or {}).items() if k not in DROPPED}
        Setting.objects.filter(pk=d.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_log_user_id_value'),
    ]

    operations = [
        migrations.RunPython(out_of_definition, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='action',
            name='completed_by',
        ),
        migrations.RemoveField(
            model_name='action',
            name='deadline_by',
        ),
        migrations.RemoveField(
            model_name='action',
            name='end_by',
        ),
        migrations.RemoveField(
            model_name='action',
            name='expected_by',
        ),
        migrations.RemoveField(
            model_name='action',
            name='start_by',
        ),
    ]
