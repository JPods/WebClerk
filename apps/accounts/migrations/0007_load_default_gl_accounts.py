"""
Migration: Load Default B2B GL Accounts

This migration loads a standard set of GL accounts into the GlAccount model.
"""

from django.db import migrations


GL_ACCOUNTS = [
    # -----------------------------------------------------------------------
    # ASSETS — Current
    # -----------------------------------------------------------------------
    {
        "account_number": "ASSET-CASH-000",
        "name": "Cash",
        "type": "asset",
        "category": "cash",
        "used_for": "cash",
        "division": 0,
        "comment": "Primary operating cash account.",
        "account_debit": "ASSET-CASH-000",
        "account_credit": "LIAB-ACCTSPAY-000",
    },
    {
        "account_number": "ASSET-PETTY-000",
        "name": "Petty Cash",
        "type": "asset",
        "category": "cash",
        "used_for": "cash",
        "division": 0,
        "comment": "Small on-hand cash fund for minor expenses.",
        "account_debit": "ASSET-PETTY-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "ASSET-AR-000",
        "name": "Accounts Receivable",
        "type": "asset",
        "category": "receivables",
        "used_for": "receivables",
        "division": 0,
        "comment": "Amounts owed by customers for goods/services delivered.",
        "account_debit": "ASSET-AR-000",
        "account_credit": "REV-SALES-000",
    },
    {
        "account_number": "ASSET-AROTHER-000",
        "name": "Other Receivables",
        "type": "asset",
        "category": "receivables",
        "used_for": "receivables",
        "division": 0,
        "comment": "Non-trade receivables (employee advances, deposits, etc.).",
        "account_debit": "ASSET-AROTHER-000",
        "account_credit": "ASSET-CASH-000",
    },
    {
        "account_number": "ASSET-INVENTORY-000",
        "name": "Inventory",
        "type": "asset",
        "category": "inventory",
        "used_for": "inventory",
        "division": 0,
        "comment": "Goods held for sale or use in production.",
        "account_debit": "ASSET-INVENTORY-000",
        "account_credit": "LIAB-ACCTSPAY-000",
    },
    {
        "account_number": "ASSET-PREPAID-000",
        "name": "Prepaid Expenses",
        "type": "asset",
        "category": "receivables",
        "used_for": None,
        "division": 0,
        "comment": "Expenses paid in advance (insurance, subscriptions, rent).",
        "account_debit": "ASSET-PREPAID-000",
        "account_credit": "ASSET-CASH-000",
    },
    # ...existing code from the rest of the GL_ACCOUNTS list...
    {
        "account_number": "EXP-GENERAL-000",
        "name": "General & Administrative",
        "type": "expense",
        "category": "expense",
        "used_for": "expense",
        "division": 0,
        "comment": "Catch-all for overhead expenses not covered by other accounts.",
        "account_debit": "EXP-GENERAL-000",
        "account_credit": "ASSET-CASH-000",
    },
]


def load_gl_accounts(apps, schema_editor):
    GlAccount = apps.get_model("accounts", "GlAccount")
    objs = [GlAccount(**data) for data in GL_ACCOUNTS]
    GlAccount.objects.bulk_create(objs, ignore_conflicts=True)


def unload_gl_accounts(apps, schema_editor):
    GlAccount = apps.get_model("accounts", "GlAccount")
    numbers = [d["account_number"] for d in GL_ACCOUNTS]
    GlAccount.objects.filter(account_number__in=numbers).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_erosion_rename_compare_to_parent"),
    ]

    operations = [
        migrations.RunPython(load_gl_accounts, reverse_code=unload_gl_accounts),
    ]
