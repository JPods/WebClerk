"""The staff role 'employee' is renamed 'support' (Bill, 2026-11-26: "remove 'employee' from
STAFF_ROLES. An employee is one of superuser, admin, accounting, sales, production, warehouse";
"I added support as the catchall employee role").

Being an employee is a fact about a person; a role says what they may do. What the old role could
see and change goes to 'support' unchanged, so nobody loses access:

1. every model definition's access block for 'employee' becomes its block for 'support' (a
   definition that already has a 'support' block keeps it and drops the old one);
2. every contact whose role is 'employee' becomes 'support';
3. the contact's role choices become the one vocabulary (access.LOGIN_ROLES).
"""
from django.db import migrations, models

OLD, NEW = 'employee', 'support'
ROLE_CHOICES = [('', ''), ('admin', 'admin'), ('accounting', 'accounting'), ('sales', 'sales'),
                ('production', 'production'), ('warehouse', 'warehouse'), ('support', 'support'),
                ('agent', 'agent'), ('rep', 'rep'), ('customer', 'customer'), ('buyer', 'buyer'),
                ('vendor', 'vendor'), ('manufacturer', 'manufacturer'), ('user', 'user')]


def renamed(config):
    """The definition's config with its 'employee' role block under 'support'."""
    config = dict(config or {})
    access = config.get('access')
    if not isinstance(access, dict) or not isinstance(access.get('roles'), dict) or OLD not in access['roles']:
        return config
    roles = dict(access['roles'])
    block = roles.pop(OLD)
    roles.setdefault(NEW, block)
    config['access'] = {**access, 'roles': roles}
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    touched = set()
    for s in Setting.objects.filter(purpose='wc:model'):
        if not isinstance(s.config, dict):
            continue
        config = renamed(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
            touched.add((s.parent_model or '').lower())
    apps.get_model('core', 'Contact').objects.filter(role=OLD).update(role=NEW)
    from apps.core.services.access import clear_cache
    for model in touched:
        clear_cache(model)


class Migration(migrations.Migration):
    dependencies = [('core', '0075_company_formatting_models_override')]
    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contact', name='role',
            field=models.CharField(choices=ROLE_CHOICES, default='user', help_text='User role in system', max_length=50),
        ),
    ]
