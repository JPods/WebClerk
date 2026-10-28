"""SerialLog removed: a serial's history is its own config.actions (Bill, 2026-10-28); the
rows were folded in by core 0027_log_copy."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0023_catalog_line_item_optional'),
        ('core', '0027_log_copy'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SerialLog',
        ),
    ]
