"""Seed example letter/email templates as Document records."""

from django.db import migrations


def seed_templates(apps, schema_editor):
    Document = apps.get_model("docs", "Document")

    templates = [
        {
            "ida": "TMPL-COLLECT",
            "name": "Collection Letter",
            "model_name": "template",
            "status": "active",
            "description": "Past-due collection letter for customers with outstanding balances",
            "body": (
                "Dear {{customer.attention}},\n\n"
                "Your account with {{company_name}} has a past due balance of "
                "${{customer.financial.customer.aging.total}}.\n\n"
                "Current: ${{customer.financial.customer.aging.current}}\n"
                "30 days: ${{customer.financial.customer.aging.past_30}}\n"
                "60 days: ${{customer.financial.customer.aging.past_60}}\n"
                "90+ days: ${{customer.financial.customer.aging.past_90}}\n\n"
                "Please remit payment at your earliest convenience.\n\n"
                "Thank you,\n{{company_name}}"
            ),
            "data": {
                "subject": "Past Due Balance Notice — {{customer.name}}",
                "target_model": "invoice",
                "category": "collections",
            },
        },
        {
            "ida": "TMPL-ORDER-CONFIRM",
            "name": "Order Confirmation",
            "model_name": "template",
            "status": "active",
            "description": "Email confirmation sent when an order is placed",
            "body": (
                "Dear {{contact.display_name}},\n\n"
                "Thank you for your order {{record.ida}}.\n\n"
                "Order Total: ${{totals.total}}\n"
                "Status: {{status}}\n\n"
                "We will notify you when your order ships.\n\n"
                "Thank you for your business,\n{{company_name}}"
            ),
            "data": {
                "subject": "Order Confirmation — {{record.ida}}",
                "target_model": "order",
                "category": "transactional",
            },
        },
        {
            "ida": "TMPL-INV-REMINDER",
            "name": "Invoice Reminder",
            "model_name": "template",
            "status": "active",
            "description": "Friendly reminder for an unpaid invoice",
            "body": (
                "Dear {{customer.attention}},\n\n"
                "This is a friendly reminder that invoice {{record.ida}} "
                "with a balance of ${{balance}} is due.\n\n"
                "If payment has already been sent, please disregard this notice.\n\n"
                "Thank you,\n{{company_name}}"
            ),
            "data": {
                "subject": "Invoice Reminder — {{record.ida}}",
                "target_model": "invoice",
                "category": "collections",
            },
        },
        {
            "ida": "TMPL-STATEMENT",
            "name": "Statement Cover Letter",
            "model_name": "template",
            "status": "active",
            "description": "Cover letter for customer account statements",
            "body": (
                "Dear {{customer.attention}},\n\n"
                "Please find enclosed your account statement from {{company_name}}.\n\n"
                "Account Balance: ${{customer.financial.customer.aging.total}}\n\n"
                "If you have any questions regarding your account, "
                "please do not hesitate to contact us.\n\n"
                "Sincerely,\n{{company_name}}"
            ),
            "data": {
                "subject": "Account Statement — {{customer.name}}",
                "target_model": "org",
                "category": "statements",
            },
        },
    ]

    for tmpl in templates:
        # Skip if already exists (idempotent)
        if Document.objects.filter(ida=tmpl["ida"]).exists():
            continue
        Document.objects.create(**tmpl)


def remove_templates(apps, schema_editor):
    Document = apps.get_model("docs", "Document")
    Document.objects.filter(
        ida__in=["TMPL-COLLECT", "TMPL-ORDER-CONFIRM", "TMPL-INV-REMINDER", "TMPL-STATEMENT"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0002_add_is_locked_to_lifecycle"),
    ]

    operations = [
        migrations.RunPython(seed_templates, remove_templates),
    ]
