# Data migration: update stored parent_model values after model renames
# - "purchase_order" → "purchase"
# - "sales_order" → "order"

from django.db import migrations


def update_parent_model_values(apps, schema_editor):
    """Update parent_model column in all transaction tables."""
    renames = {
        "purchase_order": "purchase",
        "sales_order": "order",
    }
    model_names = ["Invoice", "Order", "Proposal", "Purchase", "WorkOrder"]
    for model_name in model_names:
        Model = apps.get_model("transactions", model_name)
        for old_val, new_val in renames.items():
            Model.objects.filter(parent_model=old_val).update(parent_model=new_val)


def reverse_parent_model_values(apps, schema_editor):
    """Reverse: restore old parent_model values."""
    renames = {
        "purchase": "purchase_order",
        "order": "sales_order",
    }
    model_names = ["Invoice", "Order", "Proposal", "Purchase", "WorkOrder"]
    for model_name in model_names:
        Model = apps.get_model("transactions", model_name)
        for old_val, new_val in renames.items():
            Model.objects.filter(parent_model=old_val).update(parent_model=new_val)


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0036_alter_payment_contact_id_and_more"),
    ]

    operations = [
        migrations.RunPython(
            update_parent_model_values,
            reverse_code=reverse_parent_model_values,
        ),
    ]
