from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0009_invoice_parent_id_invoice_parent_type_and_more"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="purchasereceipt",
            table="inventory_receipt",
        ),
    ]
