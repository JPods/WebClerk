"""Settings hold only the structure of the application (Bill, 2026-10-28).

Removes the alice_log Settings once their copy is checked (refuses if the Log holds fewer alice
rows than it removes), the model definitions of the removed log models, and points the admin
console's Serials entry at serial (it opened serial_log)."""
import json

from django.db import migrations

REMOVED_MODELS = ('serial_log', 'alice_coaching_log')


def settings_hold_structure(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Log = apps.get_model('core', 'Log')
    old = Setting.objects.filter(purpose='alice_log')
    n_old, n_new = old.count(), Log.objects.filter(purpose='alice').count()
    if n_new < n_old:
        raise RuntimeError(f"alice_log copy incomplete: {n_old} Settings, {n_new} Log rows")
    old.delete()
    Setting.objects.filter(purpose='wc:model', parent_model__in=REMOVED_MODELS).delete()
    for s in Setting.objects.filter(purpose='wc:admin'):
        text = json.dumps(s.config)
        fixed = text.replace('/databrowser?model=serial_log"', '/databrowser?model=serial"')
        if fixed != text:
            Setting.objects.filter(pk=s.pk).update(config=json.loads(fixed))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_log_copy'),
    ]

    operations = [
        migrations.RunPython(settings_hold_structure, migrations.RunPython.noop),
    ]
