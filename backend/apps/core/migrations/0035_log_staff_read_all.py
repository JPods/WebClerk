"""Staff below admin read everyone's quiz and Alice rows in the Log and change only their own
(Bill, 2026-10-28). The purposes they reach are their scope here, in the log Setting, so an
administrator sets the limit; LogBehaviour still makes the writer the responsible person."""

from django.db import migrations

STAFF_ROLES = ('accounting', 'sales', 'production', 'warehouse', 'employee', 'rep')


def widen(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for setting in Setting.objects.filter(purpose='wc:model', parent_model='log'):
        config = dict(setting.config or {})
        access = dict(config.get('access') or {})
        roles = dict(access.get('roles') or {})
        for role in STAFF_ROLES:
            if role in roles:
                block = dict(roles[role])
                block['scope'] = {'purpose__in': ['alice', 'quiz']}
                block['edit_scope'] = {'user_id': '$user.contact_id'}
                roles[role] = block
        access['roles'] = roles
        config['access'] = access
        Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_log_staff_access'),
    ]

    operations = [
        migrations.RunPython(widen, migrations.RunPython.noop),
    ]
