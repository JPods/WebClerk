"""
seed_databrowser — Create initial DataBrowser layouts + one fake record per model.

Usage:
    ./bin/python manage.py seed_databrowser              # both layouts + fake records
    ./bin/python manage.py seed_databrowser --layouts     # layouts only
    ./bin/python manage.py seed_databrowser --fakes       # fake records only
    ./bin/python manage.py seed_databrowser --force       # overwrite existing layouts

Layouts are saved as Setting records with purpose="wc:workbench_fields".
Each includes a named "initial" view that Alice can use as a baseline
to compare against user-submitted layouts.

Fake records are marked with metadata.health = "fake" so they can be
filtered or deleted later.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.models.setting import Setting
import json, time, uuid as uuid_mod


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
    'proposal':     {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'price_level', 'attention', 'email', 'address_full', 'terms', 'dt_created', 'dt_modified']},
    'purchase':     {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'price_level', 'attention', 'email', 'address_full', 'terms', 'dt_created', 'dt_modified']},
    'workorder':    {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'attention', 'dt_created', 'dt_modified']},
    'requisition':  {'list': ['id', 'ida', 'status', 'total', 'dt_created', 'priority'], 'detail': ['id', 'ida', 'status', 'total', 'priority', 'dt_created', 'dt_modified']},

    # --- Transaction lines ---
    'invoice_line':     {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'price_level', 'dt_created', 'dt_modified']},
    'order_line':       {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'price_level', 'dt_created', 'dt_modified']},
    'proposal_line':    {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'price_level', 'dt_created', 'dt_modified']},
    'purchase_line':    {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'dt_created', 'dt_modified']},
    'workorder_line':   {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'dt_created', 'dt_modified']},
    'requisition_line': {'list': ['id', 'line_number', 'status', 'dt_created'], 'detail': ['id', 'line_number', 'status', 'dt_created', 'dt_modified']},

    # --- Products ---
    'item':             {'list': ['id', 'ida', 'name', 'kind', 'status', 'uom', 'dt_created'], 'detail': ['id', 'ida', 'name', 'description', 'sku', 'kind', 'status', 'uom', 'product_line', 'price', 'cost', 'flags', 'weight', 'is_serialized', 'lead_time_days', 'dt_created', 'dt_modified']},
    'variant':          {'list': ['id', 'ida', 'description', 'canonical_key', 'dt_created'], 'detail': ['id', 'ida', 'item_ida', 'description', 'canonical_key', 'attrs', 'dt_created', 'dt_modified']},
    'warehouse':        {'list': ['id', 'code', 'name', 'priority', 'is_active', 'site_code'], 'detail': ['id', 'code', 'name', 'priority', 'site_code', 'is_active', 'location', 'count', 'dt_created', 'dt_modified']},
    'org_item':         {'list': ['id', 'ida', 'item_ida', 'description', 'availability'], 'detail': ['id', 'ida', 'item_ida', 'description', 'availability', 'data', 'metrics', 'dt_created', 'dt_modified']},
    'bill_of_material': {'list': ['id', 'parent_ida', 'child_ida', 'quantity', 'sequence', 'revision'], 'detail': ['id', 'parent_ida', 'child_ida', 'child_description', 'quantity', 'scrap_factor', 'yield_pct', 'sequence', 'revision', 'is_alternate', 'alternate_group', 'is_optional', 'cost_snapshot', 'dt_created']},
    'service':          {'list': ['id', 'ida', 'description', 'category', 'default_duration_minutes'], 'detail': ['id', 'ida', 'description', 'purpose', 'category', 'display', 'billing', 'process', 'default_duration_minutes', 'dt_created', 'dt_modified']},
    'catalog':          {'list': ['id', 'ida', 'name', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'name', 'is_active', 'dt_created', 'dt_modified']},
    'item_xref':        {'list': ['id', 'ida', 'item_ida', 'dt_created'], 'detail': ['id', 'ida', 'item_ida', 'dt_created', 'dt_modified']},
    'item_usage':       {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},

    # --- Core ---
    'contact':      {'list': ['id', 'email', 'name_first', 'name_last', 'company', 'title', 'role', 'phone'], 'detail': ['id', 'ida', 'email', 'name_first', 'name_last', 'name_prefix', 'name_suffix', 'company', 'title', 'department', 'role', 'phone', 'domain', 'address_full', 'comment', 'is_staff', 'is_superuser', 'dt_created', 'dt_modified']},
    'action':       {'list': ['id', 'ida', 'status', 'kanban_column', 'priority', 'percent_complete', 'project_name', 'dt_deadline'], 'detail': ['id', 'ida', 'action', 'description', 'status', 'kanban_column', 'priority', 'difficulty', 'percent_complete', 'project_name', 'project_ida', 'assigned_to', 'sequence', 'dt_start', 'dt_deadline', 'dt_expected', 'dt_completed', 'duration', 'dt_created', 'dt_modified']},
    'setting':      {'list': ['id', 'name', 'purpose', 'parent_model', 'role', 'is_active'], 'detail': ['id', 'name', 'purpose', 'parent_model', 'role', 'is_active', 'data', 'dt_created', 'dt_modified']},
    'report':       {'list': ['id', 'name', 'model_name', 'output_type', 'category', 'purpose'], 'detail': ['id', 'name', 'description', 'purpose', 'model_name', 'record_id', 'output_type', 'category', 'dt_created', 'dt_modified']},
    'notification': {'list': ['id', 'name', 'purpose', 'model_name', 'record_id', 'dt_created'], 'detail': ['id', 'name', 'purpose', 'model_name', 'record_id', 'data', 'dt_created', 'dt_modified']},

    # --- Accounts ---
    'gl_account':       {'list': ['id', 'ida', 'name', 'type', 'category', 'division', 'used_for'], 'detail': ['id', 'ida', 'name', 'type', 'category', 'division', 'used_for', 'type_id', 'account_credit', 'account_debit', 'comment', 'is_active', 'dt_created', 'dt_modified']},
    'gl_journal':       {'list': ['id', 'account', 'debit', 'credit', 'source', 'source_model', 'dt_created'], 'detail': ['id', 'account', 'debit', 'credit', 'source', 'type', 'source_id', 'source_model', 'dt_created', 'dt_modified']},
    'ledger':           {'list': ['id', 'value_original', 'value_available', 'dt_due', 'dt_applied', 'source', 'model_name'], 'detail': ['id', 'value_original', 'value_available', 'source', 'model_name', 'parent_id', 'dt_due', 'dt_discount_due', 'dt_journaled', 'dt_applied', 'is_cleared', 'is_void', 'discount_potential', 'dt_created']},
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
    'document':        {'list': ['id', 'name', 'status', 'model_name', 'confidential', 'mime_type', 'count_accessed'], 'detail': ['id', 'name', 'slug', 'status', 'description', 'model_name', 'record_id', 'confidential', 'mime_type', 'size_bytes', 'checksum', 'path', 'retention_period', 'sequence', 'count_accessed', 'copyright', 'dt_created', 'dt_modified']},
    'tag':             {'list': ['id', 'name', 'purpose', 'status', 'model_name', 'sequence', 'count_accessed'], 'detail': ['id', 'name', 'purpose', 'status', 'model_name', 'record_id', 'data', 'sequence', 'count_accessed', 'dt_created', 'dt_modified']},
    'linkage':         {'list': ['id', 'name', 'model_name', 'record_id', 'group_id', 'purpose', 'role'], 'detail': ['id', 'name', 'model_name', 'record_id', 'group_id', 'purpose', 'role', 'note', 'sequence', 'dt_created', 'dt_modified']},
    'question_answer': {'list': ['id', 'question', 'answer', 'parent_model', 'status', 'sequence'], 'detail': ['id', 'question', 'answer', 'parent_model', 'parent_id', 'status', 'sequence', 'answered_by', 'count_accessed', 'dt_created', 'dt_modified']},

    # --- Sync ---
    'connection':  {'list': ['id', 'ida', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'is_active', 'dt_created', 'dt_modified']},
    'sync_bundle': {'list': ['id', 'ida', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'is_active', 'dt_created', 'dt_modified']},

    # --- Products (additional) ---
    'delivery_line':   {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'delivery_visit':  {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'inventory_adjustment_run': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'inventory_check':      {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'inventory_check_line': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'inventory_metrics_snapshot': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'inventory_reservation': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'pending_inventory_adjustment': {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},
    'serial_log':  {'list': ['id', 'ida', 'dt_created'], 'detail': ['id', 'ida', 'dt_created', 'dt_modified']},

    # --- Transactions (additional) ---
    'project':              {'list': ['id', 'ida', 'name', 'is_active', 'dt_created'], 'detail': ['id', 'ida', 'name', 'is_active', 'dt_created', 'dt_modified']},
}


def _now_ms():
    return int(time.time() * 1000)


def _filter_valid_fields(model_cls, field_names):
    """Return only field names that actually exist on the model."""
    valid = {f.name for f in model_cls._meta.get_fields()}
    return [f for f in field_names if f in valid]


class Command(BaseCommand):
    help = 'Seed DataBrowser initial layouts and/or fake records for all models'

    def add_arguments(self, parser):
        parser.add_argument('--layouts', action='store_true', help='Seed layouts only')
        parser.add_argument('--fakes', action='store_true', help='Seed fake records only')
        parser.add_argument('--force', action='store_true', help='Overwrite existing layouts')

    def handle(self, *args, **options):
        do_layouts = options.get('layouts', False)
        do_fakes = options.get('fakes', False)
        force = options.get('force', False)

        # Default: do both
        if not do_layouts and not do_fakes:
            do_layouts = True
            do_fakes = True

        if do_layouts:
            self._seed_layouts(force)
        if do_fakes:
            self._seed_fakes()

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
                Setting.objects.create(
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

    def _seed_fakes(self):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding fake records...'))
        created = skipped = errors = 0

        for model_key in sorted(MODEL_REGISTRY.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                continue

            # Skip line models — they need parent FKs
            if meta.kind == 'line':
                skipped += 1
                continue

            try:
                model_cls = meta.import_model()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Skip {model_key}: {e}'))
                errors += 1
                continue

            try:
                # Check if fake already exists
                has_metadata = any(
                    f.name == 'metadata' for f in model_cls._meta.get_fields() if hasattr(f, 'column')
                )
                has_ida = any(
                    f.name == 'ida' for f in model_cls._meta.get_fields() if hasattr(f, 'column')
                )
                if has_metadata:
                    existing = model_cls.objects.filter(metadata__health='fake').first()
                elif has_ida:
                    existing = model_cls.objects.filter(ida__startswith='zz-fake-').first()
                else:
                    existing = None
                if existing:
                    skipped += 1
                    continue

                with transaction.atomic():
                    obj = self._create_fake(model_cls, model_key, meta)
                    if obj:
                        created += 1
                        self.stdout.write(f'  Created fake {model_key} #{obj.pk}')
                    else:
                        skipped += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.WARNING(f'  Error {model_key}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Fakes: {created} created, {skipped} skipped, {errors} errors'
        ))

    def _create_fake(self, model_cls, model_key, meta):
        """Create a single fake record with sensible defaults."""
        now = _now_ms()
        fields = {f.name: f for f in model_cls._meta.get_fields() if hasattr(f, 'column')}
        kwargs = {}

        # Metadata with health=fake marker
        if 'metadata' in fields:
            kwargs['metadata'] = {'health': 'fake', 'created_by': 'seed_databrowser'}

        # Standard fields
        if 'ida' in fields:
            kwargs['ida'] = f'zz-fake-{model_key}'
        if 'name' in fields and fields['name'].__class__.__name__ == 'CharField':
            kwargs['name'] = f'zz Fake {meta.singular}'
        if 'display_name' in fields:
            kwargs['display_name'] = f'zz Fake {meta.singular}'
        if 'description' in fields and fields['description'].__class__.__name__ in ('CharField', 'TextField'):
            kwargs['description'] = f'Fake {meta.singular} for DataBrowser testing'
        if 'status' in fields:
            kwargs['status'] = 'active'
        if 'is_active' in fields:
            kwargs['is_active'] = True
        if 'dt_created' in fields:
            kwargs['dt_created'] = now
        if 'dt_modified' in fields:
            kwargs['dt_modified'] = now
        if 'uuid' in fields:
            kwargs['uuid'] = str(uuid_mod.uuid4())
        if 'version' in fields:
            kwargs['version'] = 1

        # JSON fields — empty dicts
        for fname in ('refs', 'prefs', 'comments', 'actions', 'data'):
            if fname in fields and fields[fname].__class__.__name__ == 'JSONField':
                kwargs.setdefault(fname, {})

        # Model-specific defaults
        if model_key in ('customer', 'vendor', 'manufacturer', 'employee', 'rep'):
            kwargs['org_type'] = model_key
            kwargs.setdefault('email', f'zz-fake-{model_key}@example.com')
            kwargs.setdefault('phone', '555-000-0000')
        elif model_key == 'contact':
            kwargs['email'] = f'zz-fake@example.com'
            kwargs['name_first'] = 'zz Fake'
            kwargs['name_last'] = 'Contact'
            kwargs['role'] = 'user'
        elif model_key == 'item':
            kwargs.setdefault('kind', 'product')
            kwargs.setdefault('uom', 'ea')
            kwargs.setdefault('price', {'base': 0})
            kwargs.setdefault('cost', {'standard': 0})
        elif model_key == 'setting':
            kwargs['purpose'] = 'fake_seed'
            kwargs['config'] = {'health': 'fake'}
        elif model_key == 'gl_account':
            kwargs['ida'] = 'zz-fake-00000'
            kwargs['type'] = 'asset'
            kwargs['category'] = 'cash'
        elif model_key == 'currency':
            kwargs['code'] = 'ZZF'
            kwargs['symbol'] = 'F'
            kwargs['precision'] = 2
        elif model_key == 'term':
            kwargs.setdefault('days_due', 0)
        elif model_key == 'warehouse':
            kwargs['code'] = 'ZZ-FAKE'
        elif model_key in ('invoice', 'order', 'proposal', 'purchase', 'workorder', 'requisition'):
            kwargs.setdefault('total', 0)
            if 'balance' in fields:
                kwargs.setdefault('balance', 0)

        # Skip models that require complex FK setup we can't easily satisfy
        required_fks = [
            f for f in model_cls._meta.get_fields()
            if hasattr(f, 'related_model') and f.related_model is not None
            and hasattr(f, 'null') and not f.null
            and f.name not in kwargs
            and hasattr(f, 'column')
        ]
        if required_fks:
            # Can't create without required FKs
            return None

        try:
            obj = model_cls(**kwargs)
            obj.full_clean()
            obj.save()
            return obj
        except Exception:
            # Try without full_clean (some models have complex validation)
            try:
                obj = model_cls(**kwargs)
                obj.save()
                return obj
            except Exception:
                raise
