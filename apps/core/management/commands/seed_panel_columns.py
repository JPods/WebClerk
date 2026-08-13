"""
seed_panel_columns — Best-guess column layouts for embedded panels (db.panel).

Merges panel[] into existing workbench_fields Settings without touching
list/detail/views. If no Setting exists, creates one with panel only.

These columns drive PanelTable rendering in RelatedPanel and anywhere
a model appears as an embedded panel inside another model's detail view.

Usage:
    ./bin/python manage.py seed_panel_columns
    ./bin/python manage.py seed_panel_columns --force   # overwrite existing panel[]
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


def f(field, **kw):
    """Shorthand for a DbFieldSpec dict."""
    spec = {'field': field}
    spec.update(kw)
    return spec


# ── Panel column definitions per model ────────────────────────────────────
# These define what columns appear when the model is shown as an embedded
# panel inside another model's detail view. Format values match
# DbFieldSpec.format in setting.py: currency, percent, date, number,
# json, phone, masked.

PANEL_COLUMNS = {
    # --- Transaction lines ---
    'order_line': [
        f('ida', width=70),
        f('item_code', width=100),
        f('description', width=200),
        f('qty', width=50, align='right'),
        f('unit_price', width=80, align='right', format='currency'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'invoice_line': [
        f('ida', width=70),
        f('item_code', width=100),
        f('description', width=200),
        f('qty', width=50, align='right'),
        f('unit_price', width=80, align='right', format='currency'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'proposal_line': [
        f('ida', width=70),
        f('item_code', width=100),
        f('description', width=200),
        f('qty', width=50, align='right'),
        f('unit_price', width=80, align='right', format='currency'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'purchase_line': [
        f('ida', width=70),
        f('item_code', width=100),
        f('description', width=200),
        f('qty', width=50, align='right'),
        f('cost', width=80, align='right', format='currency'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'work_order_line': [
        f('ida', width=70),
        f('item_code', width=100),
        f('description', width=200),
        f('qty', width=50, align='right'),
    ],
    'receipt_line': [
        f('ida', width=70),
        f('item_code', width=100),
        f('description', width=200),
        f('qty_received', width=70, align='right'),
    ],

    # --- Communications ---
    'email': [
        f('email', width=200),
        f('name', width=120),
        f('type', width=70),
        f('is_primary', width=50),
    ],
    'phone': [
        f('number', width=130, format='phone'),
        f('name', width=120),
        f('country_code', width=40),
        f('format', width=70),
    ],
    'address': [
        f('full', width=250),
        f('city', width=100),
        f('state', width=50),
        f('zip', width=60),
        f('address_type', width=70),
    ],
    'domain': [
        f('path', width=200),
        f('type', width=70),
        f('status', width=70),
    ],

    # --- Transactions (as panels on orgs/contacts) ---
    'order': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],
    'invoice': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('balance', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],
    'proposal': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],
    'purchase': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],
    'payment': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],
    'work_order': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],

    # --- Actions / Documents ---
    'action': [
        f('ida', width=80),
        f('action', width=200),
        f('status', width=70),
        f('priority', width=60),
        f('assigned_to', width=100),
        f('dt_deadline', width=90, format='date'),
    ],
    'document': [
        f('ida', width=80),
        f('name', width=200),
        f('status', width=70),
        f('mime_type', width=80),
        f('dt_created', width=90, format='date'),
    ],
    'question_answer': [
        f('question', width=250),
        f('answer', width=200),
        f('status', width=70),
    ],

    # --- Products ---
    'serial': [
        f('ida', width=80),
        f('serial_number', width=120),
        f('status', width=70),
        f('location', width=100),
    ],
    'item_xref': [
        f('ida', width=80),
        f('item_ida', width=100),
        f('dt_created', width=90, format='date'),
    ],
    'org_item': [
        f('ida', width=80),
        f('item_ida', width=100),
        f('description', width=200),
        f('availability', width=80),
    ],
    'bill_of_material': [
        f('child_ida', width=100),
        f('child_description', width=200),
        f('quantity', width=60, align='right'),
        f('scrap_factor', width=70, align='right'),
    ],
    'variant': [
        f('ida', width=80),
        f('description', width=200),
        f('canonical_key', width=120),
    ],
    'service': [
        f('ida', width=80),
        f('description', width=200),
        f('category', width=80),
    ],
    # --- Inventory ---
    'receipt': [
        f('ida', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],

    # --- Accounts ---
    'ledger': [
        f('ida', width=80),
        f('value_original', width=90, align='right', format='currency'),
        f('value_available', width=90, align='right', format='currency'),
        f('source', width=100),
        f('dt_due', width=90, format='date'),
    ],
    'payment_application': [
        f('ida', width=80),
        f('amount', width=90, align='right', format='currency'),
        f('dt_created', width=90, format='date'),
    ],
    'serial_log': [
        f('ida', width=80),
        f('dt_created', width=90, format='date'),
    ],
    'gl_journal': [
        f('account', width=120),
        f('debit', width=80, align='right', format='currency'),
        f('credit', width=80, align='right', format='currency'),
        f('source', width=100),
        f('dt_created', width=90, format='date'),
    ],
}


class Command(BaseCommand):
    help = 'Seed db.panel column definitions for embedded panels'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing panel columns')

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = updated = skipped = 0

        for model_key, panel_specs in sorted(PANEL_COLUMNS.items()):
            existing = Setting.objects.filter(
                parent_model=model_key,
                purpose='workbench_fields',
            ).first()

            if existing:
                config = existing.config or {}
                db = config.get('db') or config

                if db.get('panel') and not force:
                    skipped += 1
                    continue

                # Merge panel into existing config.db
                if 'db' in config:
                    config['db']['panel'] = panel_specs
                else:
                    config['panel'] = panel_specs
                existing.config = config
                existing.save()
                updated += 1
                self.stdout.write(f'  Updated {model_key}: {len(panel_specs)} panel columns')
            else:
                try:
                    Setting.objects.create(
                        name=f'workbench_fields:{model_key}',
                        parent_model=model_key,
                        purpose='workbench_fields',
                        config={'db': {'panel': panel_specs}},
                    )
                    created += 1
                    self.stdout.write(f'  Created {model_key}: {len(panel_specs)} panel columns')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Skip {model_key}: {e}'))
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {created} created, {updated} updated, {skipped} skipped'
        ))
