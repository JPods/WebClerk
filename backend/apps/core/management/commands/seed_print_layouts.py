"""Seed config.form PrintLayout JSON on Report records.

Writes the PrintLayout sections array into each Report's config.form,
which the new panel-based designer reads and the UniversalPrint renderer
uses for print output.

Usage: ./manage.py seed_print_layouts
       ./manage.py seed_print_layouts --dry-run
       ./manage.py seed_print_layouts --force   (overwrite existing config.form)
"""
from django.core.management.base import BaseCommand
from apps.core.models import Report


# ── Shared building blocks ──────────────────────────────────────────

COMPANY_HEADER = {"type": "company_header", "logo": True, "show_address": True, "show_contact": True}
COMPANY_HEADER_COMPACT = {"type": "company_header", "logo": True, "show_address": False, "show_contact": False}
COMMENTS = {"type": "comments", "source": "comments.public", "label": "Comments"}
CONDITIONS = {"type": "conditions", "source": "conditions_description"}


def sell_addresses(info_title, info_label):
    return {"type": "address_blocks", "columns": [
        {"title": "Bill To", "fields": [
            {"field": "attention", "label": "Attn"},
            {"field": "company", "label": "Company"},
            {"field": "address_full", "label": "Address"},
        ]},
        {"title": "Ship To", "fields": [
            {"field": "config.ship_to.company", "label": "Company"},
            {"field": "config.ship_to.attention", "label": "Attn"},
            {"field": "config.ship_to.address1", "label": "Address"},
        ]},
        {"title": info_title, "fields": [
            {"field": "ida", "label": f"{info_label} #"},
            {"field": "status", "label": "Status"},
            {"field": "dt_created", "label": "Date", "format": "date"},
            {"field": "terms", "label": "Terms"},
            {"field": "price_level", "label": "Price Level"},
        ]},
    ]}


def sell_lines(qty_field="quantity.active", qty_label="Qty"):
    return {"type": "line_items", "show_footer_totals": True, "columns": [
        {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "15%"},
        {"field": "item.description", "label": "Description", "align": "left", "width": "35%"},
        {"field": qty_field, "label": qty_label, "align": "right", "format": "number"},
        {"field": "price.unit", "label": "Unit Price", "align": "right", "format": "currency"},
        {"field": "price.extended", "label": "Extended", "align": "right", "format": "currency"},
    ]}


def cost_lines(qty_field="quantity.staged", qty_label="Qty"):
    return {"type": "line_items", "show_footer_totals": True, "columns": [
        {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "15%"},
        {"field": "item.description", "label": "Description", "align": "left", "width": "35%"},
        {"field": qty_field, "label": qty_label, "align": "right", "format": "number"},
        {"field": "cost.unit", "label": "Unit Cost", "align": "right", "format": "currency"},
        {"field": "cost.extended", "label": "Extended", "align": "right", "format": "currency"},
    ]}


