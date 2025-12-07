# Generated manually for renaming id fields to follow naming convention

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_paymentmethod_paymentterm_payment'),
    ]

    operations = [
        # Rename customer_id to id_customer in all transaction tables
        migrations.RenameField(
            model_name='invoice',
            old_name='customer_id',
            new_name='id_customer',
        ),
        migrations.RenameField(
            model_name='proposal',
            old_name='customer_id',
            new_name='id_customer',
        ),
        migrations.RenameField(
            model_name='purchaseorder',
            old_name='customer_id',
            new_name='id_customer',
        ),
        migrations.RenameField(
            model_name='salesorder',
            old_name='customer_id',
            new_name='id_customer',
        ),
        migrations.RenameField(
            model_name='workorder',
            old_name='customer_id',
            new_name='id_customer',
        ),

        # Rename manufacturer_id to id_manufacturer
        migrations.RenameField(
            model_name='invoice',
            old_name='manufacturer_id',
            new_name='id_manufacturer',
        ),
        migrations.RenameField(
            model_name='proposal',
            old_name='manufacturer_id',
            new_name='id_manufacturer',
        ),
        migrations.RenameField(
            model_name='purchaseorder',
            old_name='manufacturer_id',
            new_name='id_manufacturer',
        ),
        migrations.RenameField(
            model_name='salesorder',
            old_name='manufacturer_id',
            new_name='id_manufacturer',
        ),
        migrations.RenameField(
            model_name='workorder',
            old_name='manufacturer_id',
            new_name='id_manufacturer',
        ),

        # Rename vendor_id to id_vendor
        migrations.RenameField(
            model_name='invoice',
            old_name='vendor_id',
            new_name='id_vendor',
        ),
        migrations.RenameField(
            model_name='proposal',
            old_name='vendor_id',
            new_name='id_vendor',
        ),
        migrations.RenameField(
            model_name='purchaseorder',
            old_name='vendor_id',
            new_name='id_vendor',
        ),
        migrations.RenameField(
            model_name='salesorder',
            old_name='vendor_id',
            new_name='id_vendor',
        ),
        migrations.RenameField(
            model_name='workorder',
            old_name='vendor_id',
            new_name='id_vendor',
        ),
    ]