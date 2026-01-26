"""
Migration to rename PurchaseOrder/PurchaseOrderLine to Purchase/PurchaseLine.

This migration:
1. Renames the Django models
2. Renames the foreign key field
3. Renames the database tables
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0023_rename_order_id_to_order'),
    ]

    operations = [
        # Step 1: Rename the Django models (keeps using old table names)
        migrations.RenameModel(
            old_name='PurchaseOrder',
            new_name='Purchase',
        ),
        migrations.RenameModel(
            old_name='PurchaseOrderLine',
            new_name='PurchaseLine',
        ),
        
        # Step 2: Rename the foreign key field (still on old table)
        migrations.RenameField(
            model_name='purchaseline',
            old_name='purchaseorder_id',
            new_name='purchase',
        ),
        
        # Step 3: Rename the tables
        migrations.AlterModelTable(
            name='purchase',
            table='purchases',
        ),
        migrations.AlterModelTable(
            name='purchaseline',
            table='purchase_lines',
        ),
    ]
