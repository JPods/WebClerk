"""
Seed print layouts for aged receivables report and customer statement.

Creates Setting records with purpose='wc:print_layout' that drive UniversalPrint.

Usage:
    ./bin/python manage.py seed_receivables_layouts
    ./bin/python manage.py seed_receivables_layouts --force
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


AGING_COLUMNS = [
    {"field": "future", "label": "Future", "align": "right", "format": "currency"},
    {"field": "current", "label": "Current", "align": "right", "format": "currency"},
    {"field": "period_1", "label": "1-30 Days\nPast Due", "align": "right", "format": "currency"},
    {"field": "period_2", "label": "31-60 Days\nPast Due", "align": "right", "format": "currency"},
    {"field": "period_3", "label": "61+ Days\nPast Due", "align": "right", "format": "currency"},
]


# ── Aged Receivables Report (internal) ────────────────────────────────

AGED_RECEIVABLES_LAYOUT = {
    "model": "aged_receivables",
    "family": "report",
    "paper": "letter",
    "orientation": "landscape",
    "title": "Receivable Report",
    "version": 1,
    "data_url": "/wcapi/reports/aged_receivables/",
    "sections": [
        {
            "type": "report_header",
            "title": "Receivable Report",
            "show_date": True,
            "show_company": True,
        },
        {
            "type": "grouped_line_items",
            "group_by": "customer",
            "group_header": {
                "layout": "two_column",
                "left": [
                    {"field": "name", "label": "Name"},
                    {"field": "company", "label": "Name"},
                ],
                "right": [
                    {"field": "phone", "label": "Phone"},
                    {"field": "fax", "label": "FAX"},
                ],
                "summary": [
                    {"field": "balance_due", "label": "Balance Due", "format": "currency"},
                    {"field": "open_orders", "label": "Open Orders", "format": "currency"},
                    {"field": "summary", "label": "Summary", "format": "currency"},
                ],
            },
            "columns": [
                {"field": "type", "label": "Type", "align": "left", "width": "5%"},
                {"field": "number", "label": "Number", "align": "left", "width": "10%"},
                {"field": "date", "label": "Date", "align": "left", "format": "date", "width": "8%"},
                {"field": "original", "label": "Original", "align": "right", "format": "currency"},
                {"field": "balance", "label": "Balance Due", "align": "right", "format": "currency"},
                {"field": "future", "label": "Future", "align": "right", "format": "currency"},
                {"field": "current", "label": "Current", "align": "right", "format": "currency"},
                {"field": "period_1", "label": "Past Due 1", "align": "right", "format": "currency"},
                {"field": "period_2", "label": "Past Due 2", "align": "right", "format": "currency"},
                {"field": "period_3", "label": "Past Due 3", "align": "right", "format": "currency"},
            ],
            "show_group_totals": True,
        },
        {
            "type": "report_footer",
            "show_grand_totals": True,
            "total_columns": [
                {"field": "balance_due", "label": "Balance Due", "format": "currency"},
                {"field": "future", "label": "Future", "format": "currency"},
                {"field": "current", "label": "Current", "format": "currency"},
                {"field": "period_1", "label": "Past Due 1", "format": "currency"},
                {"field": "period_2", "label": "Past Due 2", "format": "currency"},
                {"field": "period_3", "label": "Past Due 3", "format": "currency"},
            ],
        },
    ],
}


# ── Customer Statement (customer-facing, one per customer) ────────────

STATEMENT_LAYOUT = {
    "model": "statement",
    "family": "statement",
    "paper": "letter",
    "orientation": "portrait",
    "title": "Statement",
    "version": 1,
    "data_url": "/wcapi/reports/statement/{customer_id}/",
    "page_break": "per_customer",
    "sections": [
        {
            "type": "company_header",
            "logo": True,
            "show_address": False,
            "show_contact": False,
            "title": "Statement:",
            "show_date": True,
            "subtitle_field": "company",
        },
        {
            "type": "address_blocks",
            "columns": [
                {
                    "title": "",
                    "fields": [
                        {"field": "attention", "label": "Attention:", "bold_label": True},
                        {"field": "company", "label": "Company:", "bold_label": True},
                        {"field": "address_full", "label": ""},
                        {"field": "phone", "label": "Phone:", "bold_label": True},
                        {"field": "fax", "label": "Fax:", "bold_label": True},
                    ],
                },
                {
                    "title": "",
                    "sections": [
                        {
                            "type": "text_block",
                            "field": "heading",
                            "style": "italic",
                        },
                        {
                            "type": "response_area",
                            "title": "Response Area",
                            "options": [
                                "The check is in the mail.",
                                "I don't have copies of invoices. (\\u2713 needed invoices)",
                                "Payment is due to be mailed on ____________.",
                                "Other:",
                            ],
                            "lines_after": 3,
                        },
                    ],
                },
            ],
        },
        {
            "type": "aging_summary",
            "label": "Totals:",
            "columns": [
                {"field": "balance_due", "label": "Balance Due", "format": "currency"},
                {"field": "current", "label": "Current", "format": "currency"},
                {"field": "period_1", "label": "1 to 30 Days\nPast Due", "format": "currency"},
                {"field": "period_2", "label": "31 to 60 Days\nPast Due", "format": "currency"},
                {"field": "period_3", "label": "61+ Days\nPast Due", "format": "currency"},
            ],
        },
        {
            "type": "line_items",
            "title": "Transaction Details:",
            "separator": "- - - - - - - - - - Transaction - - - - - - - - - -",
            "columns": [
                {"field": "type", "label": "Type", "align": "left", "width": "5%"},
                {"field": "number", "label": "Number", "align": "left", "width": "10%"},
                {"field": "date", "label": "Date", "align": "left", "format": "date", "width": "8%"},
                {"field": "original", "label": "Total", "align": "right", "format": "currency"},
                {"field": "balance", "label": "Balance", "align": "right", "format": "currency"},
                {"field": "current", "label": "Current", "align": "right", "format": "currency"},
                {"field": "period_1", "label": "1 to 30 Days\nPast Due", "align": "right", "format": "currency"},
                {"field": "period_2", "label": "31 to 60 Days\nPast Due", "align": "right", "format": "currency"},
                {"field": "period_3", "label": "61+ Days\nPast Due", "align": "right", "format": "currency"},
                {"field": "finance", "label": "Finance", "align": "right", "format": "currency"},
                {"field": "days", "label": "Days", "align": "right"},
            ],
            "show_footer_totals": True,
        },
        {
            "type": "text_block",
            "field": "closing",
            "style": "italic",
            "margin_top": "1em",
        },
    ],
}


class Command(BaseCommand):
    help = 'Seed print layouts for aged receivables report and customer statement'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing')

    def handle(self, *args, **options):
        force = options.get('force', False)
        layouts = [
            ('aged_receivables', 'Aged Receivables Report', AGED_RECEIVABLES_LAYOUT),
            ('statement', 'Customer Statement', STATEMENT_LAYOUT),
        ]

        for model_key, name, layout in layouts:
            existing = Setting.objects.filter(
                parent_model=model_key, purpose='wc:print_layout',
            ).first()

            if existing and not force:
                self.stdout.write(f'  {model_key}: already exists (use --force)')
                continue

            if existing:
                existing.config = layout
                existing.name = name
                existing.save()
                self.stdout.write(f'  {model_key}: updated')
            else:
                Setting.objects.create(
                    name=name,
                    parent_model=model_key,
                    purpose='wc:print_layout',
                    scope='system',
                    config=layout,
                )
                self.stdout.write(f'  {model_key}: created')

        self.stdout.write(self.style.SUCCESS('Receivables print layouts seeded'))
