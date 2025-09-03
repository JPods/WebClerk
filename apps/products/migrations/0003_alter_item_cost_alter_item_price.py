"""No-op: cost/price JSON factory defaults already present in squashed 0001_initial."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0002_billofmaterial_alternate_group_and_more'),
    ]

    operations = []
