# Data migration: update stored model_name values in ledger entries
# - "purchase_order" → "purchase"
# - "sales_order" → "order"  (if any legacy data)

from django.db import migrations


def update_ledger_model_names(apps, schema_editor):
    """Update model_name column in Ledger table."""
    Ledger = apps.get_model("accounts", "Ledger")
    renames = {
        "purchase_order": "purchase",
        "sales_order": "order",
    }
    for old_val, new_val in renames.items():
        Ledger.objects.filter(model_name=old_val).update(model_name=new_val)


def reverse_ledger_model_names(apps, schema_editor):
    """Reverse: restore old model_name values."""
    Ledger = apps.get_model("accounts", "Ledger")
    renames = {
        "purchase": "purchase_order",
        "order": "sales_order",
    }
    for old_val, new_val in renames.items():
        Ledger.objects.filter(model_name=old_val).update(model_name=new_val)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_audit_gljournal_taxjurisdiction_ledger"),
    ]

    operations = [
        migrations.RunPython(
            update_ledger_model_names,
            reverse_code=reverse_ledger_model_names,
        ),
    ]
