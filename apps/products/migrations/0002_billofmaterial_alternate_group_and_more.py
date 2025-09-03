"""No-op legacy migration kept only to satisfy historical dependency chain after squash.

All operations from this file were folded into 0001_initial during the 2025-09-03
products migration squash. Left intentionally empty to avoid duplicate column/constraint
errors when applying migrations on a fresh database.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = []
