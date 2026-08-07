"""Seed print_layout Settings for transaction models.

These JSON layouts drive the UniversalPrint renderer in React2025.
Alice can draft new layouts from user-uploaded PDF/image examples;
users tweak field mappings in the DataBrowser Setting editor.

Usage: ./manage.py seed_print_layouts
       ./manage.py seed_print_layouts --model order
       ./manage.py seed_print_layouts --force   (overwrite existing)
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


# ── Shared building blocks ──────────────────────────────────────────

COMPANY_HEADER = {"type": "company_header", "logo": True, "show_address": True, "show_contact": True}

SELL_ADDRESSES = {
    "type": "address_blocks",
    "columns": [
        {
            "title": "Bill To",
            "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
                {"field": "email", "label": "Email"},
            ],
        },
        {
            "title": "Ship To",
            "fields": [
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.address1", "label": "Address"},
                {"field": "config.ship_to.city_state_zip", "label": "City/State"},
                {"field": "ship_via", "label": "Ship Via"},
            ],
        },
    ],
}

EXEC_ADDRESSES = {
    "type": "address_blocks",
    "columns": [
        {
            "title": "Vendor",
            "fields": [
                {"field": "attention", "label": "Attn"},
                {"field": "company", "label": "Company"},
                {"field": "address_full", "label": "Address"},
                {"field": "phone", "label": "Phone"},
                {"field": "email", "label": "Email"},
            ],
        },
        {
            "title": "Ship To",
            "fields": [
                {"field": "config.ship_to.company", "label": "Company"},
                {"field": "config.ship_to.address1", "label": "Address"},
            ],
        },
    ],
}

SELL_LINE_ITEMS = {
    "type": "line_items",
    "columns": [
        {"field": "item.ida_item", "label": "Item", "align": "left"},
        {"field": "item.description", "label": "Description", "align": "left", "width": "40%"},
        {"field": "quantity.active", "label": "Qty", "align": "right"},
        {"field": "price.unit", "label": "Unit Price", "align": "right", "format": "currency"},
        {"field": "price.extended", "label": "Extended", "align": "right", "format": "currency"},
    ],
    "show_footer_totals": True,
}

EXEC_LINE_ITEMS = {
    "type": "line_items",
    "columns": [
        {"field": "item.ida_item", "label": "Item", "align": "left"},
        {"field": "item.description", "label": "Description", "align": "left", "width": "40%"},
        {"field": "quantity.active", "label": "Qty", "align": "right"},
        {"field": "cost.unit", "label": "Unit Cost", "align": "right", "format": "currency"},
        {"field": "cost.extended", "label": "Extended", "align": "right", "format": "currency"},
    ],
    "show_footer_totals": True,
}

STANDARD_TOTALS = {
    "type": "totals",
    "rows": [
        {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
        {"field": "totals.tax", "label": "Tax", "format": "currency"},
        {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
        {"field": "totals.total", "label": "Total", "format": "currency", "style": "bold"},
    ],
    "left_text": "Thank you for your business.",
}

CONDITIONS = {"type": "conditions", "source": "conditions_description"}
COMMENTS = {"type": "comments", "source": "comments.public", "label": "Comments"}

SELL_SIGNATURE = {
    "type": "signature",
    "preamble": "By signing below, the customer accepts the terms and conditions of this document.",
    "blocks": [
        {"label": "Customer", "lines": ["Signature", "Date"]},
        {"label": "Authorized By", "lines": ["Signature", "Date"]},
    ],
}


# ── Per-model layouts ───────────────────────────────────────────────

def _order_info_col(title, model_label):
    return {
        "title": title,
        "fields": [
            {"field": "ida", "label": f"{model_label} #"},
            {"field": "status", "label": "Status"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "dt_needed", "label": "Need By", "format": "date"},
            {"field": "terms", "label": "Terms"},
            {"field": "price_level", "label": "Price Level"},
            {"field": "priority", "label": "Priority"},
        ],
    }


PRINT_LAYOUTS = {
    "order": {
        "model": "order",
        "family": "sell",
        "paper": "letter",
        "title": "Order",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {**SELL_ADDRESSES, "columns": [*SELL_ADDRESSES["columns"], _order_info_col("Order Info", "Order")]},
            {"type": "meta_row", "fields": [
                {"field": "source.campaign_name", "label": "Cust PO#"},
                {"field": "customer_id", "label": "Account"},
            ]},
            COMMENTS,
            SELL_LINE_ITEMS,
            STANDARD_TOTALS,
            CONDITIONS,
            SELL_SIGNATURE,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Order #"},
                {"field": "customer_id", "label": "Customer #"},
                {"field": "source.campaign_name", "label": "PO #"},
            ]},
        ],
    },

    "invoice": {
        "model": "invoice",
        "family": "sell",
        "paper": "letter",
        "title": "Invoice",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {**SELL_ADDRESSES, "columns": [*SELL_ADDRESSES["columns"], _order_info_col("Invoice Info", "Invoice")]},
            COMMENTS,
            SELL_LINE_ITEMS,
            {**STANDARD_TOTALS, "rows": [
                *STANDARD_TOTALS["rows"],
                {"field": "totals.amount_paid", "label": "Amount Paid", "format": "currency"},
                {"field": "balance", "label": "Balance Due", "format": "currency", "style": "bold"},
            ]},
            CONDITIONS,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Invoice #"},
                {"field": "customer_id", "label": "Customer #"},
                {"field": "dt_created", "label": "Date", "format": "date"},
            ]},
        ],
    },

    "proposal": {
        "model": "proposal",
        "family": "sell",
        "paper": "letter",
        "title": "Proposal",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {**SELL_ADDRESSES, "columns": [*SELL_ADDRESSES["columns"], _order_info_col("Proposal Info", "Proposal")]},
            COMMENTS,
            SELL_LINE_ITEMS,
            STANDARD_TOTALS,
            CONDITIONS,
            SELL_SIGNATURE,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Proposal #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },

    "purchase": {
        "model": "purchase",
        "family": "exec",
        "paper": "letter",
        "title": "Purchase Order",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {**EXEC_ADDRESSES, "columns": [*EXEC_ADDRESSES["columns"], {
                "title": "PO Info",
                "fields": [
                    {"field": "ida", "label": "PO #"},
                    {"field": "status", "label": "Status"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                    {"field": "dt_needed", "label": "Need By", "format": "date"},
                    {"field": "terms", "label": "Terms"},
                ],
            }]},
            COMMENTS,
            EXEC_LINE_ITEMS,
            STANDARD_TOTALS,
            CONDITIONS,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "PO #"},
                {"field": "vendor_id", "label": "Vendor #"},
            ]},
        ],
    },

    "work_order": {
        "model": "work_order",
        "family": "exec",
        "paper": "letter",
        "title": "Work Order",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {
                    "title": "Customer",
                    "fields": [
                        {"field": "attention", "label": "Attn"},
                        {"field": "company", "label": "Company"},
                        {"field": "address_full", "label": "Address"},
                        {"field": "phone", "label": "Phone"},
                    ],
                },
                {
                    "title": "Work Order Info",
                    "fields": [
                        {"field": "ida", "label": "WO #"},
                        {"field": "status", "label": "Status"},
                        {"field": "dt_created", "label": "Date", "format": "date"},
                        {"field": "dt_needed", "label": "Need By", "format": "date"},
                        {"field": "priority", "label": "Priority"},
                    ],
                },
            ]},
            COMMENTS,
            EXEC_LINE_ITEMS,
            STANDARD_TOTALS,
            SELL_SIGNATURE,
        ],
    },

    "receipt": {
        "model": "receipt",
        "family": "exec",
        "paper": "letter",
        "title": "Receipt",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {**EXEC_ADDRESSES, "columns": [*EXEC_ADDRESSES["columns"], {
                "title": "Receipt Info",
                "fields": [
                    {"field": "ida", "label": "Receipt #"},
                    {"field": "status", "label": "Status"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                ],
            }]},
            EXEC_LINE_ITEMS,
            STANDARD_TOTALS,
        ],
    },

    "requisition": {
        "model": "requisition",
        "family": "exec",
        "paper": "letter",
        "title": "Requisition",
        "version": 1,
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {
                    "title": "Requested By",
                    "fields": [
                        {"field": "attention", "label": "Name"},
                        {"field": "department", "label": "Department"},
                        {"field": "phone", "label": "Phone"},
                    ],
                },
                {
                    "title": "Requisition Info",
                    "fields": [
                        {"field": "ida", "label": "Req #"},
                        {"field": "status", "label": "Status"},
                        {"field": "dt_created", "label": "Date", "format": "date"},
                        {"field": "dt_needed", "label": "Need By", "format": "date"},
                        {"field": "priority", "label": "Priority"},
                    ],
                },
            ]},
            COMMENTS,
            EXEC_LINE_ITEMS,
            STANDARD_TOTALS,
            {
                "type": "signature",
                "preamble": "Approval signatures required before purchase.",
                "blocks": [
                    {"label": "Requested By", "lines": ["Signature", "Date"]},
                    {"label": "Approved By", "lines": ["Signature", "Date"]},
                ],
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Seed print_layout Settings for transaction models"

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, help='Seed only this model')
        parser.add_argument('--force', action='store_true', help='Overwrite existing layouts')

    def handle(self, *args, **options):
        target = options.get('model')
        force = options.get('force', False)
        created = updated = skipped = 0

        for model_name, config in PRINT_LAYOUTS.items():
            if target and model_name != target:
                continue

            existing = Setting.objects.filter(
                purpose='print_layout',
                parent_model=model_name,
            ).first()

            if existing and not force:
                skipped += 1
                self.stdout.write(f'  {model_name}: skipped (exists)')
                continue

            if existing:
                existing.config = config
                existing.save()
                updated += 1
                self.stdout.write(f'  {model_name}: updated ({len(config["sections"])} sections)')
            else:
                Setting.objects.create(
                    name=f'print_layout:{model_name}',
                    ida=f'print-layout-{model_name}',
                    parent_model=model_name,
                    purpose='print_layout',
                    config=config,
                )
                created += 1
                self.stdout.write(f'  {model_name}: created ({len(config["sections"])} sections)')

        self.stdout.write(self.style.SUCCESS(
            f'Print layouts: {created} created, {updated} updated, {skipped} skipped'
        ))
