"""
Migration to rename SalesOrder/SalesOrderLine to Order/OrderLine.

This migration:
1. Renames the Django models first
2. Renames the foreign key field
3. Renames the database tables
4. Renames the foreign key column
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0021_remove_invoice_is_locked_remove_invoice_po_number_and_more'),
    ]

    operations = [
        # Step 1: Rename the Django models (keeps using old table names)
        migrations.RenameModel(
            old_name='SalesOrder',
            new_name='Order',
        ),
        migrations.RenameModel(
            old_name='SalesOrderLine',
            new_name='OrderLine',
        ),
        
        # Step 2: Rename the foreign key field (still on old table)
        migrations.RenameField(
            model_name='orderline',
            old_name='salesorder_id',
            new_name='order_id',
        ),
        
        # Step 3: Rename the tables
        migrations.AlterModelTable(
            name='order',
            table='orders',
        ),
        migrations.AlterModelTable(
            name='orderline',
            table='order_lines',
        ),
    ]
