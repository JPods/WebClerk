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
    'workorder_line': [
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
    'touch': [
        f('ida', width=70),
        f('channel', width=70),
        f('direction', width=50),
        f('subject', width=200),
        f('outcome', width=80),
        f('dt_created', width=90, format='date'),
    ],
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

    # --- Orgs (as panels on transactions/contacts) ---
    'customer': [
        f('ida', width=80),
        f('company', width=200),
        f('status', width=70),
        f('phone', width=120, format='phone'),
    ],
    'vendor': [
        f('ida', width=80),
        f('company', width=200),
        f('status', width=70),
    ],
    'manufacturer': [
        f('ida', width=80),
        f('company', width=200),
        f('status', width=70),
    ],
    'employee': [
        f('ida', width=80),
        f('display_name', width=200),
        f('status', width=70),
        f('email', width=180),
    ],
    'rep': [
        f('ida', width=80),
        f('display_name', width=200),
        f('status', width=70),
    ],
    'contact': [
        f('ida', width=80),
        f('attention', width=150),
        f('email', width=180),
        f('phone', width=120, format='phone'),
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
    'workorder': [
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
    # NOTE: 'service' is not in MODEL_REGISTRY — no panel needed
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
    # --- AI / Alice ---
    'ai_message': [
        f('ida', width=70),
        f('sender', width=100),
        f('receiver', width=100),
        f('subject', width=200),
        f('classification', width=80),
        f('dt_created', width=90, format='date'),
    ],
    'alice_coaching_log': [
        f('ida', width=70),
        f('drill_name', width=150),
        f('category', width=80),
        f('passed', width=50),
        f('score', width=50, align='right'),
        f('dt_created', width=90, format='date'),
    ],
    'alice_observation': [
        f('ida', width=70),
        f('category', width=80),
        f('source', width=80),
        f('message', width=200),
        f('priority', width=60, align='right'),
        f('acknowledged', width=50),
    ],
    'alice_preset': [
        f('ida', width=70),
        f('name', width=150),
        f('preset_type', width=80),
        f('model_name', width=100),
        f('use_count', width=60, align='right'),
        f('dt_created', width=90, format='date'),
    ],

    # --- Accounts ---
    'audit': [
        f('ida', width=80),
        f('name', width=200),
        f('status', width=70),
        f('priority', width=60, align='right'),
        f('is_completed', width=50),
        f('dt_created', width=90, format='date'),
    ],
    'currency': [
        f('code', width=60),
        f('name', width=150),
        f('symbol', width=40),
        f('precision', width=60, align='right'),
        f('is_active', width=50),
    ],
    'gl_account': [
        f('ida', width=80),
        f('name', width=200),
        f('type', width=80),
        f('category', width=80),
        f('type_id', width=70),
        f('division', width=60, align='right'),
    ],
    'journal_batch': [
        f('ida', width=80),
        f('batch_type', width=80),
        f('status', width=70),
        f('period_year', width=60, align='right'),
        f('period_month', width=60, align='right'),
        f('total_debit', width=90, align='right', format='currency'),
        f('total_credit', width=90, align='right', format='currency'),
    ],
    'tax_jurisdiction': [
        f('ida', width=80),
        f('tax_jurisdiction', width=150),
        f('tax_name', width=100),
        f('tax_rate_sales', width=70, align='right', format='percent'),
        f('is_active', width=50),
    ],
    'term': [
        f('ida', width=80),
        f('name', width=150),
        f('description', width=200),
        f('days_due', width=60, align='right'),
        f('discount_rate', width=70, align='right', format='percent'),
    ],

    # --- Sync ---
    'bundle': [
        f('ida', width=80),
        f('direction', width=70),
        f('model_name', width=100),
        f('status', width=70),
        f('alert', width=100),
        f('dt_created', width=90, format='date'),
    ],
    'connection': [
        f('ida', width=80),
        f('name', width=200),
        f('type', width=70),
        f('status', width=70),
        f('action', width=70),
        f('dt_created', width=90, format='date'),
    ],

    # --- Products / Inventory ---
    'catalog': [
        f('name', width=150),
        f('code', width=80),
        f('status', width=70),
        f('currency', width=50),
        f('priority', width=60, align='right'),
        f('is_active', width=50),
    ],
    'delivery_visit': [
        f('status', width=70),
        f('dt_scheduled', width=90, format='date'),
        f('dt_arrived', width=90, format='date'),
        f('dt_completed', width=90, format='date'),
    ],
    'delivery_line': [
        f('planned_qty', width=70, align='right'),
        f('loaded_qty', width=70, align='right'),
        f('delivered_qty', width=70, align='right'),
        f('skipped_reason', width=100),
        f('status', width=70),
    ],
    'inventory_adjustment_run': [
        f('run_type', width=80),
        f('status', width=70),
        f('attempted', width=70, align='right'),
        f('applied', width=70, align='right'),
        f('skipped_locked', width=70, align='right'),
        f('dry_run', width=50),
    ],
    'inventory_check': [
        f('status', width=70),
        f('dt_performed', width=90, format='date'),
        f('notes', width=200),
        f('dt_created', width=90, format='date'),
    ],
    'inventory_check_line': [
        f('item_ida', width=100),
        f('description', width=200),
        f('counted_qty', width=70, align='right'),
        f('prior_qty', width=70, align='right'),
        f('variance_qty', width=70, align='right'),
    ],
    'inventory_layer': [
        f('item_ida', width=100),
        f('lot', width=80),
        f('status', width=70),
        f('source_doc_type', width=80),
        f('is_locked', width=50),
        f('dt_created', width=90, format='date'),
    ],
    'inventory_metrics_snapshot': [
        f('status', width=70),
        f('purpose', width=100),
        f('dt_created', width=90, format='date'),
    ],
    'inventory_reservation': [
        f('ida', width=80),
        f('item_ida', width=100),
        f('state', width=70),
        f('qty', width=60, align='right'),
        f('reason', width=100),
        f('dt_expires', width=90, format='date'),
    ],
    'item_usage': [
        f('item_ida', width=100),
        f('description', width=200),
        f('year', width=50, align='right'),
        f('month', width=50, align='right'),
        f('status', width=70),
    ],
    'warehouse': [
        f('name', width=150),
        f('code', width=70),
        f('site_code', width=70),
        f('status', width=70),
        f('priority', width=60),
        f('is_active', width=50),
    ],

    # --- Docs ---
    'linkage': [
        f('ida', width=80),
        f('name', width=150),
        f('model_name', width=100),
        f('role', width=70),
        f('sequence', width=60, align='right'),
        f('dt_created', width=90, format='date'),
    ],
    'tag': [
        f('ida', width=80),
        f('name', width=150),
        f('model_name', width=100),
        f('count_accessed', width=70, align='right'),
        f('sequence', width=60, align='right'),
    ],

    # --- Orgs ---
    'other_org': [
        f('ida', width=80),
        f('display_name', width=200),
        f('org_type', width=80),
        f('status', width=70),
        f('email', width=180),
    ],

    # --- Transactions ---
    'payment_method': [
        f('ida', width=80),
        f('name', width=150),
        f('description', width=200),
        f('is_active', width=50),
    ],
    'payment_term': [
        f('ida', width=80),
        f('name', width=150),
        f('days', width=60, align='right'),
        f('is_active', width=50),
    ],
    'pending_payment_application': [
        f('ida', width=80),
        f('amount', width=90, align='right', format='currency'),
        f('state', width=70),
        f('reason', width=100),
        f('dt_applied', width=90, format='date'),
    ],
    'project_association': [
        f('ida', width=80),
        f('model_code', width=100),
        f('status', width=70),
        f('dt_created', width=90, format='date'),
    ],
    'requisition': [
        f('ida', width=80),
        f('name', width=200),
        f('status', width=70),
        f('dt_created', width=90, format='date'),
    ],
    'requisition_line': [
        f('ida', width=70),
        f('line_number', width=60, align='right'),
        f('line_type', width=70),
        f('price_level', width=70),
        f('status', width=70),
        f('dt_created', width=90, format='date'),
    ],
    'statement_line': [
        f('ida', width=80),
        f('description', width=200),
        f('amount', width=90, align='right', format='currency'),
        f('merchant', width=100),
        f('category', width=80),
        f('statement_date', width=90, format='date'),
    ],

    # --- Core / Support ---
    'report': [
        f('ida', width=80),
        f('name', width=200),
        f('category', width=80),
        f('output_type', width=70),
        f('status', width=70),
        f('dt_created', width=90, format='date'),
    ],
    'setting': [
        f('ida', width=80),
        f('name', width=200),
        f('purpose', width=100),
        f('scope', width=70),
        f('parent_model', width=100),
    ],
    'workspace': [
        f('ida', width=80),
        f('name', width=150),
        f('component', width=100),
        f('nav_group', width=80),
        f('nav_order', width=60, align='right'),
        f('is_active', width=50),
    ],
    'databrowser': [
        f('ida', width=80),
        f('name', width=200),
        f('purpose', width=100),
        f('scope', width=70),
        f('parent_model', width=100),
    ],
    'gantt': [
        f('ida', width=80),
        f('name', width=200),
        f('purpose', width=100),
        f('scope', width=70),
        f('parent_model', width=100),
    ],
    'wc': [
        f('ida', width=80),
        f('name', width=200),
        f('purpose', width=100),
        f('scope', width=70),
        f('parent_model', width=100),
    ],

    # --- Projects / Misc ---
    'project': [
        f('ida', width=80),
        f('name', width=200),
        f('status', width=70),
        f('dt_created', width=90, format='date'),
    ],
    'item': [
        f('ida', width=80),
        f('sku', width=100),
        f('description', width=200),
        f('status', width=70),
    ],
    'notification': [
        f('ida', width=80),
        f('subject', width=200),
        f('status', width=70),
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
                purpose='wc:workbench_fields',
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
                        purpose='wc:workbench_fields',
                        explanation=f"Panel column layout for {model_key}. Defines which fields appear in related-record panels.",
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

        # Auto-flush frontend if anything changed
        if created or updated:
            from django.core.management import call_command
            call_command('flush_frontend')
