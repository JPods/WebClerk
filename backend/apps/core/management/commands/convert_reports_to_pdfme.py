"""Convert print reports to pdfme templates.

Creates a copy of each print report with output_type='pdfme' and a best-effort
pdfme template in config.pdfme_template. Originals are untouched.

Usage: ./manage.py convert_reports_to_pdfme
       ./manage.py convert_reports_to_pdfme --report 407   # one report
       ./manage.py convert_reports_to_pdfme --dry-run      # preview only
"""
from django.core.management.base import BaseCommand
from apps.core.models.report import Report
import json


# US Letter: 215.9mm x 279.4mm. pdfme uses mm.
PAGE_W = 210
PAGE_H = 297
MARGIN = 14
CONTENT_W = PAGE_W - 2 * MARGIN

# Standard pdfme field positions for commerce documents
COMPANY_HEADER = [
    {'name': 'company_name', 'type': 'text', 'position': {'x': MARGIN, 'y': 10},
     'width': 120, 'height': 10, 'fontSize': 18, 'fontWeight': 'bold', 'fontColor': '#1a1a1a'},
    {'name': 'company_address', 'type': 'text', 'position': {'x': MARGIN, 'y': 22},
     'width': 120, 'height': 8, 'fontSize': 9, 'fontColor': '#555555'},
    {'name': 'company_phone', 'type': 'text', 'position': {'x': MARGIN, 'y': 30},
     'width': 120, 'height': 8, 'fontSize': 9, 'fontColor': '#555555'},
]

DOCUMENT_TITLE = [
    {'name': 'document_title', 'type': 'text', 'position': {'x': 150, 'y': 10},
     'width': 46, 'height': 12, 'fontSize': 20, 'fontWeight': 'bold',
     'fontColor': '#1a1a1a', 'alignment': 'right'},
    {'name': 'document_number', 'type': 'text', 'position': {'x': 150, 'y': 24},
     'width': 46, 'height': 8, 'fontSize': 10, 'alignment': 'right'},
    {'name': 'document_date', 'type': 'text', 'position': {'x': 150, 'y': 32},
     'width': 46, 'height': 8, 'fontSize': 9, 'fontColor': '#555555', 'alignment': 'right'},
]

BILL_TO = [
    {'name': 'bill_to_label', 'type': 'text', 'position': {'x': MARGIN, 'y': 52},
     'width': 40, 'height': 7, 'fontSize': 9, 'fontWeight': 'bold'},
    {'name': 'bill_to_company', 'type': 'text', 'position': {'x': MARGIN, 'y': 59},
     'width': 80, 'height': 7, 'fontSize': 10},
    {'name': 'bill_to_attention', 'type': 'text', 'position': {'x': MARGIN, 'y': 66},
     'width': 80, 'height': 7, 'fontSize': 9},
    {'name': 'bill_to_address', 'type': 'text', 'position': {'x': MARGIN, 'y': 73},
     'width': 80, 'height': 14, 'fontSize': 9, 'fontColor': '#333333'},
]

SHIP_TO = [
    {'name': 'ship_to_label', 'type': 'text', 'position': {'x': 110, 'y': 52},
     'width': 40, 'height': 7, 'fontSize': 9, 'fontWeight': 'bold'},
    {'name': 'ship_to_company', 'type': 'text', 'position': {'x': 110, 'y': 59},
     'width': 80, 'height': 7, 'fontSize': 10},
    {'name': 'ship_to_attention', 'type': 'text', 'position': {'x': 110, 'y': 66},
     'width': 80, 'height': 7, 'fontSize': 9},
    {'name': 'ship_to_address', 'type': 'text', 'position': {'x': 110, 'y': 73},
     'width': 80, 'height': 14, 'fontSize': 9, 'fontColor': '#333333'},
]

VENDOR_BLOCK = [
    {'name': 'vendor_label', 'type': 'text', 'position': {'x': MARGIN, 'y': 52},
     'width': 40, 'height': 7, 'fontSize': 9, 'fontWeight': 'bold'},
    {'name': 'vendor_company', 'type': 'text', 'position': {'x': MARGIN, 'y': 59},
     'width': 80, 'height': 7, 'fontSize': 10},
    {'name': 'vendor_attention', 'type': 'text', 'position': {'x': MARGIN, 'y': 66},
     'width': 80, 'height': 7, 'fontSize': 9},
    {'name': 'vendor_address', 'type': 'text', 'position': {'x': MARGIN, 'y': 73},
     'width': 80, 'height': 14, 'fontSize': 9, 'fontColor': '#333333'},
]

