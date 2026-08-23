"""
seed_display_layouts — Create wc:detail_layout Settings for transaction models.

Defines the db.display layout: header cards, line items, tabs.
Cards reference fields from the print template (Order Confirmation, Report id=411).

Usage:
    ./bin/python manage.py seed_display_layouts
    ./bin/python manage.py seed_display_layouts --force   # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


# ── Card definitions (reusable across models) ──────────────────────────

BILL_TO_CARD = {
    'title': 'Bill To',
    'title_ida': 'customer_id',
    'component': 'customer_search',
    'fields': [
        {'field': 'company', 'label': 'Company'},
        {'field': 'phone', 'label': 'Phone'},
        {'field': 'attention', 'label': 'Attn'},
        {'field': 'address_full', 'label': 'Address'},
        {'field': 'email', 'label': 'Email'},
    ],
    'footer': 'action_summary',
}

SHIP_TO_CARD = {
    'title': 'Ship To',
    'fields': [
        {'field': 'config.ship_to.company', 'label': 'Company'},
        {'field': 'config.ship_to.attention', 'label': 'Attn'},
        {'field': 'config.ship_to.phone', 'label': 'Phone'},
        {'field': 'config.ship_to.address_full', 'label': 'Address'},
    ],
}

# ── Per-model transaction detail cards ─────────────────────────────────

ORDER_INFO_CARD = {
    'title': 'Order',
    'fields': [
        {'field': 'type_sale', 'label': 'Type Sale', 'type': 'select'},
        {'field': 'terms', 'label': 'Terms'},
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date Ord'},
        {'field': 'dt_needed', 'label': 'Need By'},
        {'field': 'price_level', 'label': 'Price Level'},
        {'field': 'ship_via', 'label': 'Ship Via'},
        {'field': 'priority', 'label': 'Priority'},
    ],
}

INVOICE_INFO_CARD = {
    'title': 'Invoice',
    'fields': [
        {'field': 'type_sale', 'label': 'Type Sale', 'type': 'select'},
        {'field': 'terms', 'label': 'Terms'},
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date'},
        {'field': 'dt_needed', 'label': 'Due Date'},
        {'field': 'price_level', 'label': 'Price Level'},
        {'field': 'ship_via', 'label': 'Ship Via'},
    ],
}

PROPOSAL_INFO_CARD = {
    'title': 'Proposal',
    'fields': [
        {'field': 'type_sale', 'label': 'Type Sale', 'type': 'select'},
        {'field': 'terms', 'label': 'Terms'},
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date'},
        {'field': 'dt_deadline', 'label': 'Expires'},
        {'field': 'price_level', 'label': 'Price Level'},
    ],
}

PURCHASE_INFO_CARD = {
    'title': 'Purchase',
    'fields': [
        {'field': 'terms', 'label': 'Terms'},
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date'},
        {'field': 'dt_needed', 'label': 'Need By'},
        {'field': 'ship_via', 'label': 'Ship Via'},
        {'field': 'priority', 'label': 'Priority'},
    ],
}

VENDOR_CARD = {
    'title': 'Vendor',
    'title_ida': 'vendor_id',
    'fields': [
        {'field': 'company', 'label': 'Company'},
        {'field': 'phone', 'label': 'Phone'},
        {'field': 'attention', 'label': 'Attn'},
        {'field': 'address_full', 'label': 'Address'},
        {'field': 'email', 'label': 'Email'},
    ],
}

WORK_ORDER_INFO_CARD = {
    'title': 'Work Order',
    'fields': [
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Start Date'},
        {'field': 'dt_needed', 'label': 'Need By'},
        {'field': 'dt_deadline', 'label': 'Deadline'},
        {'field': 'priority', 'label': 'Priority'},
        {'field': 'assigned_to', 'label': 'Assigned To'},
    ],
}

REQUISITION_INFO_CARD = {
    'title': 'Requisition',
    'fields': [
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date'},
        {'field': 'dt_needed', 'label': 'Need By'},
        {'field': 'priority', 'label': 'Priority'},
        {'field': 'assigned_to', 'label': 'Requested By'},
    ],
}

RECEIPT_INFO_CARD = {
    'title': 'Receipt',
    'fields': [
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date Received'},
        {'field': 'source_type', 'label': 'Source'},
        {'field': 'ship_via', 'label': 'Ship Via'},
    ],
}

PAYMENT_INFO_CARD = {
    'title': 'Payment',
    'fields': [
        {'field': 'status', 'label': 'Status', 'type': 'select'},
        {'field': 'dt_start', 'label': 'Date'},
        {'field': 'payment_method', 'label': 'Method'},
        {'field': 'reference', 'label': 'Reference'},
    ],
}

# ── Sell-side tabs (order, invoice, proposal) ──────────────────────────

SELL_TABS = [
    {'label': 'Summary', 'content': 'summary'},
    {'label': 'Margins', 'content': 'margins'},
    {'label': 'Contacts', 'content': 'contacts'},
    {'label': 'QA', 'content': 'qa'},
    {'label': 'Actions', 'content': 'actions'},
    {'label': 'Documents', 'content': 'documents'},
    {'label': 'Notes', 'content': 'notes'},
    {'label': 'Related', 'content': 'related_transactions'},
]

# ── Exec-side tabs (purchase, requisition, work_order) ─────────────────

EXEC_TABS = [
    {'label': 'Summary', 'content': 'summary'},
    {'label': 'Contacts', 'content': 'contacts'},
    {'label': 'Actions', 'content': 'actions'},
    {'label': 'Documents', 'content': 'documents'},
    {'label': 'Shipping', 'content': 'shipping'},
    {'label': 'Notes', 'content': 'notes'},
    {'label': 'Related', 'content': 'related_transactions'},
]

RECEIPT_TABS = [
    {'label': 'Summary', 'content': 'summary'},
    {'label': 'Actions', 'content': 'actions'},
    {'label': 'Documents', 'content': 'documents'},
    {'label': 'Notes', 'content': 'notes'},
]

PAYMENT_TABS = [
    {'label': 'Summary', 'content': 'summary'},
    {'label': 'Actions', 'content': 'actions'},
    {'label': 'Notes', 'content': 'notes'},
    {'label': 'History', 'content': 'history'},
]

# ── Model configs ──────────────────────────────────────────────────────

MODELS = {
    'order': {
        'family': 'sell',
        'cards': {
            'bill_to': BILL_TO_CARD,
            'ship_to': SHIP_TO_CARD,
            'info': ORDER_INFO_CARD,
        },
        'header_cards': ['bill_to', 'ship_to', 'info'],
        'line_toolbar': ['L', 'S', 'XR', 'M', 'C'],
        'tabs': SELL_TABS,
        'locked_statuses': ['completed', 'cancelled', 'void'],
    },
    'invoice': {
        'family': 'sell',
        'cards': {
            'bill_to': BILL_TO_CARD,
            'ship_to': SHIP_TO_CARD,
            'info': INVOICE_INFO_CARD,
        },
        'header_cards': ['bill_to', 'ship_to', 'info'],
        'line_toolbar': ['L', 'S', 'XR', 'M'],
        'tabs': SELL_TABS,
        'locked_statuses': ['posted', 'void'],
    },
    'proposal': {
        'family': 'sell',
        'cards': {
            'bill_to': BILL_TO_CARD,
            'ship_to': SHIP_TO_CARD,
            'info': PROPOSAL_INFO_CARD,
        },
        'header_cards': ['bill_to', 'ship_to', 'info'],
        'line_toolbar': ['L', 'S'],
        'tabs': SELL_TABS,
        'locked_statuses': ['accepted', 'expired', 'cancelled'],
    },
    'purchase': {
        'family': 'exec',
        'cards': {
            'vendor': VENDOR_CARD,
            'ship_to': SHIP_TO_CARD,
            'info': PURCHASE_INFO_CARD,
        },
        'header_cards': ['vendor', 'ship_to', 'info'],
        'line_toolbar': ['L', 'S'],
        'tabs': EXEC_TABS,
        'locked_statuses': ['completed', 'cancelled', 'void'],
    },
    'work_order': {
        'family': 'exec',
        'cards': {
            'bill_to': BILL_TO_CARD,
            'info': WORK_ORDER_INFO_CARD,
        },
        'header_cards': ['bill_to', 'info'],
        'line_toolbar': ['L'],
        'tabs': EXEC_TABS,
        'locked_statuses': ['completed', 'cancelled'],
    },
    'requisition': {
        'family': 'exec',
        'cards': {
            'vendor': VENDOR_CARD,
            'info': REQUISITION_INFO_CARD,
        },
        'header_cards': ['vendor', 'info'],
        'line_toolbar': ['L'],
        'tabs': EXEC_TABS,
        'locked_statuses': ['completed', 'cancelled'],
    },
    'receipt': {
        'family': 'exec',
        'cards': {
            'vendor': VENDOR_CARD,
            'info': RECEIPT_INFO_CARD,
        },
        'header_cards': ['vendor', 'info'],
        'line_toolbar': [],
        'tabs': RECEIPT_TABS,
        'locked_statuses': ['completed'],
    },
    'payment': {
        'family': 'sell',
        'cards': {
            'bill_to': BILL_TO_CARD,
            'info': PAYMENT_INFO_CARD,
        },
        'header_cards': ['bill_to', 'info'],
        'line_toolbar': [],
        'tabs': PAYMENT_TABS,
        'locked_statuses': ['posted', 'void'],
    },
}


class Command(BaseCommand):
    help = 'Create wc:detail_layout Settings for transaction models'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing layout Settings')

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = updated = skipped = 0

        for model_key, cfg in MODELS.items():
            config = {
                'model': model_key,
                'family': cfg['family'],
                'card': cfg['cards'],
                'sections': [
                    {
                        'type': 'header',
                        'header': {
                            'layout': 'columns',
                            'cards': cfg['header_cards'],
                        },
                    },
                    {
                        'type': 'line_card',
                        'family': cfg['family'],
                        'toolbar': cfg['line_toolbar'],
                        'actions': [],
                    },
                    {
                        'type': 'tabs',
                        'tabs': cfg['tabs'],
                    },
                ],
                'edit_rules': {
                    'locked_statuses': cfg['locked_statuses'],
                    'status_field': 'status',
                },
            }

            existing = Setting.objects.filter(
                parent_model=model_key,
                purpose='wc:detail_layout',
                is_active=True,
            ).first()

            expl = (
                f"Display layout for {model_key}. "
                f"Defines header cards (bill to, ship to, {model_key} info), "
                f"line items toolbar, and tab panels for the App view detail page."
            )

            if existing and not force:
                skipped += 1
                self.stdout.write(f'  SKIP {model_key} (id={existing.id}) — exists')
                continue

            if existing:
                existing.config = config
                existing.explanation = expl
                existing.save()
                updated += 1
                self.stdout.write(f'  Updated {model_key} (id={existing.id})')
            else:
                Setting.objects.create(
                    name=f'detail_layout:{model_key}',
                    ida=f'wc-display-{model_key}',
                    parent_model=model_key,
                    purpose='wc:detail_layout',
                    scope='system',
                    config=config,
                    explanation=expl,
                )
                created += 1
                self.stdout.write(f'  Created {model_key}')

        self.stdout.write(self.style.SUCCESS(
            f'Display layouts: {created} created, {updated} updated, {skipped} skipped'
        ))
