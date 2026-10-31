"""A company decides whether its lists offer edit-in-list (Bill, 2026-10-31).

The company profile gains prefs.behavior.edit_in_list (on) when it lacks it, and staff are sent
it at startup (bootstrap_exposure). A company that has set it keeps its choice.
"""
from django.db import migrations

PATH = 'behavior.edit_in_list'


def add_switch(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:company_profile'):
        prefs = dict(s.prefs or {})
        behavior = dict(prefs.get('behavior') or {})
        behavior.setdefault('edit_in_list', True)
        prefs['behavior'] = behavior
        config = dict(s.config or {})
        exposure = dict(config.get('bootstrap_exposure') or {})
        staff = list(exposure.get('staff') or [])
        if PATH not in staff:
            staff.append(PATH)
        exposure['staff'] = staff
        config['bootstrap_exposure'] = exposure
        Setting.objects.filter(pk=s.pk).update(prefs=prefs, config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_contact_add_card'),
    ]

    operations = [
        migrations.RunPython(add_switch, migrations.RunPython.noop),
    ]
