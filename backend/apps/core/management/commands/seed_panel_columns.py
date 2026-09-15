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
    # ══════════════════════════════════════════════════════════════════════
    # Column order convention (Bill's rule):
    #   1. ida          — always first
    #   2. purpose      — if the model has it
    #   3. status       — if the model has it
    #   4. Scalar fields — model's own DB columns (not JSON internals)
    #   5. comments.process — for any model with a comments JSONField
    #   6. Best-guess   — most useful remaining for a glance decision
    #
    # Target: 4-6 columns per panel. Enough to decide whether to click in.
    # ══════════════════════════════════════════════════════════════════════

    # ── Transaction lines ───────────────────────────────────────────────
    # Lines use flattened JSON names (item_code, qty, unit_price, extended)
    # because the API projects item/quantity/price JSON into scalar keys.
    'order_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('item_code', width=100),
        f('description', width=180),
        f('qty', width=50, align='right'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'invoice_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('item_code', width=100),
        f('description', width=180),
        f('qty', width=50, align='right'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'proposal_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('item_code', width=100),
        f('description', width=180),
        f('qty', width=50, align='right'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'purchase_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('item_code', width=100),
        f('description', width=180),
        f('qty', width=50, align='right'),
        f('extended', width=90, align='right', format='currency'),
    ],
    'workorder_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('item_code', width=100),
        f('description', width=180),
        f('qty', width=50, align='right'),
    ],
    'receipt_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('item_code', width=100),
        f('description', width=180),
        f('lot', width=80),
    ],
    'requisition_line': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('line_number', width=60, align='right'),
        f('line_type', width=70),
        f('price_level', width=70),
    ],

    # ── Communications ──────────────────────────────────────────────────
    'touch': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('channel', width=70),
        f('subject', width=180),
        f('outcome', width=80),
    ],
    'email': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('email', width=180),
        f('name', width=120),
        f('type', width=70),
    ],
    'phone': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('number', width=130, format='phone'),
        f('name', width=120),
        f('format', width=70),
    ],
    'address': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('full', width=220),
        f('city', width=100),
        f('state', width=50),
    ],
    'domain': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('path', width=200),
        f('type', width=70),
    ],

    # ── Orgs ────────────────────────────────────────────────────────────
    'customer': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('display_name', width=180),
        f('email', width=160),
        f('comments.process', width=120),
    ],
    'vendor': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('display_name', width=180),
        f('email', width=160),
        f('comments.process', width=120),
    ],
    'manufacturer': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('display_name', width=180),
        f('email', width=160),
        f('comments.process', width=120),
    ],
    'employee': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('display_name', width=180),
        f('email', width=160),
        f('comments.process', width=120),
    ],
    'rep': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('display_name', width=180),
        f('email', width=160),
        f('comments.process', width=120),
    ],
    'other_org': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('display_name', width=180),
        f('org_type', width=80),
        f('email', width=160),
    ],
    'contact': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('attention', width=140),
        f('email', width=160),
        f('company', width=120),
    ],

    # ── Transactions ────────────────────────────────────────────────────
    'order': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('source_name', width=100),
        f('total', width=90, align='right', format='currency'),
        f('comments.process', width=120),
    ],
    'invoice': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('invoice_type', width=80),
        f('total', width=90, align='right', format='currency'),
        f('balance', width=90, align='right', format='currency'),
    ],
    'proposal': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_needed', width=90, format='date'),
        f('comments.process', width=120),
    ],
    'purchase': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_needed', width=90, format='date'),
        f('comments.process', width=120),
    ],
    'payment': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('method', width=80),
        f('amount', width=90, align='right', format='currency'),
        f('category', width=80),
    ],
    'workorder': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('total', width=90, align='right', format='currency'),
        f('dt_needed', width=90, format='date'),
        f('comments.process', width=120),
    ],
    'receipt': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('source_type', width=80),
        f('dt_received', width=90, format='date'),
        f('comments.process', width=120),
    ],
    'requisition': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('source_name', width=120),
        f('dt_needed', width=90, format='date'),
        f('comments.process', width=120),
    ],
    'statement_line': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('description', width=160),
        f('amount', width=90, align='right', format='currency'),
        f('category', width=80),
    ],
    'payment_application': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('amount', width=90, align='right', format='currency'),
        f('applied_at', width=90, format='date'),
        f('comments.process', width=120),
    ],
    'pending_payment_application': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('amount', width=90, align='right', format='currency'),
        f('state', width=70),
        f('reason', width=100),
    ],
    'project_association': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('model_code', width=100),
        f('dt_created', width=90, format='date'),
    ],

    # ── Actions / Documents ─────────────────────────────────────────────
    'action': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('action_type', width=80),
        f('priority', width=60, align='right'),
        f('dt_deadline', width=90, format='date'),
    ],
    'document': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('mime_type', width=80),
        f('comments.process', width=120),
    ],
    'question_answer': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('question', width=200),
        f('answer', width=180),
    ],
    'linkage': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('model_name', width=100),
        f('role', width=70),
    ],
    'tag': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('model_name', width=100),
    ],

    # ── Products ────────────────────────────────────────────────────────
    'item': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('sku', width=100),
        f('name', width=180),
        f('comments.process', width=120),
    ],
    'serial': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('serial_ida', width=120),
        f('item_ida', width=100),
        f('description', width=160),
    ],
    'variant': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('description', width=160),
        f('canonical_key', width=100),
    ],
    'item_xref': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('external_sku', width=100),
        f('source_name', width=100),
    ],
    'org_item': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('description', width=160),
        f('availability_state', width=80),
    ],
    'bill_of_material': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('child_ida', width=100),
        f('child_description', width=160),
        f('quantity', width=60, align='right'),
    ],
    'serial_log': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('action', width=120),
        f('dt', width=90, format='date'),
    ],
    'catalog': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('code', width=80),
        f('currency', width=50),
    ],

    # ── Inventory ───────────────────────────────────────────────────────
    'warehouse': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('code', width=70),
        f('site_code', width=70),
    ],
    'inventory_layer': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('lot', width=80),
        f('source_doc_type', width=80),
    ],
    'inventory_reservation': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('qty', width=60, align='right'),
        f('reason', width=100),
    ],
    'inventory_check': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('dt_performed', width=90, format='date'),
        f('notes', width=180),
    ],
    'inventory_check_line': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('counted_qty', width=70, align='right'),
        f('variance_qty', width=70, align='right'),
    ],
    'inventory_adjustment_run': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('run_type', width=80),
        f('attempted', width=70, align='right'),
        f('applied', width=70, align='right'),
    ],
    'inventory_metrics_snapshot': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('dt_created', width=90, format='date'),
    ],
    'item_usage': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('item_ida', width=100),
        f('year', width=50, align='right'),
        f('month', width=50, align='right'),
    ],
    'delivery_visit': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('dt_scheduled', width=90, format='date'),
        f('dt_arrived', width=90, format='date'),
    ],
    'delivery_line': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('planned_qty', width=70, align='right'),
        f('delivered_qty', width=70, align='right'),
        f('skipped_reason', width=100),
    ],

    # ── Accounts ────────────────────────────────────────────────────────
    'ledger': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('source', width=100),
        f('value_original', width=90, align='right', format='currency'),
        f('value_available', width=90, align='right', format='currency'),
    ],
    'gl_journal': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('account', width=120),
        f('debit', width=80, align='right', format='currency'),
        f('credit', width=80, align='right', format='currency'),
    ],
    'gl_account': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('type', width=80),
        f('category', width=80),
    ],
    'journal_batch': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('batch_type', width=80),
        f('total_debit', width=90, align='right', format='currency'),
        f('total_credit', width=90, align='right', format='currency'),
    ],
    'tax_jurisdiction': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('tax_jurisdiction', width=150),
        f('tax_name', width=100),
        f('tax_rate_sales', width=70, align='right', format='percent'),
    ],
    'term': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('days_due', width=60, align='right'),
        f('discount_rate', width=70, align='right', format='percent'),
    ],
    'currency': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('code', width=60),
        f('name', width=150),
        f('symbol', width=40),
    ],
    'audit': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('priority', width=60, align='right'),
        f('is_completed', width=50),
    ],

    # ── AI / Alice ──────────────────────────────────────────────────────
    'ai_message': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('sender', width=100),
        f('subject', width=180),
        f('classification', width=80),
    ],
    'alice_coaching_log': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('drill_name', width=150),
        f('category', width=80),
        f('score', width=50, align='right'),
    ],
    'alice_observation': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('category', width=80),
        f('source', width=80),
        f('message', width=180),
    ],
    'alice_preset': [
        f('ida', width=70),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('preset_type', width=80),
        f('model_name', width=100),
    ],

    # ── Sync ────────────────────────────────────────────────────────────
    'bundle': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('direction', width=70),
        f('model_name', width=100),
        f('alert', width=100),
    ],
    'connection': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('type', width=70),
        f('action', width=70),
    ],

    # ── Projects / Core ────────────────────────────────────────────────
    'project': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('category', width=80),
        f('comments.process', width=120),
    ],
    'notification': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('model_name', width=80),
    ],
    'report': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=180),
        f('category', width=80),
        f('output_type', width=70),
    ],
    'setting': [
        f('ida', width=80),
        f('purpose', width=100),
        f('status', width=70),
        f('name', width=180),
        f('scope', width=70),
        f('parent_model', width=100),
    ],
    'workspace': [
        f('ida', width=80),
        f('purpose', width=80),
        f('status', width=70),
        f('name', width=150),
        f('component', width=100),
        f('nav_group', width=80),
    ],
    'databrowser': [
        f('ida', width=80),
        f('purpose', width=100),
        f('status', width=70),
        f('name', width=180),
        f('scope', width=70),
        f('parent_model', width=100),
    ],
    'gantt': [
        f('ida', width=80),
        f('purpose', width=100),
        f('status', width=70),
        f('name', width=180),
        f('scope', width=70),
        f('parent_model', width=100),
    ],
    'wc': [
        f('ida', width=80),
        f('purpose', width=100),
        f('status', width=70),
        f('name', width=180),
        f('scope', width=70),
        f('parent_model', width=100),
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
