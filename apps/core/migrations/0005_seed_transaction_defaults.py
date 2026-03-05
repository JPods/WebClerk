"""Seed singleton Setting for transaction_defaults / React_settings.

Creates a single Setting record that React reads on startup to populate
default field values when creating new transactions (orders, invoices, etc.).
"""
from django.db import migrations


def seed_transaction_defaults(apps, schema_editor):
    Setting = apps.get_model("core", "Setting")

    # Idempotent: skip if already exists
    if Setting.objects.filter(
        name="transaction_defaults", purpose="React_settings"
    ).exists():
        return

    Setting.objects.create(
        name="transaction_defaults",
        purpose="React_settings",
        is_active=True,
        data={
            "terms": "On Order",
            "due_date_period": 1,          # days to add to dt
            "price_level": "retail",
            "priority": "standard",
        },
    )


def remove_transaction_defaults(apps, schema_editor):
    Setting = apps.get_model("core", "Setting")
    Setting.objects.filter(
        name="transaction_defaults", purpose="React_settings"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_alter_setting_purpose"),
    ]

    operations = [
        migrations.RunPython(
            seed_transaction_defaults,
            reverse_code=remove_transaction_defaults,
        ),
    ]
