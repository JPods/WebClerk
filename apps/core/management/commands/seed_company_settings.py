"""Seed the company profile Setting record.

Creates a Setting with purpose='company_profile' that holds:
  - Company name, address, phone, email, website
  - Logo paths for various uses (letterhead, invoice, email, favicon)
  - Certificate/document paths
  - Tax IDs, registration numbers
  - Default formatting for printed documents

Usage: ./manage.py seed_company_settings
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


COMPANY_PROFILE_CONFIG = {
    "company": {
        "name": "",
        "legal_name": "",
        "tagline": "",
        "address": {
            "street1": "",
            "street2": "",
            "city": "",
            "state": "",
            "zip": "",
            "country": "US",
        },
        "phone": "",
        "fax": "",
        "email": "",
        "website": "",
        "tax_id": "",
        "registration_number": "",
    },
    "logos": {
        "primary": "",           # main logo — used on letterhead, invoices, reports
        "icon": "",              # square icon — used as favicon, app icon
        "email_banner": "",      # wide banner for email headers
        "watermark": "",         # light/transparent version for document backgrounds
        "dark_theme": "",        # logo variant for dark backgrounds
    },
    "documents": {
        "letterhead_template": "",   # path or Document id for letterhead
        "invoice_template": "",
        "po_template": "",
        "proposal_template": "",
        "statement_template": "",
        "packing_slip_template": "",
    },
    "certificates": {
        # paths or Document ids for certificates, licenses, insurance
        # key = purpose, value = path/url/document_id
    },
    "print_defaults": {
        "paper_size": "letter",      # letter, a4
        "margin_top": 1.0,          # inches
        "margin_bottom": 0.75,
        "margin_left": 0.75,
        "margin_right": 0.75,
        "font_family": "Helvetica",
        "font_size": 10,
        "show_logo": True,
        "show_address": True,
        "show_phone": True,
        "show_email": True,
        "show_website": True,
        "show_tax_id": False,
        "footer_text": "",
    },
    "accounting": {
        "package": "",               # quickbooks, sage, xero, manual
        "export_format": "csv",      # csv, json, quickbooks_iif, tab
        "default_division": "",
        "fiscal_year_end_month": 12,
        "fiscal_year_end_day": 31,
    },
    "alice_coaching": {
        "wchq_level": "receive_only",  # none, receive_only, send_only, full
        "manufacturer_reporting": "none",  # none, aggregate_only, full
    },
}


class Command(BaseCommand):
    help = "Seed the company profile Setting record"

    def handle(self, *args, **options):
        setting, created = Setting.objects.get_or_create(
            purpose='company_profile',
            parent_model='setting',
            defaults={
                'ida': 'company-profile',
                'config': COMPANY_PROFILE_CONFIG,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created company_profile Setting #{setting.id}"))
        else:
            # Merge new keys without overwriting existing values
            config = setting.config or {}
            for section, defaults in COMPANY_PROFILE_CONFIG.items():
                if section not in config:
                    config[section] = defaults
                elif isinstance(defaults, dict) and isinstance(config[section], dict):
                    for key, val in defaults.items():
                        if key not in config[section]:
                            config[section][key] = val
            setting.config = config
            setting.save(update_fields=['config'])
            self.stdout.write(self.style.SUCCESS(f"Updated company_profile Setting #{setting.id} (merged new keys)"))
