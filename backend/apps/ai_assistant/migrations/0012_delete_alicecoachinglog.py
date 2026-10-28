"""AliceCoachingLog removed: drills are Log rows, purpose coaching (Bill, 2026-10-28: one log
model); copied by core 0027_log_copy."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0011_is_locked_deleted'),
        ('core', '0027_log_copy'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AliceCoachingLog',
        ),
    ]
