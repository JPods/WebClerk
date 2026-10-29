"""Pending.changes is a dict, as every reader takes it (core.models audit C-13); the two rows
holding the old empty-list default become empty dicts."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_contact_dt_joined_epoch_ms'),
    ]

    operations = [
        migrations.RunSQL("UPDATE pending SET changes = '{}'::jsonb WHERE changes = '[]'::jsonb",
                          migrations.RunSQL.noop),
        migrations.AlterField(
            model_name='pending',
            name='changes',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
