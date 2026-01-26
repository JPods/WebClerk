"""
Migration to rename order_id_id column to order_id (proper Django FK naming).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0022_rename_sales_order_to_order'),
    ]

    operations = [
        # Rename the field from order_id to order (which creates order_id column)
        migrations.RenameField(
            model_name='orderline',
            old_name='order_id',
            new_name='order',
        ),
    ]
