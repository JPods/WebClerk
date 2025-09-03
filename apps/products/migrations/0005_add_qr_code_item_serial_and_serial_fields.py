"""No-op: qr_code + Serial extended fields included in squashed 0001_initial."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0004_item_base_uom_and_breaks'),
    ]

    operations = []
