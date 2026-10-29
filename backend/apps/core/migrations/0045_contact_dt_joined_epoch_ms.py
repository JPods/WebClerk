"""contact.dt_joined is UTC epoch ms like every stored date (Axiom 14; core.models audit C-11).
The column converts in place: each timestamp becomes its milliseconds since the epoch."""
from django.db import migrations, models

import apps.core.models.contact


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_action_drop_unwritten_by_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(
                'ALTER TABLE contacts ALTER COLUMN dt_joined TYPE bigint '
                'USING (extract(epoch FROM dt_joined) * 1000)::bigint',
                'ALTER TABLE contacts ALTER COLUMN dt_joined TYPE timestamp with time zone '
                'USING to_timestamp(dt_joined / 1000.0)')],
            state_operations=[migrations.AlterField(
                model_name='contact', name='dt_joined',
                field=models.BigIntegerField(default=apps.core.models.contact.now_ms,
                                             help_text='Account creation date (UTC epoch ms)'))],
        ),
    ]
