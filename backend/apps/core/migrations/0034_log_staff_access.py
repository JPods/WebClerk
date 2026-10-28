"""Staff below admin reach the Log: they write quiz answers and Alice feedback, and read
only the rows they are responsible for (Bill, 2026-10-28). LogBehaviour limits what they
write to LOG_STAFF_PURPOSES."""

from django.db import migrations

STAFF_ROLES = ('accounting', 'sales', 'production', 'warehouse', 'employee', 'rep')
BLOCK = {
    'view': ['id', 'ida', 'dt_created', 'purpose', 'action', 'model_name', 'record_id',
             'config.name', 'config.details', 'user_id'],
    'edit': ['purpose', 'action', 'model_name', 'record_id', 'config.name', 'config.details'],
    'scope': {'user_id': '$user.contact_id'},
    'create': True, 'delete': False,
}


def grant(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for setting in Setting.objects.filter(purpose='wc:model', parent_model='log'):
        config = dict(setting.config or {})
        access = dict(config.get('access') or {})
        roles = dict(access.get('roles') or {})
        for role in STAFF_ROLES:
            roles.setdefault(role, dict(BLOCK))
        access['roles'] = roles
        config['access'] = access
        Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_delete_alice_aggregates'),
    ]

    operations = [
        migrations.RunPython(grant, migrations.RunPython.noop),
    ]
