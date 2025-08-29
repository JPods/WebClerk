"""No-op migration replacing auto-generated delete migration.

The previous auto-generated migration attempted to delete the Document model
after a transient field change (version field override) confusion. We retain
the original 0001 schema; this migration intentionally performs no operations
to keep the linear migration history intact.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('docs', '0001_initial'),
    ]

    operations = []
