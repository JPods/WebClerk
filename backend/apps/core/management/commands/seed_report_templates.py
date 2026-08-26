"""Seed Report model records for the 28 standard report templates.

Each Report record carries:
  - name, description, category, model_name
  - config.template: pdfme template JSON (stub — designer fills in layout)
  - config.data_source: which service/endpoint provides the data
  - config.fields: data fields available for template binding

Usage: ./manage.py seed_report_templates
"""
from django.core.management.base import BaseCommand
from apps.core.models.report import Report


REPORTS = [
    # ── Customer-Facing ──
    {
        'name': 'Invoice',
        'description': 'Customer invoice with line items, totals, and payment terms',
        'category': 'customer_facing',
        'model_name': 'invoice',
        'config': {
            'data_source': 'invoice_detail',
            'fields': ['ida', 'dt_created', 'customer.company', 'customer.address', 'bill_to', 'ship_to',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty', 'lines[].unit_price',
                        'lines[].extended', 'totals.subtotal', 'totals.tax', 'totals.shipping', 'totals.total',
                        'terms', 'due_date', 'notes'],
            'template': {},
        },
    },
    {
        'name': 'Proposal / Quote',
        'description': 'Customer proposal with line items — no AR impact',
        'category': 'customer_facing',
        'model_name': 'proposal',
        'config': {
            'data_source': 'proposal_detail',
            'fields': ['ida', 'dt_created', 'customer.company', 'customer.address',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty', 'lines[].unit_price',
                        'lines[].extended', 'totals.subtotal', 'totals.tax', 'totals.total',
                        'valid_until', 'notes'],
            'template': {},
        },
    },
    {
        'name': 'Order Confirmation',
        'description': 'Customer order confirmation with expected ship date',
        'category': 'customer_facing',
        'model_name': 'order',
        'config': {
            'data_source': 'order_detail',
            'fields': ['ida', 'dt_created', 'customer.company', 'customer.address',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty', 'lines[].unit_price',
                        'lines[].extended', 'totals.total', 'ship_date', 'ship_via', 'notes'],
            'template': {},
        },
    },
    {
        'name': 'Statement',
        'description': 'Customer statement — open invoices, payments, aging, balance',
        'category': 'customer_facing',
        'model_name': 'contact',
        'config': {
            'data_source': 'customer_statement',
            'fields': ['customer.company', 'customer.address', 'customer.phone',
                        'aging.balance_due', 'aging.current', 'aging.past_1_30', 'aging.past_31_60', 'aging.past_61',
                        'lines[].type', 'lines[].number', 'lines[].date', 'lines[].total', 'lines[].balance',
                        'lines[].days', 'lines[].finance'],
            'template': {},
        },
    },
    {
        'name': 'Credit Memo',
        'description': 'Credit note / reversal document with reason',
        'category': 'customer_facing',
        'model_name': 'invoice',
        'config': {
            'data_source': 'invoice_detail',
            'filter': {'invoice_type': 'credit_note'},
            'fields': ['ida', 'dt_created', 'customer.company', 'reason',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty', 'lines[].unit_price',
                        'totals.total'],
            'template': {},
        },
    },
    {
        'name': 'Packing Slip',
        'description': 'Shipment packing list — items and quantities, no prices',
        'category': 'customer_facing',
        'model_name': 'invoice',
        'config': {
            'data_source': 'invoice_detail',
            'hide_prices': True,
            'fields': ['ida', 'dt_created', 'ship_to',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty_shipped',
                        'weight', 'boxes', 'ship_via', 'tracking'],
            'template': {},
        },
    },
    {
        'name': 'Return Receipt',
        'description': 'RMA / return receipt — what was received back',
        'category': 'customer_facing',
        'model_name': 'receipt',
        'config': {
            'data_source': 'receipt_detail',
            'fields': ['ida', 'dt_created', 'customer.company',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty', 'lines[].condition',
                        'reason', 'notes'],
            'template': {},
        },
    },

    # ── Internal Operations ──
    {
        'name': 'Pick List',
        'description': 'Warehouse pick list for order fulfillment',
        'category': 'operations',
        'model_name': 'order',
        'config': {
            'data_source': 'order_pick_list',
            'fields': ['ida', 'customer.company', 'ship_date',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty',
                        'lines[].warehouse', 'lines[].aisle', 'lines[].bin'],
            'template': {},
        },
    },
    {
        'name': 'Purchase Order',
        'description': 'PO sent to vendor — items, quantities, costs',
        'category': 'operations',
        'model_name': 'purchase',
        'config': {
            'data_source': 'purchase_detail',
            'fields': ['ida', 'dt_created', 'vendor.company', 'vendor.address',
                        'lines[].item_ida', 'lines[].vendor_item_num', 'lines[].description',
                        'lines[].qty', 'lines[].unit_cost', 'lines[].extended',
                        'totals.total', 'delivery_date', 'ship_to', 'notes'],
            'template': {},
        },
    },
    {
        'name': 'Work Order',
        'description': 'Work order / job ticket for production or service',
        'category': 'operations',
        'model_name': 'workorder',
        'config': {
            'data_source': 'workorder_detail',
            'fields': ['ida', 'dt_created', 'customer.company', 'status',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty',
                        'lines[].labor_hours', 'lines[].material_cost',
                        'due_date', 'assigned_to', 'notes'],
            'template': {},
        },
    },
    {
        'name': 'BOM Expansion',
        'description': 'Bill of Materials tree — indented components with costs',
        'category': 'operations',
        'model_name': 'item',
        'config': {
            'data_source': 'bom_expand_tree',
            'fields': ['parent.ida', 'parent.name', 'build_qty',
                        'rows[].level', 'rows[].item_ida', 'rows[].description',
                        'rows[].qty_plan', 'rows[].qty_actual', 'rows[].cost_avg',
                        'rows[].cost_extended', 'rows[].is_subassembly',
                        'total_cost'],
            'template': {},
        },
    },
    {
        'name': 'Inventory Count Sheet',
        'description': 'Physical count sheet — blind (no expected qty) or with expected',
        'category': 'operations',
        'model_name': 'inventory_layer',
        'config': {
            'data_source': 'inventory_count_sheet',
            'fields': ['warehouse', 'rows[].item_ida', 'rows[].item_name', 'rows[].lot',
                        'rows[].location.aisle', 'rows[].location.shelf', 'rows[].location.bin',
                        'rows[].qr_code', 'rows[].expected_qty'],
            'template': {},
        },
    },
    {
        'name': 'Serial History',
        'description': 'Serial number lifecycle — all state changes',
        'category': 'operations',
        'model_name': 'serial',
        'config': {
            'data_source': 'serial_history',
            'fields': ['serial_ida', 'item_ida', 'item.name', 'status',
                        'warranty.date_start', 'warranty.date_end',
                        'logs[].action', 'logs[].dt', 'logs[].config'],
            'template': {},
        },
    },
    {
        'name': 'Receiving Report',
        'description': 'Goods received — PO match and variance',
        'category': 'operations',
        'model_name': 'receipt',
        'config': {
            'data_source': 'receipt_detail',
            'fields': ['ida', 'dt_created', 'vendor.company', 'po_ida',
                        'lines[].item_ida', 'lines[].description',
                        'lines[].qty_ordered', 'lines[].qty_received', 'lines[].variance',
                        'notes'],
            'template': {},
        },
    },
    {
        'name': 'Requisition',
        'description': 'Internal purchase request — before PO approval',
        'category': 'operations',
        'model_name': 'requisition',
        'config': {
            'data_source': 'requisition_detail',
            'fields': ['ida', 'dt_created', 'requested_by', 'approved_by',
                        'lines[].item_ida', 'lines[].description', 'lines[].qty',
                        'lines[].estimated_cost', 'reason', 'notes'],
            'template': {},
        },
    },

    # ── Financial / Accounting ──
    {
        'name': 'GL Summary',
        'description': '$ by account code for a period — the retype screen',
        'category': 'accounting',
        'model_name': 'gl_journal',
        'config': {
            'data_source': 'account_summary_by_period',
            'fields': ['period', 'rows[].account', 'rows[].account_name',
                        'rows[].debit', 'rows[].credit', 'rows[].net',
                        'total_debit', 'total_credit', 'balanced'],
            'template': {},
        },
    },
    {
        'name': 'Tax Report',
        'description': 'Sales tax collected by jurisdiction for filing',
        'category': 'accounting',
        'model_name': 'tax_jurisdiction',
        'config': {
            'data_source': 'tax_summary_by_period',
            'fields': ['period_label', 'rows[].jurisdiction', 'rows[].tax_collected',
                        'rows[].invoice_count', 'total_tax', 'total_invoices',
                        'company.name', 'company.tax_id'],
            'template': {},
        },
    },
    {
        'name': 'AR Aging',
        'description': 'Accounts receivable aging by customer',
        'category': 'accounting',
        'model_name': 'contact',
        'config': {
            'data_source': 'ar_aging_by_customer',
            'fields': ['rows[].customer.company', 'rows[].customer.ida',
                        'rows[].current', 'rows[].past_30', 'rows[].past_60', 'rows[].past_90',
                        'rows[].total', 'rows[].days_avg_paid',
                        'totals.current', 'totals.past_30', 'totals.past_60', 'totals.past_90', 'totals.total'],
            'template': {},
        },
    },
    {
        'name': 'AP Aging',
        'description': 'Accounts payable aging by vendor',
        'category': 'accounting',
        'model_name': 'contact',
        'config': {
            'data_source': 'ap_aging_by_vendor',
            'fields': ['rows[].vendor.company', 'rows[].vendor.ida',
                        'rows[].current', 'rows[].past_30', 'rows[].past_60', 'rows[].past_90',
                        'rows[].total'],
            'template': {},
        },
    },
    {
        'name': 'Cash Receipts Journal',
        'description': 'Payments received for a period',
        'category': 'accounting',
        'model_name': 'payment',
        'config': {
            'data_source': 'cash_receipts_journal',
            'fields': ['period', 'rows[].date', 'rows[].customer', 'rows[].invoice_ida',
                        'rows[].amount', 'rows[].method', 'rows[].reference',
                        'total'],
            'template': {},
        },
    },
    {
        'name': 'Sales Journal',
        'description': 'Revenue posted by period',
        'category': 'accounting',
        'model_name': 'gl_journal',
        'config': {
            'data_source': 'sales_journal_detail',
            'fields': ['period', 'rows[].date', 'rows[].invoice_ida', 'rows[].customer',
                        'rows[].account', 'rows[].debit', 'rows[].credit',
                        'total_debit', 'total_credit'],
            'template': {},
        },
    },
    {
        'name': 'Purchase Journal',
        'description': 'AP posted by period',
        'category': 'accounting',
        'model_name': 'gl_journal',
        'config': {
            'data_source': 'purchase_journal_detail',
            'fields': ['period', 'rows[].date', 'rows[].po_ida', 'rows[].vendor',
                        'rows[].account', 'rows[].debit', 'rows[].credit',
                        'total_debit', 'total_credit'],
            'template': {},
        },
    },

    # ── Sales Analysis ──
    {
        'name': 'Sales by Customer',
        'description': 'Revenue, margin, and order count by customer for a period',
        'category': 'sales_analysis',
        'model_name': 'contact',
        'config': {
            'data_source': 'sales_by_customer',
            'fields': ['period', 'rows[].customer.company', 'rows[].customer.ida',
                        'rows[].revenue', 'rows[].cost', 'rows[].margin_pct',
                        'rows[].order_count', 'rows[].invoice_count'],
            'template': {},
        },
    },
    {
        'name': 'Sales by Item',
        'description': 'Qty sold, revenue, margin, and velocity by item',
        'category': 'sales_analysis',
        'model_name': 'item',
        'config': {
            'data_source': 'sales_by_item',
            'fields': ['period', 'rows[].item_ida', 'rows[].name',
                        'rows[].qty_sold', 'rows[].revenue', 'rows[].cost',
                        'rows[].margin_pct', 'rows[].margin_velocity', 'rows[].velocity_category'],
            'template': {},
        },
    },
    {
        'name': 'Sales by Salesperson',
        'description': 'Revenue, margin, and commission by salesperson/rep',
        'category': 'sales_analysis',
        'model_name': 'contact',
        'config': {
            'data_source': 'sales_by_salesperson',
            'fields': ['period', 'rows[].salesperson', 'rows[].revenue', 'rows[].cost',
                        'rows[].margin_pct', 'rows[].commission', 'rows[].order_count'],
            'template': {},
        },
    },
    {
        'name': 'Margin Velocity',
        'description': 'Stars, dead capital, and volume drivers — the velocity report',
        'category': 'sales_analysis',
        'model_name': 'item',
        'config': {
            'data_source': 'velocity_report',
            'fields': ['rows[].item_ida', 'rows[].name', 'rows[].margin_velocity',
                        'rows[].margin_pct', 'rows[].annual_turns', 'rows[].velocity_category',
                        'rows[].qty_on_hand', 'rows[].cost_avg'],
            'template': {},
        },
    },
    {
        'name': 'Campaign ROI',
        'description': 'Campaign spend vs attributed contacts, orders, and revenue',
        'category': 'sales_analysis',
        'model_name': 'campaign',
        'config': {
            'data_source': 'campaign_roi',
            'fields': ['campaign.name', 'campaign.source_type', 'campaign.region',
                        'campaign.spend', 'contacts_attributed', 'orders_attributed',
                        'revenue_attributed', 'roi_pct', 'cost_per_acquisition'],
            'template': {},
        },
    },
    {
        'name': 'Customer Profitability',
        'description': 'Revenue, COGS, margin, and days-to-pay by customer',
        'category': 'sales_analysis',
        'model_name': 'contact',
        'config': {
            'data_source': 'customer_profitability',
            'fields': ['rows[].customer.company', 'rows[].revenue', 'rows[].cogs',
                        'rows[].margin_pct', 'rows[].days_avg_paid', 'rows[].high_credit',
                        'rows[].total_exposure', 'rows[].lifetime_value'],
            'template': {},
        },
    },
]


class Command(BaseCommand):
    help = "Seed 28 standard report templates into the Report model"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for spec in REPORTS:
            ida = f"rpt-{spec['name'].lower().replace(' ', '-').replace('/', '-')}"
            report, was_created = Report.objects.get_or_create(
                ida=ida,
                defaults={
                    'name': spec['name'],
                    'description': spec['description'],
                    'model_name': spec.get('model_name', ''),
                    'category': spec.get('category', ''),
                    'config': spec.get('config', {}),
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {spec['name']}")
            else:
                # Update config fields without overwriting user-designed templates
                config = report.config or {}
                for key in ('data_source', 'fields', 'filter', 'hide_prices'):
                    if key in spec.get('config', {}):
                        config.setdefault(key, spec['config'][key])
                if not config.get('template'):
                    config['template'] = spec.get('config', {}).get('template', {})
                report.config = config
                report.description = spec['description']
                report.category = spec.get('category', report.category)
                report.save(update_fields=['config', 'description', 'category'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created} created, {updated} updated. Total: {len(REPORTS)} reports."
        ))
