"""
seed_databrowser — Create initial DataBrowser layouts.

Usage:
    ./bin/python manage.py seed_databrowser              # layouts
    ./bin/python manage.py seed_databrowser --force       # overwrite existing layouts

Layouts are saved as Setting records with purpose="wc:workbench_fields".
Each includes a named "initial" view that Alice can use as a baseline
to compare against user-submitted layouts.

This command makes no records. Every record is a real record (Bill, 2026-11-13).
"""
from django.core.management.base import BaseCommand
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.models.setting import Setting


# ─────────────────────────────────────────────────────────────────────────────
# Curated field layouts per model — list (compact) and detail (comprehensive)
# ─────────────────────────────────────────────────────────────────────────────

LAYOUTS = {
    # --- Orgs ---
    'customer':     {'list': ['id', 'display_name', 'status', 'email', 'phone', 'address_full', 'price_level'], 'detail': ['id', 'ida', 'display_name', 'status', 'org_type', 'attention', 'email', 'phone', 'domain', 'address_full', 'price_level', 'terms', 'company', 'dt_created', 'dt_modified']},
    'vendor':       {'list': ['id', 'display_name', 'status', 'email', 'phone', 'address_full', 'price_level'], 'detail': ['id', 'ida', 'display_name', 'status', 'org_type', 'attention', 'email', 'phone', 'domain', 'address_full', 'price_level', 'terms', 'dt_created', 'dt_modified']},
    'manufacturer': {'list': ['id', 'display_name', 'status', 'email', 'phone', 'address_full'], 'detail': ['id', 'ida', 'display_name', 'status', 'org_type', 'attention', 'email', 'phone', 'domain', 'address_full', 'dt_created', 'dt_modified']},
    'employee':     {'list': ['id', 'display_name', 'status', 'email', 'phone', 'address_full'], 'detail': ['id', 'ida', 'display_name', 'status', 'org_type', 'attention', 'email', 'phone', 'address_full', 'dt_created', 'dt_modified']},
    'rep':          {'list': ['id', 'display_name', 'status', 'email', 'phone', 'address_full'], 'detail': ['id', 'ida', 'display_name', 'status', 'org_type', 'attention', 'email', 'phone', 'address_full', 'dt_created', 'dt_modified']},

    # --- Transactions (headers) ---
    'invoice':      {'list': ['id', 'ida', 'status', 'total', 'balance', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'balance', 'priority', 'price_level', 'attention', 'email', 'phone', 'address_full', 'terms', 'dt_created', 'dt_modified']},
    'order':        {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'price_level', 'attention', 'email', 'phone', 'address_full', 'terms', 'dt_created', 'dt_modified']},
    'quote':     {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'price_level', 'attention', 'email', 'address_full', 'terms', 'dt_created', 'dt_modified']},
    'purchase':     {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'price_level', 'attention', 'email', 'address_full', 'terms', 'dt_created', 'dt_modified']},
    'workorder':    {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'attention', 'dt_created', 'dt_modified']},
    'requisition':  {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'dt_created', 'dt_modified']},

    # --- Transaction lines ---
    'invoice_line':     {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'price_level', 'dt_created', 'dt_modified']},
    'order_line':       {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'price_level', 'dt_created', 'dt_modified']},
    'quote_line':    {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'price_level', 'dt_created', 'dt_modified']},
    'purchase_line':    {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'dt_created', 'dt_modified']},
    'workorder_line':   {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'dt_created', 'dt_modified']},
    'requisition_line': {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'dt_created', 'dt_modified']},

    # --- Products ---
    'item':             {'list': ['id', 'ida', 'name', 'kind', 'status', 'uom', 'dt_created'], 'detail': ['id', 'ida', 'name', 'description', 'sku', 'kind', 'status', 'uom', 'product_line', 'price', 'cost', 'flags', 'weight', 'is_serialized', 'lead_time_days', 'dt_created', 'dt_modified']},
    'variant':          {'list': ['id', 'ida', 'description', 'canonical_key', 'dt_created'], 'detail': ['id', 'ida', 'item_ida', 'description', 'canonical_key', 'attrs', 'dt_created', 'dt_modified']},
    'warehouse':        {'list': ['id', 'code', 'name', 'priority', 'is_active', 'site_code'], 'detail': ['id', 'code', 'name', 'priority', 'site_code', 'is_active', 'location', 'count', 'dt_created', 'dt_modified']},
    'bill_of_material': {'list': ['id', 'parent_ida', 'child_ida', 'quantity', 'sequence', 'revision'], 'detail': ['id', 'parent_ida', 'child_ida', 'child_description', 'quantity', 'scrap_factor', 'yield_pct', 'sequence', 'revision', 'is_alternate', 'alternate_group', 'is_optional', 'cost_snapshot', 'dt_created']},
    'service':          {'list': ['id', 'ida', 'description', 'category', 'default_duration_minutes'], 'detail': ['id', 'ida', 'description', 'purpose', 'category', 'display', 'billing', 'process', 'default_duration_minutes', 'dt_created', 'dt_modified']},
    'catalog':          {'list': ['id', 'ida', 'name', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'name', 'is_active', 'dt_created', 'dt_modified']},
    'item_xref':        {'list': ['id', 'ida', 'item_ida', 'dt_created'], 'detail': ['id', 'ida', 'item_ida', 'dt_created', 'dt_modified']},
    'item_usage':       {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},

    # --- Core ---
    'contact':      {'list': ['id', 'email', 'name_first', 'name_last', 'company', 'title', 'role', 'phone'], 'detail': ['id', 'ida', 'email', 'name_first', 'name_last', 'name_prefix', 'name_suffix', 'company', 'title', 'department', 'role', 'phone', 'domain', 'address_full', 'comment', 'is_staff', 'is_superuser', 'dt_created', 'dt_modified']},
    'action':       {'list': ['id', 'ida', 'status', 'kanban_column', 'priority', 'percent_complete', 'project_name', 'dt_deadline'], 'detail': ['id', 'ida', 'action', 'description', 'status', 'kanban_column', 'priority', 'difficulty', 'percent_complete', 'project_name', 'project_ida', 'assigned_to', 'sequence', 'dt_start', 'dt_deadline', 'dt_expected', 'dt_completed', 'duration', 'dt_created', 'dt_modified']},
    'setting':      {'list': ['id', 'name', 'purpose', 'parent_model', 'role', 'is_active'], 'detail': ['id', 'name', 'purpose', 'parent_model', 'role', 'is_active', 'data', 'dt_created', 'dt_modified']},
    'report':       {'list': ['id', 'name', 'target_model', 'output_type', 'category', 'purpose'], 'detail': ['id', 'name', 'description', 'purpose', 'target_model', 'record_id', 'output_type', 'category', 'dt_created', 'dt_modified']},

    # --- Accounts ---
    'gl_account':       {'list': ['id', 'ida', 'name', 'type', 'category', 'division', 'used_for'], 'detail': ['id', 'ida', 'name', 'type', 'category', 'division', 'used_for', 'type_id', 'account_credit', 'account_debit', 'comment', 'is_active', 'dt_created', 'dt_modified']},
    'gl_journal':       {'list': ['id', 'account', 'debit', 'credit', 'source', 'source_model', 'dt_created'], 'detail': ['id', 'account', 'debit', 'credit', 'source', 'type', 'source_id', 'source_model', 'dt_created', 'dt_modified']},
    'ledger':           {'list': ['id', 'value_original', 'value_available', 'dt_due', 'source', 'model_name'], 'detail': ['id', 'value_original', 'value_available', 'source', 'model_name', 'parent_id', 'dt_due', 'dt_discount_due', 'dt_recorded', 'discount_potential', 'dt_created']},
    'audit':            {'list': ['id', 'name', 'purpose', 'priority', 'rating', 'is_completed', 'dt_created'], 'detail': ['id', 'name', 'purpose', 'priority', 'rating', 'is_completed', 'conflicts', 'changes', 'actions', 'recommendations', 'dt_created', 'dt_modified']},
    'currency':         {'list': ['id', 'code', 'name', 'symbol', 'precision', 'is_active'], 'detail': ['id', 'code', 'name', 'symbol', 'precision', 'is_active', 'dt_created', 'dt_modified']},
    'term':             {'list': ['id', 'name', 'description', 'days_due', 'discount_rate', 'period_count'], 'detail': ['id', 'name', 'description', 'days_due', 'discount_rate', 'days_discount', 'period_count', 'days_in_period', 'day_cut_off_invoice', 'day_cut_off_due', 'approved_by', 'dt_begin', 'dt_created']},
    'tax_jurisdiction': {'list': ['id', 'tax_jurisdiction', 'service_provider', 'tax_rate_sales', 'tax_rate_cost', 'is_active'], 'detail': ['id', 'tax_jurisdiction', 'tax_name', 'service_provider', 'service_id', 'tax_rate_sales', 'tax_rate_cost', 'tax_rate_on_shipping', 'gl_account_payable', 'is_active', 'scripts', 'dt_created']},

    # --- Communications ---
    'email':    {'list': ['id', 'email', 'name', 'type', 'is_primary', 'is_verified', 'opt_out'], 'detail': ['id', 'email', 'name', 'attention', 'type', 'is_primary', 'is_verified', 'opt_out', 'contact_id', 'dt_created', 'dt_modified']},
    'phone':    {'list': ['id', 'number', 'name', 'country_code', 'format', 'opt_out'], 'detail': ['id', 'number', 'name', 'attention', 'country_code', 'format', 'opt_out', 'contact_id', 'dt_created', 'dt_modified']},
    'address':  {'list': ['id', 'full', 'city', 'state', 'zip', 'country', 'address_type'], 'detail': ['id', 'address1', 'address2', 'city', 'state', 'zip', 'country', 'full', 'address_type', 'latitude', 'longitude', 'instructions', 'contact_id', 'dt_created', 'dt_modified']},
    'domain':   {'list': ['id', 'path', 'type', 'status', 'sequence', 'count_accessed'], 'detail': ['id', 'path', 'type', 'status', 'comment', 'sequence', 'count_accessed', 'contact_id', 'dt_created', 'dt_modified']},

    # --- Docs ---
    'document':        {'list': ['id', 'name', 'status', 'target_model', 'confidential', 'mime_type', 'count_accessed'], 'detail': ['id', 'name', 'slug', 'status', 'description', 'target_model', 'record_id', 'confidential', 'mime_type', 'size_bytes', 'checksum', 'path', 'retention_period', 'sequence', 'count_accessed', 'dt_created', 'dt_modified']},
    'tag':             {'list': ['id', 'name', 'purpose', 'status', 'target_model', 'sequence', 'count_accessed'], 'detail': ['id', 'name', 'purpose', 'status', 'target_model', 'record_id', 'data', 'sequence', 'count_accessed', 'dt_created', 'dt_modified']},
    'linkage':         {'list': ['id', 'name', 'model_name', 'record_id', 'group_id', 'purpose', 'role'], 'detail': ['id', 'name', 'model_name', 'record_id', 'group_id', 'purpose', 'role', 'note', 'sequence', 'dt_created', 'dt_modified']},
    'question_answer': {'list': ['id', 'question', 'answer', 'parent_model', 'status', 'sequence'], 'detail': ['id', 'question', 'answer', 'parent_model', 'parent_id', 'status', 'sequence', 'answered_by', 'count_accessed', 'dt_created', 'dt_modified']},

    # --- Sync ---
    'connection':  {'list': ['id', 'ida', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'is_active', 'dt_created', 'dt_modified']},
    'sync_bundle': {'list': ['id', 'ida', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'is_active', 'dt_created', 'dt_modified']},

    # --- Products (additional) ---
    'inventory_adjustment_run': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'inventory_metrics_snapshot': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'pending_inventory_adjustment': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},

    # --- Transactions (additional) ---
    'project':              {'list': ['id', 'ida', 'name', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'name', 'is_active', 'dt_created', 'dt_modified']},
}