STANDARD_TOTALS = {"type": "totals", "left_text": "Thank you for your business.", "rows": [
    {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
    {"field": "totals.tax", "label": "Tax", "format": "currency"},
    {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
    {"field": "totals.total", "label": "Total", "format": "currency", "bold": True},
]}


# ── Layouts keyed by Report id ─────────────────────────────────────

REPORT_LAYOUTS = {

    # --- ORDER ---

    411: {  # Order Confirmation
        "model": "order", "title": "Order Confirmation", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            sell_addresses("Order Info", "Order"),
            COMMENTS,
            sell_lines("quantity.staged", "Qty Ordered"),
            STANDARD_TOTALS,
            CONDITIONS,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Order #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },

    412: {  # Pick Ticket — no prices, has bin location
        "model": "order", "title": "Pick Ticket", "paper": "letter",
        "sections": [
            COMPANY_HEADER_COMPACT,
            {"type": "meta_row", "fields": [
                {"field": "ida", "label": "Order #"},
                {"field": "company", "label": "Customer"},
                {"field": "dt_created", "label": "Date", "format": "date"},
                {"field": "status", "label": "Status"},
            ]},
            {"type": "address_blocks", "columns": [
                {"title": "Ship To", "fields": [
                    {"field": "config.ship_to.company", "label": "Company"},
                    {"field": "config.ship_to.attention", "label": "Attn"},
                    {"field": "config.ship_to.address1", "label": "Address"},
                ]},
            ]},
            {"type": "line_items", "show_footer_totals": False, "columns": [
                {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "20%"},
                {"field": "item.description", "label": "Description", "align": "left", "width": "35%"},
                {"field": "item.bin", "label": "Bin", "align": "left", "width": "15%"},
                {"field": "quantity.staged", "label": "Qty", "align": "right", "format": "number"},
                {"field": "physical.weight", "label": "Weight", "align": "right", "format": "number"},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Order #"},
            ]},
        ],
    },

    413: {  # Packing Slip — no prices
        "model": "order", "title": "Packing Slip", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Ship To", "fields": [
                    {"field": "config.ship_to.company", "label": "Company"},
                    {"field": "config.ship_to.attention", "label": "Attn"},
                    {"field": "config.ship_to.address1", "label": "Address"},
                ]},
                {"title": "Order Info", "fields": [
                    {"field": "ida", "label": "Order #"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                    {"field": "config.ship_via", "label": "Ship Via"},
                ]},
            ]},
            {"type": "line_items", "show_footer_totals": False, "columns": [
                {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "20%"},
                {"field": "item.description", "label": "Description", "align": "left", "width": "50%"},
                {"field": "quantity.active", "label": "Qty Shipped", "align": "right", "format": "number"},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Order #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },

    # --- INVOICE ---

    407: {  # Invoice
        "model": "invoice", "title": "Invoice", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            sell_addresses("Invoice Info", "Invoice"),
            COMMENTS,
            sell_lines(),
            {"type": "totals", "left_text": "Thank you for your business.", "rows": [
                {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
                {"field": "totals.tax", "label": "Tax", "format": "currency"},
                {"field": "totals.shipping", "label": "Shipping", "format": "currency"},
                {"field": "totals.total", "label": "Total", "format": "currency", "bold": True},
                {"field": "totals.balance", "label": "Balance Due", "format": "currency", "bold": True},
            ]},
            CONDITIONS,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Invoice #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },

    408: {  # Credit Memo
        "model": "invoice", "title": "Credit Memo", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Bill To", "fields": [
                    {"field": "attention", "label": "Attn"},
                    {"field": "company", "label": "Company"},
                    {"field": "address_full", "label": "Address"},
                ]},
                {"title": "Credit Memo Info", "fields": [
                    {"field": "ida", "label": "Credit Memo #"},
                    {"field": "status", "label": "Status"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                ]},
            ]},
            {"type": "comments", "source": "comments.public", "label": "Reason"},
            sell_lines(),
            {"type": "totals", "rows": [
                {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
                {"field": "totals.tax", "label": "Tax", "format": "currency"},
                {"field": "totals.total", "label": "Credit Total", "format": "currency", "bold": True},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Credit Memo #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },

    # --- PROPOSAL ---

    416: {  # Proposal
        "model": "proposal", "title": "Proposal", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Prepared For", "fields": [
                    {"field": "attention", "label": "Attn"},
                    {"field": "company", "label": "Company"},
                    {"field": "address_full", "label": "Address"},
                ]},
                {"title": "Proposal Info", "fields": [
                    {"field": "ida", "label": "Proposal #"},
                    {"field": "status", "label": "Status"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                    {"field": "terms", "label": "Terms"},
                ]},
            ]},
            COMMENTS,
            sell_lines("quantity.staged", "Qty"),
            STANDARD_TOTALS,
            CONDITIONS,
            {"type": "signature", "preamble": "Accepted and agreed:", "blocks": [
                {"label": "Customer Signature", "lines": ["Signature", "Printed Name", "Date"]},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Proposal #"},
            ]},
        ],
    },

    # --- PURCHASE ---

    414: {  # Purchase Order
        "model": "purchase", "title": "Purchase Order", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Vendor", "fields": [
                    {"field": "attention", "label": "Attn"},
                    {"field": "company", "label": "Company"},
                    {"field": "address_full", "label": "Address"},
                ]},
                {"title": "Ship To", "fields": [
                    {"field": "config.ship_to.company", "label": "Company"},
                    {"field": "config.ship_to.attention", "label": "Attn"},
                    {"field": "config.ship_to.address1", "label": "Address"},
                ]},
                {"title": "PO Info", "fields": [
                    {"field": "ida", "label": "PO #"},
                    {"field": "status", "label": "Status"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                    {"field": "terms", "label": "Terms"},
                    {"field": "config.ship_via", "label": "Ship Via"},
                ]},
            ]},
            COMMENTS,
            cost_lines(),
            {"type": "totals", "rows": [
                {"field": "totals.subtotal", "label": "Subtotal", "format": "currency"},
                {"field": "totals.total", "label": "Total", "format": "currency", "bold": True},
            ]},
            CONDITIONS,
            {"type": "footer", "fields": [
                {"field": "ida", "label": "PO #"},
            ]},
        ],
    },

    415: {  # Receiving Report
        "model": "purchase", "title": "Receiving Report", "paper": "letter",
        "sections": [
            COMPANY_HEADER_COMPACT,
            {"type": "meta_row", "fields": [
                {"field": "ida", "label": "PO #"},
                {"field": "company", "label": "Vendor"},
                {"field": "dt_created", "label": "PO Date", "format": "date"},
                {"field": "status", "label": "Status"},
            ]},
            {"type": "line_items", "show_footer_totals": False, "columns": [
                {"field": "item.ida_item", "label": "Item #", "align": "left", "width": "20%"},
                {"field": "item.description", "label": "Description", "align": "left", "width": "35%"},
                {"field": "quantity.staged", "label": "Ordered", "align": "right", "format": "number"},
                {"field": "quantity.active", "label": "Received", "align": "right", "format": "number"},
                {"field": "cost.unit", "label": "Unit Cost", "align": "right", "format": "currency"},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "PO #"},
            ]},
        ],
    },

    # --- PAYMENT ---

    419: {  # Payment Receipt
        "model": "payment", "title": "Payment Receipt", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Received From", "fields": [
                    {"field": "attention", "label": "Attn"},
                    {"field": "company", "label": "Company"},
                    {"field": "address_full", "label": "Address"},
                ]},
                {"title": "Payment Info", "fields": [
                    {"field": "ida", "label": "Receipt #"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                    {"field": "config.payment_method", "label": "Method"},
                    {"field": "config.reference", "label": "Reference"},
                ]},
            ]},
            {"type": "detail_fields", "fields": [
                {"field": "totals.total", "label": "Amount Received", "format": "currency"},
            ]},
            {"type": "totals", "left_text": "Thank you for your payment.", "rows": [
                {"field": "totals.total", "label": "Total Received", "format": "currency", "bold": True},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Receipt #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },

    # --- CUSTOMER ---

    409: {  # Statement
        "model": "customer", "title": "Statement", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Account", "fields": [
                    {"field": "attention", "label": "Attn"},
                    {"field": "company", "label": "Company"},
                    {"field": "address_full", "label": "Address"},
                ]},
                {"title": "Statement Info", "fields": [
                    {"field": "ida", "label": "Account #"},
                    {"field": "aging.balance_due", "label": "Balance Due", "format": "currency"},
                    {"field": "terms", "label": "Terms"},
                ]},
            ]},
            {"type": "data_table", "grand_totals": True, "columns": [
                {"field": "ida", "label": "Invoice #", "align": "left", "width": "15%"},
                {"field": "dt_created", "label": "Date", "align": "left", "format": "date", "width": "12%"},
                {"field": "terms", "label": "Terms", "align": "left", "width": "12%"},
                {"field": "totals.total", "label": "Amount", "align": "right", "format": "currency"},
                {"field": "totals.balance", "label": "Balance", "align": "right", "format": "currency"},
            ]},
            {"type": "totals", "rows": [
                {"field": "aging.current", "label": "Current", "format": "currency"},
                {"field": "aging.past_1_30", "label": "1-30 Days", "format": "currency"},
                {"field": "aging.past_31_60", "label": "31-60 Days", "format": "currency"},
                {"field": "aging.past_61", "label": "61+ Days", "format": "currency"},
                {"field": "aging.balance_due", "label": "Total Due", "format": "currency", "bold": True},
            ]},
            {"type": "conditional_text", "source": "statement.comments"},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Account #"},
                {"field": "company", "label": "Customer"},
            ]},
        ],
    },

    410: {  # Aging Report
        "model": "customer", "title": "Aging Report", "paper": "letter",
        "sections": [
            COMPANY_HEADER_COMPACT,
            {"type": "data_table", "grand_totals": True, "group_by": "rep",
             "group_label": "Rep", "group_subtotals": True, "columns": [
                {"field": "ida", "label": "Account #", "align": "left", "width": "12%"},
                {"field": "company", "label": "Customer", "align": "left", "width": "25%"},
                {"field": "aging.current", "label": "Current", "align": "right", "format": "currency"},
                {"field": "aging.past_1_30", "label": "1-30", "align": "right", "format": "currency"},
                {"field": "aging.past_31_60", "label": "31-60", "align": "right", "format": "currency"},
                {"field": "aging.past_61", "label": "61+", "align": "right", "format": "currency"},
                {"field": "aging.balance_due", "label": "Total", "align": "right", "format": "currency"},
            ]},
            {"type": "footer", "fields": [
                {"field": "dt_created", "label": "Report Date", "format": "date"},
            ]},
        ],
    },

    # --- REQUISITION ---

    417: {  # Requisition
        "model": "requisition", "title": "Requisition", "paper": "letter",
        "sections": [
            COMPANY_HEADER_COMPACT,
            {"type": "meta_row", "fields": [
                {"field": "ida", "label": "Requisition #"},
                {"field": "status", "label": "Status"},
                {"field": "dt_created", "label": "Date", "format": "date"},
                {"field": "company", "label": "Requested By"},
            ]},
            {"type": "comments", "source": "comments.public", "label": "Justification"},
            cost_lines(),
            {"type": "totals", "rows": [
                {"field": "totals.total", "label": "Estimated Total", "format": "currency", "bold": True},
            ]},
            {"type": "signature", "preamble": "Approval:", "blocks": [
                {"label": "Approved By", "lines": ["Signature", "Date"]},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "Req #"},
            ]},
        ],
    },

    # --- WORK ORDER ---

    418: {  # Work Order
        "model": "workorder", "title": "Work Order", "paper": "letter",
        "sections": [
            COMPANY_HEADER,
            {"type": "address_blocks", "columns": [
                {"title": "Customer", "fields": [
                    {"field": "attention", "label": "Attn"},
                    {"field": "company", "label": "Company"},
                    {"field": "address_full", "label": "Address"},
                ]},
                {"title": "Work Order Info", "fields": [
                    {"field": "ida", "label": "WO #"},
                    {"field": "status", "label": "Status"},
                    {"field": "dt_created", "label": "Date", "format": "date"},
                    {"field": "config.priority", "label": "Priority"},
                    {"field": "config.deadline", "label": "Due", "format": "date"},
                ]},
            ]},
            {"type": "detail_fields", "fields": [
                {"field": "description", "label": "Description"},
            ]},
            COMMENTS,
            cost_lines(),
            {"type": "totals", "rows": [
                {"field": "totals.materials", "label": "Materials", "format": "currency"},
                {"field": "totals.labor", "label": "Labor", "format": "currency"},
                {"field": "totals.total", "label": "Total", "format": "currency", "bold": True},
            ]},
            {"type": "signature", "preamble": "Work completed and accepted:", "blocks": [
                {"label": "Technician", "lines": ["Signature", "Date"]},
                {"label": "Customer", "lines": ["Signature", "Date"]},
            ]},
            {"type": "footer", "fields": [
                {"field": "ida", "label": "WO #"},
                {"field": "customer_id", "label": "Customer #"},
            ]},
        ],
    },
}

