"""Seed Setting for print_defaults.

Creates a singleton Setting record that controls PDF generation defaults:
page size, margins, company header, per-model template selection, etc.
React reads this via wcapi to configure the pdfme form designer and
PDF generation service.
"""
from django.db import migrations, models


PRINT_DEFAULTS_CONFIG = {
    "page": {
        "size": "letter",           # "letter" (215.9x279.4mm) or "a4" (210x297mm)
        "width_mm": 215.9,
        "height_mm": 279.4,
        "margin_mm": {
            "top": 20,
            "right": 20,
            "bottom": 20,
            "left": 20,
        },
        "orientation": "portrait",  # "portrait" or "landscape"
    },
    "company": {
        "name": "",
        "address": "",
        "phone": "",
        "email": "",
        "website": "",
        "tax_id": "",
        "logo_url": "",             # path or URL to company logo image
    },
    "templates": {
        "invoice": {
            "template_id": "invoice",
            "show_logo": True,
            "show_payment_info": True,
            "show_balance": True,
            "footer_text": "",
        },
        "order": {
            "packing_slip_template_id": "order-packing-slip",
            "pull_sheet_template_id": "order-pull-sheet",
            "show_prices_on_packing_slip": False,
            "show_bin_on_pull_sheet": True,
        },
        "purchase": {
            "template_id": "purchase-order",
            "show_conditions": True,
            "show_signature_line": True,
            "default_conditions": "",
        },
        "proposal": {
            "template_id": "invoice",
            "title_override": "PROPOSAL",
            "show_terms_and_conditions": True,
            "validity_days": 30,
        },
    },
    "formatting": {
        "currency_symbol": "$",
        "currency_code": "USD",
        "date_format": "MM/DD/YYYY",
        "number_locale": "en-US",
        "font_family": "",          # blank = pdfme default
        "font_size": 10,
    },
}


def seed_print_defaults(apps, schema_editor):
    Setting = apps.get_model("core", "Setting")

    if Setting.objects.filter(
        name="print_defaults", purpose="print_defaults"
    ).exists():
        return

    Setting.objects.create(
        name="print_defaults",
        purpose="print_defaults",
        is_active=True,
        config=PRINT_DEFAULTS_CONFIG,
    )


def remove_print_defaults(apps, schema_editor):
    Setting = apps.get_model("core", "Setting")
    Setting.objects.filter(
        name="print_defaults", purpose="print_defaults"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_rename_action_to_task"),
    ]

    operations = [
        migrations.AlterField(
            model_name='setting',
            name='purpose',
            field=models.CharField(
                blank=True, null=True, max_length=255,
                choices=[
                    ('', ''), ('view_edit', 'view_edit'), ('constants', 'constants'),
                    ('db_defaults', 'db_defaults'), ('sales_defaults', 'sales_defaults'),
                    ('purchase_defaults', 'purchase_defaults'), ('accounting_defaults', 'accounting_defaults'),
                    ('keywords', 'keywords'), ('search', 'search'),
                    ('workbench_fields', 'workbench_fields'), ('detail_field_access', 'detail_field_access'),
                    ('qa_counters', 'qa_counters'), ('qa_questions', 'qa_questions'),
                    ('admin', 'admin'), ('admin_selectlist', 'admin_selectlist'),
                    ('React_settings', 'React_settings'), ('list_column_config', 'list_column_config'),
                    ('alice_pending', 'alice_pending'), ('alice_log', 'alice_log'),
                    ('field_access', 'field_access'), ('seed', 'seed'),
                    ('alice_coaching', 'alice_coaching'), ('campaign', 'campaign'),
                    ('company_profile', 'company_profile'), ('accounting_interface', 'accounting_interface'),
                    ('wchq_connection', 'wchq_connection'), ('ai_prompt_history', 'ai_prompt_history'),
                    ('calculated_function', 'calculated_function'),
                    ('print_defaults', 'print_defaults'),
                ],
            ),
        ),
        migrations.RunPython(
            seed_print_defaults,
            reverse_code=remove_print_defaults,
        ),
    ]
