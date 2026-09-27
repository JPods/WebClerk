"""
seed_reports — Seed example Report records for every model.

Usage:
    ./bin/python manage.py seed_reports
    ./bin/python manage.py seed_reports --force   # overwrite existing

Each model gets a curated set of reports that represent real business
documents users would print, email, or export. These serve as examples
and can be customized per deployment.
"""
from django.core.management.base import BaseCommand
from apps.core.models.report import Report


REPORTS = [
    # ── Orders ──
    {'target_model': 'order', 'name': 'Order Confirmation', 'description': 'Standard order confirmation for customer', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'order_confirmation', 'route': '/transactions/order/print/{id}'}},
    {'target_model': 'order', 'name': 'Pick / Pull Request', 'description': 'Warehouse picking list with bin locations and quantities', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'pick_request'}},
    {'target_model': 'order', 'name': 'Packing Slip', 'description': 'Packing slip for shipping — no prices, quantities only', 'output_type': 'print', 'category': 'report', 'sort_order': 3, 'config': {'template': 'packing_slip'}},
    {'target_model': 'order', 'name': 'Proforma Invoice', 'description': 'Proforma invoice for customs and international shipping', 'output_type': 'print', 'category': 'report', 'sort_order': 4, 'config': {'template': 'proforma_invoice'}},
    {'target_model': 'order', 'name': 'Order Acknowledgement Email', 'description': 'Email confirmation sent to customer on order entry', 'output_type': 'email', 'category': 'letter', 'sort_order': 10, 'config': {'template': 'order_ack_email'}},
    {'target_model': 'order', 'name': 'Order Line Export', 'description': 'CSV export of order lines with item details', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'order_lines_csv'}},
    {'target_model': 'order', 'name': 'Shipping Label', 'description': 'Shipping label with barcode for carrier', 'output_type': 'label', 'category': 'label', 'sort_order': 30, 'config': {'template': 'shipping_label'}},

    # ── Invoices ──
    {'target_model': 'invoice', 'name': 'Invoice', 'description': 'Standard invoice with line items, totals, and cash terms', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'invoice', 'route': '/transactions/invoice/print/{id}'}},
    {'target_model': 'invoice', 'name': 'Credit Memo', 'description': 'Credit memo for returned goods or price adjustments', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'credit_memo'}},
    {'target_model': 'invoice', 'name': 'Past Due Notice', 'description': 'Past due cash reminder with aging details', 'output_type': 'print', 'category': 'statement', 'sort_order': 3, 'config': {'template': 'past_due_notice'}},
    {'target_model': 'invoice', 'name': 'Invoice Email', 'description': 'Email invoice to customer with PDF attachment', 'output_type': 'email', 'category': 'letter', 'sort_order': 10, 'config': {'template': 'invoice_email'}},
    {'target_model': 'invoice', 'name': 'Invoice Line Export', 'description': 'CSV export of invoice lines', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'invoice_lines_csv'}},

    # ── Quotes ──
    {'target_model': 'quote', 'name': 'Quote / Quote', 'description': 'Sales quote with pricing, terms, and acceptance signature', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'quote', 'route': '/transactions/quote/print/{id}'}},
    {'target_model': 'quote', 'name': 'Estimate', 'description': 'Estimate without binding terms — for budgeting purposes', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'estimate'}},
    {'target_model': 'quote', 'name': 'Bid Document', 'description': 'Formal bid response with specifications and pricing', 'output_type': 'print', 'category': 'report', 'sort_order': 3, 'config': {'template': 'bid_document'}},
    {'target_model': 'quote', 'name': 'Quote Email', 'description': 'Email quote to customer for review', 'output_type': 'email', 'category': 'letter', 'sort_order': 10, 'config': {'template': 'quote_email'}},

    # ── Purchases ──
    {'target_model': 'purchase', 'name': 'Purchase Order', 'description': 'Purchase order sent to vendor', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'purchase_order'}},
    {'target_model': 'purchase', 'name': 'Receiving Report', 'description': 'Receiving checklist — quantities received vs ordered', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'receiving_report'}},
    {'target_model': 'purchase', 'name': 'PO Email to Vendor', 'description': 'Email PO to vendor with PDF attachment', 'output_type': 'email', 'category': 'letter', 'sort_order': 10, 'config': {'template': 'po_email'}},
    {'target_model': 'purchase', 'name': 'Purchase Line Export', 'description': 'CSV export of PO lines', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'purchase_lines_csv'}},

    # ── Work Orders ──
    {'target_model': 'workorder', 'name': 'Work Order', 'description': 'Work order with task list, materials, and labor', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'work_order'}},
    {'target_model': 'workorder', 'name': 'Service Report', 'description': 'Completed service report with findings and recommendations', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'service_report'}},
    {'target_model': 'workorder', 'name': 'Time & Materials Summary', 'description': 'Summary of labor hours and materials used', 'output_type': 'print', 'category': 'summary', 'sort_order': 3, 'config': {'template': 'time_materials'}},

    # ── Customers ──
    {'target_model': 'customer', 'name': 'Customer Statement', 'description': 'Account statement with open invoices and aging', 'output_type': 'print', 'category': 'statement', 'sort_order': 1, 'config': {'template': 'customer_statement'}},
    {'target_model': 'customer', 'name': 'Customer Profile', 'description': 'Customer profile with contact info, addresses, and history', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'customer_profile'}},
    {'target_model': 'customer', 'name': 'Aging Report', 'description': 'Accounts receivable aging by customer', 'output_type': 'print', 'category': 'report', 'sort_order': 3, 'config': {'template': 'ar_aging'}},
    {'target_model': 'customer', 'name': 'Customer List Export', 'description': 'CSV export of customer records', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'customer_export'}},
    {'target_model': 'customer', 'name': 'Mailing Labels', 'description': 'Address labels for mailing (Avery 5160)', 'output_type': 'label', 'category': 'label', 'sort_order': 30, 'config': {'template': 'mailing_labels'}},

    # ── Vendors ──
    {'target_model': 'vendor', 'name': 'Vendor Profile', 'description': 'Vendor profile with contact info and purchase history', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'vendor_profile'}},
    {'target_model': 'vendor', 'name': 'Vendor Statement', 'description': 'Accounts payable statement for vendor', 'output_type': 'print', 'category': 'statement', 'sort_order': 2, 'config': {'template': 'vendor_statement'}},
    {'target_model': 'vendor', 'name': 'Vendor List Export', 'description': 'CSV export of vendor records', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'vendor_export'}},
    {'target_model': 'vendor', 'name': 'AP Aging Report', 'description': 'Accounts payable aging by vendor', 'output_type': 'print', 'category': 'report', 'sort_order': 3, 'config': {'template': 'ap_aging'}},

    # ── Items / Products ──
    {'target_model': 'item', 'name': 'Product Spec Sheet', 'description': 'Product specification sheet with pricing and details', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'product_spec'}},
    {'target_model': 'item', 'name': 'Price List', 'description': 'Price list by product line or category', 'output_type': 'print', 'category': 'list', 'sort_order': 2, 'config': {'template': 'price_list'}},
    {'target_model': 'item', 'name': 'Inventory Report', 'description': 'Current inventory levels by warehouse', 'output_type': 'print', 'category': 'report', 'sort_order': 3, 'config': {'template': 'inventory_report'}},
    {'target_model': 'item', 'name': 'Item Barcode Labels', 'description': 'Barcode labels for inventory items', 'output_type': 'label', 'category': 'label', 'sort_order': 30, 'config': {'template': 'item_barcode'}},
    {'target_model': 'item', 'name': 'Item Catalog Export', 'description': 'Full product catalog CSV export', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'item_export'}},
    {'target_model': 'item', 'name': 'Reorder Report', 'description': 'Items below reorder point', 'output_type': 'print', 'category': 'report', 'sort_order': 4, 'config': {'template': 'reorder_report'}},

    # ── Bill of Material ──
    {'target_model': 'bill_of_material', 'name': 'BOM Report', 'description': 'Bill of material with component list, quantities, and costs', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'bom_report'}},
    {'target_model': 'bill_of_material', 'name': 'Where-Used Report', 'description': 'Where a component is used across assemblies', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'where_used'}},

    # ── Contacts ──
    {'target_model': 'contact', 'name': 'Contact Directory', 'description': 'Contact directory with phone, email, and address', 'output_type': 'print', 'category': 'list', 'sort_order': 1, 'config': {'template': 'contact_directory'}},
    {'target_model': 'contact', 'name': 'Contact Export', 'description': 'CSV export of contacts for mail merge', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'contact_export'}},

    # ── Actions / Tasks ──
    {'target_model': 'action', 'name': 'Task List', 'description': 'Open tasks by project and priority', 'output_type': 'print', 'category': 'list', 'sort_order': 1, 'config': {'template': 'task_list'}},
    {'target_model': 'action', 'name': 'Project Status Report', 'description': 'Project progress with burndown and completion %', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'project_status'}},

    # ── GL / Accounting ──
    {'target_model': 'gl_account', 'name': 'Chart of Accounts', 'description': 'Complete chart of accounts listing', 'output_type': 'print', 'category': 'list', 'sort_order': 1, 'config': {'template': 'chart_of_accounts'}},
    {'target_model': 'gl_journal', 'name': 'Journal Entry Report', 'description': 'Journal entries by date range and source', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'journal_entries'}},
    {'target_model': 'ledger', 'name': 'AR Aging Summary', 'description': 'Accounts receivable aging summary (current/30/60/90+)', 'output_type': 'print', 'category': 'summary', 'sort_order': 1, 'config': {'template': 'ar_aging_summary'}},
    {'target_model': 'ledger', 'name': 'AP Aging Summary', 'description': 'Accounts payable aging summary', 'output_type': 'print', 'category': 'summary', 'sort_order': 2, 'config': {'template': 'ap_aging_summary'}},
    {'target_model': 'ledger', 'name': 'Open Receivables', 'description': 'List of all open receivable records', 'output_type': 'print', 'category': 'list', 'sort_order': 3, 'config': {'template': 'open_receivables'}},

    # ── Cash ──
    {'target_model': 'cash', 'name': 'Cash Receipt', 'description': 'Cash receipt for customer', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'cash_receipt'}},
    {'target_model': 'cash', 'name': 'Cash Journal', 'description': 'Cash journal by date range', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'cash_journal'}},
    {'target_model': 'cash', 'name': 'Disbursement Report', 'description': 'AP disbursements by vendor and date', 'output_type': 'print', 'category': 'report', 'sort_order': 3, 'config': {'template': 'disbursement_report'}},

    # ── QA / Inspections ──
    {'target_model': 'question_answer', 'name': 'Condition Report', 'description': 'QA condition report with photos and answers', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'condition_report', 'route': '/transactions/qa/print/{parent_model}/{parent_id}'}},
    {'target_model': 'question_answer', 'name': 'Inspection Checklist', 'description': 'Blank inspection checklist for field use', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'inspection_checklist'}},
    {'target_model': 'question_answer', 'name': 'QA Summary Export', 'description': 'CSV export of QA responses', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'qa_export'}},

    # ── Warehouse ──
    {'target_model': 'warehouse', 'name': 'Warehouse Inventory', 'description': 'Inventory levels by warehouse and bin location', 'output_type': 'print', 'category': 'report', 'sort_order': 1, 'config': {'template': 'warehouse_inventory'}},
    {'target_model': 'warehouse', 'name': 'Cycle Count Sheet', 'description': 'Blank cycle count sheet for physical inventory', 'output_type': 'print', 'category': 'report', 'sort_order': 2, 'config': {'template': 'cycle_count'}},

    # ── Documents ──
    {'target_model': 'document', 'name': 'Document Index', 'description': 'Index of all documents by category', 'output_type': 'print', 'category': 'list', 'sort_order': 1, 'config': {'template': 'document_index'}},

    # ── Alice AI / Escalation ──
    {'target_model': 'alice_observation', 'name': 'Escalation Log', 'description': 'All AI escalations — Alice to Claude API or WCHQ, with confidence scores and reasons', 'output_type': 'screen', 'category': 'report', 'sort_order': 1, 'config': {'template': 'escalation_log', 'filters': {'category': 'escalation'}}},
    {'target_model': 'alice_observation', 'name': 'Escalation Summary', 'description': 'Weekly escalation summary — count by tier, average confidence, top question patterns', 'output_type': 'screen', 'category': 'summary', 'sort_order': 2, 'config': {'template': 'escalation_summary', 'filters': {'category': 'escalation'}, 'group_by': 'tier'}},
    {'target_model': 'alice_observation', 'name': 'Alice Pattern Report', 'description': 'Patterns, anomalies, and coaching suggestions detected by Alice', 'output_type': 'screen', 'category': 'report', 'sort_order': 3, 'config': {'template': 'alice_patterns', 'filters': {'category__in': ['pattern', 'anomaly', 'coaching']}}},
    {'target_model': 'alice_observation', 'name': 'Observation Export', 'description': 'CSV export of all Alice observations', 'output_type': 'export', 'category': 'export', 'sort_order': 20, 'config': {'template': 'alice_observation_export'}},
]


class Command(BaseCommand):
    help = 'Seed Report records — example reports for every model'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing and re-seed')

    def handle(self, *args, **options):
        if options.get('force'):
            deleted, _ = Report.objects.filter(purpose='seed').delete()
            self.stdout.write(f'Deleted {deleted} existing seed reports')

        created = skipped = 0
        for r in REPORTS:
            exists = Report.objects.filter(
                target_model=r['target_model'],
                name=r['name'],
            ).exists()
            if exists:
                skipped += 1
                continue

            Report.objects.create(
                name=r['name'],
                description=r.get('description', ''),
                purpose='seed',
                target_model=r['target_model'],
                output_type=r.get('output_type', 'print'),
                category=r.get('category', 'report'),
                sort_order=r.get('sort_order', 0),
                config=r.get('config', {}),
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Reports: {created} created, {skipped} already exist'))