LINE_ITEMS = [
    {'name': 'line_items_header', 'type': 'text', 'position': {'x': MARGIN, 'y': 92},
     'width': CONTENT_W, 'height': 7, 'fontSize': 8, 'fontWeight': 'bold',
     'fontColor': '#ffffff', 'backgroundColor': '#333333'},
    {'name': 'line_items', 'type': 'text', 'position': {'x': MARGIN, 'y': 100},
     'width': CONTENT_W, 'height': 140, 'fontSize': 9, 'fontColor': '#333333'},
]

TOTALS = [
    {'name': 'subtotal_label', 'type': 'text', 'position': {'x': 130, 'y': 245},
     'width': 30, 'height': 7, 'fontSize': 9, 'alignment': 'right'},
    {'name': 'subtotal', 'type': 'text', 'position': {'x': 162, 'y': 245},
     'width': 34, 'height': 7, 'fontSize': 9, 'alignment': 'right'},
    {'name': 'tax_label', 'type': 'text', 'position': {'x': 130, 'y': 253},
     'width': 30, 'height': 7, 'fontSize': 9, 'alignment': 'right'},
    {'name': 'tax', 'type': 'text', 'position': {'x': 162, 'y': 253},
     'width': 34, 'height': 7, 'fontSize': 9, 'alignment': 'right'},
    {'name': 'total_label', 'type': 'text', 'position': {'x': 130, 'y': 261},
     'width': 30, 'height': 8, 'fontSize': 11, 'fontWeight': 'bold', 'alignment': 'right'},
    {'name': 'total', 'type': 'text', 'position': {'x': 162, 'y': 261},
     'width': 34, 'height': 8, 'fontSize': 11, 'fontWeight': 'bold', 'alignment': 'right'},
]

FOOTER = [
    {'name': 'notes', 'type': 'text', 'position': {'x': MARGIN, 'y': 272},
     'width': 120, 'height': 14, 'fontSize': 8, 'fontColor': '#666666'},
    {'name': 'terms', 'type': 'text', 'position': {'x': MARGIN, 'y': 286},
     'width': CONTENT_W, 'height': 6, 'fontSize': 7, 'fontColor': '#999999'},
]

# ── Template builders per document type ──

TEMPLATES = {
    'invoice': {
        'title': 'INVOICE',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + SHIP_TO + LINE_ITEMS + TOTALS + FOOTER,
    },
    'credit_memo': {
        'title': 'CREDIT MEMO',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + SHIP_TO + LINE_ITEMS + TOTALS + FOOTER,
    },
    'order': {
        'title': 'ORDER CONFIRMATION',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + SHIP_TO + LINE_ITEMS + TOTALS + FOOTER,
    },
    'proposal': {
        'title': 'PROPOSAL',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + SHIP_TO + LINE_ITEMS + TOTALS + FOOTER,
    },
    'purchase': {
        'title': 'PURCHASE ORDER',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + VENDOR_BLOCK + SHIP_TO + LINE_ITEMS + TOTALS + FOOTER,
    },
    'pick_ticket': {
        'title': 'PICK TICKET',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + SHIP_TO + LINE_ITEMS,
    },
    'packing_slip': {
        'title': 'PACKING SLIP',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + SHIP_TO + LINE_ITEMS,
    },
    'receiving': {
        'title': 'RECEIVING REPORT',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + VENDOR_BLOCK + LINE_ITEMS,
    },
    'payment_receipt': {
        'title': 'PAYMENT RECEIPT',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + [
            {'name': 'payment_method', 'type': 'text', 'position': {'x': 110, 'y': 52},
             'width': 80, 'height': 7, 'fontSize': 9, 'fontWeight': 'bold'},
            {'name': 'payment_amount', 'type': 'text', 'position': {'x': 110, 'y': 59},
             'width': 80, 'height': 10, 'fontSize': 14, 'fontWeight': 'bold'},
            {'name': 'applied_invoices', 'type': 'text', 'position': {'x': MARGIN, 'y': 92},
             'width': CONTENT_W, 'height': 100, 'fontSize': 9},
        ] + FOOTER,
    },
    'statement': {
        'title': 'STATEMENT OF ACCOUNT',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + [
            {'name': 'aging_header', 'type': 'text', 'position': {'x': MARGIN, 'y': 92},
             'width': CONTENT_W, 'height': 7, 'fontSize': 8, 'fontWeight': 'bold',
             'fontColor': '#ffffff', 'backgroundColor': '#333333'},
            {'name': 'aging_buckets', 'type': 'text', 'position': {'x': MARGIN, 'y': 100},
             'width': CONTENT_W, 'height': 14, 'fontSize': 9},
            {'name': 'open_invoices_header', 'type': 'text', 'position': {'x': MARGIN, 'y': 120},
             'width': CONTENT_W, 'height': 7, 'fontSize': 8, 'fontWeight': 'bold',
             'fontColor': '#ffffff', 'backgroundColor': '#555555'},
            {'name': 'open_invoices', 'type': 'text', 'position': {'x': MARGIN, 'y': 128},
             'width': CONTENT_W, 'height': 120, 'fontSize': 9},
        ] + TOTALS + FOOTER,
    },
    'aging': {
        'title': 'AGING REPORT',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + [
            {'name': 'aging_summary', 'type': 'text', 'position': {'x': MARGIN, 'y': 52},
             'width': CONTENT_W, 'height': 20, 'fontSize': 10},
            {'name': 'detail_header', 'type': 'text', 'position': {'x': MARGIN, 'y': 78},
             'width': CONTENT_W, 'height': 7, 'fontSize': 8, 'fontWeight': 'bold',
             'fontColor': '#ffffff', 'backgroundColor': '#333333'},
            {'name': 'detail_lines', 'type': 'text', 'position': {'x': MARGIN, 'y': 86},
             'width': CONTENT_W, 'height': 180, 'fontSize': 9},
        ] + FOOTER,
    },
    'requisition': {
        'title': 'REQUISITION',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + LINE_ITEMS + FOOTER,
    },
    'workorder': {
        'title': 'WORK ORDER',
        'fields': COMPANY_HEADER + DOCUMENT_TITLE + BILL_TO + LINE_ITEMS + FOOTER,
    },
}

