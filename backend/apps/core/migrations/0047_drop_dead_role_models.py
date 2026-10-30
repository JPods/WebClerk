"""One role source; the dead models go (Bill, 2026-10-29; core.models audit step 3).

contact.role is a login's one role. Login already read it; /me read contact.refs.roles and then
UserProfile, a second and third copy. RoleConfig and ModelRoleConfig were the old access rules
(access now lives only in each model definition's config.access); ModelLinkConfig was empty.
Notification held one fake row and nothing read it: a notification is an Action with purpose
'notification'. Workspace's 10 rows were read by nothing; a console that needs adjustable
settings gets a wc:workspace Setting when a page reads it.

1. contact.refs.roles goes from every contact (2 rows: user_customer, user_vendor — both
   contacts already hold that role in contact.role).
2. The notification and workspace model definitions go, and the dd_card stops naming
   notification (the Alice dashboard opens on action).
3. The tables are dropped.
"""
from django.db import migrations

DEAD_DEFINITIONS = ('notification', 'workspace')


def one_role_source(apps, schema_editor):
    Contact = apps.get_model('core', 'Contact')
    for contact in Contact.objects.filter(refs__has_key='roles'):
        refs = dict(contact.refs)
        refs.pop('roles')
        Contact.objects.filter(pk=contact.pk).update(refs=refs)


def drop_definitions(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Setting.objects.filter(purpose='wc:model', parent_model__in=DEAD_DEFINITIONS).delete()
    for card in Setting.objects.filter(purpose='wc:dd_card'):
        config = dict(card.config or {})
        (config.get('cards') or {}).pop('notification', None)
        alice = (config.get('dashboards') or {}).get('alice')
        if alice:
            alice['rows'] = [[m for m in row if m != 'notification'] for row in alice.get('rows', [])]
            if alice.get('default_model') == 'notification':
                alice['default_model'] = 'action'
        Setting.objects.filter(pk=card.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_pending_changes_dict'),
    ]

    operations = [
        migrations.RunPython(one_role_source, migrations.RunPython.noop),
        migrations.RunPython(drop_definitions, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='ModelLinkConfig',
        ),
        migrations.DeleteModel(
            name='ModelRoleConfig',
        ),
        migrations.DeleteModel(
            name='Notification',
        ),
        migrations.DeleteModel(
            name='RoleConfig',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='contact',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='user',
        ),
        migrations.DeleteModel(
            name='Workspace',
        ),
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
