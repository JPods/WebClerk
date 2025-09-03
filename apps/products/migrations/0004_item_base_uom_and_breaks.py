"""No-op: base_uom + factories folded into 0001_initial squash."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0003_alter_item_cost_alter_item_price'),
    ]

    operations = []
