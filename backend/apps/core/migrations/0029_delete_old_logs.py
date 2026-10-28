"""Drop the old log tables once the Log holds their rows (Bill, 2026-10-28: one log model).
Refuses if any copied source has more rows than the Log took from it."""
from django.db import migrations


def check_copied(apps, schema_editor):
    Log = apps.get_model('core', 'Log')
    for model, purpose in (('AuditLog', 'audit'), ('RefsMismatchLog', 'refs_mismatch')):
        n_old = apps.get_model('core', model).objects.count()
        n_new = Log.objects.filter(purpose=purpose).count()
        if n_new < n_old:
            raise RuntimeError(f"{model} copy incomplete: {n_old} rows, {n_new} in Log")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_remove_alice_log_settings'),
    ]

    operations = [
        migrations.RunPython(check_copied, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='apilog',
            name='user',
        ),
        migrations.RemoveField(
            model_name='auditlog',
            name='user',
        ),
        migrations.DeleteModel(
            name='RefsMismatchLog',
        ),
        migrations.AlterUniqueTogether(
            name='userdailylog',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='userdailylog',
            name='user',
        ),
        migrations.DeleteModel(
            name='APILog',
        ),
        migrations.DeleteModel(
            name='AuditLog',
        ),
        migrations.DeleteModel(
            name='UserDailyLog',
        ),
    ]