# Map report names to template keys
REPORT_NAME_MAP = {
    'Invoice': 'invoice',
    'Credit Memo': 'credit_memo',
    'Order Confirmation': 'order',
    'Proposal': 'proposal',
    'Purchase Order': 'purchase',
    'Pick Ticket': 'pick_ticket',
    'Packing Slip': 'packing_slip',
    'Receiving Report': 'receiving',
    'Payment Receipt': 'payment_receipt',
    'Statement': 'statement',
    'Aging Report': 'aging',
    'Requisition': 'requisition',
    'Work Order': 'workorder',
}


def build_pdfme_template(template_key: str) -> dict:
    """Build a pdfme-compatible template dict."""
    spec = TEMPLATES.get(template_key)
    if not spec:
        return {}

    return {
        'basePdf': '__BLANK_PDF__',  # Placeholder — React resolves to BLANK_PDF at runtime
        'schemas': [spec['fields']],
        'title': spec['title'],
        'pageSize': {'width': PAGE_W, 'height': PAGE_H},
    }


class Command(BaseCommand):
    help = "Convert print reports to pdfme templates (creates copies, originals untouched)"

    def add_arguments(self, parser):
        parser.add_argument('--report', type=int, help='Convert one report by ID')
        parser.add_argument('--dry-run', action='store_true', help='Preview only, no database changes')

    def handle(self, *args, **options):
        target_id = options.get('report')
        dry_run = options.get('dry_run', False)

        qs = Report.objects.filter(output_type='print', is_active=True, is_deleted=False)
        if target_id:
            qs = qs.filter(id=target_id)

        reports = qs.order_by('model_name', 'name')
        created = 0
        skipped = 0

        for report in reports:
            template_key = REPORT_NAME_MAP.get(report.name)
            if not template_key:
                self.stdout.write(self.style.WARNING(
                    f'  SKIP #{report.id} {report.name} — no template mapping'
                ))
                skipped += 1
                continue

            # Check if pdfme copy already exists
            existing = Report.objects.filter(
                model_name=report.model_name,
                name=f'{report.name} (pdfme)',
                is_deleted=False,
            ).exists()
            if existing:
                self.stdout.write(self.style.NOTICE(
                    f'  EXISTS #{report.id} {report.name} — pdfme copy already exists'
                ))
                skipped += 1
                continue

            pdfme_template = build_pdfme_template(template_key)

            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f'  WOULD CREATE: {report.name} (pdfme) — '
                    f'{len(pdfme_template.get("schemas", [[]])[0])} fields'
                ))
                continue

            # Create the pdfme copy
            new_config = dict(report.config or {})
            new_config['pdfme_template'] = pdfme_template
            new_config['source_report_id'] = report.id

            new_report = Report.objects.create(
                name=f'{report.name} (pdfme)',
                description=f'pdfme version of {report.name}. Customize in PDF Designer.',
                model_name=report.model_name,
                output_type='print',
                category=report.category,
                role_required=report.role_required,
                sort_order=report.sort_order + 100,
                config=new_config,
                script_before=report.script_before,
                script_during=report.script_during,
                script_after=report.script_after,
            )

            created += 1
            field_count = len(pdfme_template.get('schemas', [[]])[0])
            self.stdout.write(self.style.SUCCESS(
                f'  CREATED #{new_report.id} {new_report.name} — '
                f'{field_count} pdfme fields, source: #{report.id}'
            ))

        self.stdout.write(f'\nCreated: {created}, Skipped: {skipped}')