def _filter_valid_fields(model_cls, field_names):
    """Return only field names that actually exist on the model."""
    valid = {f.name for f in model_cls._meta.get_fields()}
    return [f for f in field_names if f in valid]


class Command(BaseCommand):
    help = 'Seed DataBrowser initial layouts for all models'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing layouts')

    def handle(self, *args, **options):
        self._seed_layouts(options.get('force', False))

    def _seed_layouts(self, force):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding DataBrowser layouts...'))
        created = updated = skipped = 0

        for model_key in sorted(MODEL_REGISTRY.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                continue
            try:
                model_cls = meta.import_model()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Skip {model_key}: {e}'))
                continue

            # Get curated layout or build a generic one
            layout = LAYOUTS.get(model_key)
            if not layout:
                # Generic fallback: id + first few char/text fields
                fields = model_cls._meta.get_fields()
                names = [f.name for f in fields if hasattr(f, 'column')]
                char_fields = [f.name for f in fields if f.__class__.__name__ in ('CharField', 'EmailField') and hasattr(f, 'column')][:4]
                layout = {
                    'list': ['id'] + char_fields,
                    'detail': names[:20],
                }

            # Filter to valid fields only
            list_fields = _filter_valid_fields(model_cls, layout['list'])
            detail_fields = _filter_valid_fields(model_cls, layout['detail'])

            data = {
                'list': list_fields,
                'detail': detail_fields,
                'views': [
                    {
                        'name': 'initial',
                        'list': list_fields,
                        'detail': detail_fields,
                        'listWidths': {},
                    },
                    {
                        'name': 'flat',
                        'list': list_fields,
                        'detail': detail_fields,
                        'listWidths': {},
                    },
                ],
            }

            existing = Setting.objects.filter(
                parent_model=model_key,
                purpose='wc:workbench_fields',
            ).first()

            if existing and not force:
                skipped += 1
                continue

            meta = MODEL_REGISTRY.get(model_key)
            expl = (
                f"DataBrowser workbench layout for {meta.singular if meta else model_key}. "
                f"User-level list columns, detail fields, and named views."
            )

            if existing:
                existing.config = data
                existing.explanation = expl
                existing.save()
                updated += 1
                self.stdout.write(f'  Updated {model_key} ({len(list_fields)} list, {len(detail_fields)} detail)')
            else:
                Setting.authorized_create(
                    name=f'workbench_fields:{model_key}',
                    parent_model=model_key,
                    purpose='wc:workbench_fields',
                    config=data,
                    explanation=expl,
                )
                created += 1
                self.stdout.write(f'  Created {model_key} ({len(list_fields)} list, {len(detail_fields)} detail)')

        self.stdout.write(self.style.SUCCESS(
            f'Layouts: {created} created, {updated} updated, {skipped} skipped (use --force to overwrite)'
        ))
