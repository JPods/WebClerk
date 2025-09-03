"""No-op: serial_ida is native in squashed 0001_initial; rename unnecessary."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0005_add_qr_code_item_serial_and_serial_fields'),
    ]

    operations = []