# Dunning messages for Statement — stored in config.statement.comments
STATEMENT_COMMENTS = [
    {"when": "aging.past_61 > 0",   "text": "FINAL NOTICE: Your account is over 90 days past due. Immediate payment is required to avoid collection action.", "style": "bold"},
    {"when": "aging.past_31_60 > 0", "text": "Your account is seriously past due. Please contact us immediately to arrange payment."},
    {"when": "aging.past_1_30 > 0",  "text": "Your account is past due. Please remit payment at your earliest convenience."},
    {"default": True,                "text": "Thank you for your continued business and prompt payment."},
]

# Map of report_id → extra config keys to set (beyond config.form)
EXTRA_CONFIG = {
    409: {"statement": {"comments": STATEMENT_COMMENTS}},
}


class Command(BaseCommand):
    help = "Seed config.form PrintLayout JSON on Report records"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change')
        parser.add_argument('--force', action='store_true', help='Overwrite existing config.form')

    def handle(self, *args, **options):
        dry = options['dry_run']
        force = options['force']
        updated = skipped = missing = 0

        for report_id, layout in REPORT_LAYOUTS.items():
            try:
                report = Report.objects.get(id=report_id, is_deleted=False)
                config = report.config or {}

                if 'form' in config and not force:
                    skipped += 1
                    self.stdout.write(f'  {report.name}: skipped (has form, use --force)')
                    continue

                section_types = [s['type'] for s in layout['sections']]

                if dry:
                    self.stdout.write(f'  [dry] {report.name}: {len(layout["sections"])} sections — {", ".join(section_types)}')
                else:
                    config['form'] = layout
                    # Merge extra config (e.g. statement.comments dunning messages)
                    if report_id in EXTRA_CONFIG:
                        config.update(EXTRA_CONFIG[report_id])
                    report.config = config
                    report.save(update_fields=['config', 'dt_modified'])
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {report.name}: {len(layout["sections"])} sections'))
                updated += 1

            except Report.DoesNotExist:
                missing += 1
                self.stdout.write(self.style.WARNING(f'  ✗ id={report_id} not found'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ id={report_id}: {e}'))

        verb = 'would update' if dry else 'updated'
        self.stdout.write(f'\n{verb} {updated}, skipped {skipped}, missing {missing} (of {len(REPORT_LAYOUTS)} reports)')
