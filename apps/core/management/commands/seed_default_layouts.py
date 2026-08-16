"""
seed_default_layouts — Repopulate default list AND detail layouts for all wc:model Settings.

Selects human-meaningful fields in priority order:
  1. ida (always first — human identifier)
  2. WHO: company, attention, contact, customer, vendor, assigned_to, display_name, rep
  3. WHAT: name, action, subject, description, sku, item_id
  4. VALUE: total, balance, amount, price, cost (promoted — must show on transactions)
  5. WHY: purpose, reason, explanation
  6. WHEN: only action-event dates (dt_start, dt_deadline, dt_needed, dt_payment, dt_completed)
     — NOT system timestamps (dt_created, dt_modified, dt_approved, dt_last_used, dt_joined)
  7. STATUS: status, process, priority, percent_complete (NOT is_active — filter instead)
  8. CONTEXT: comment, comments, notes

is_active=false records are hidden by default filter, not shown as a column.

Builds both:
  - layout.list.default.columns (scannable grid — max 12 columns)
  - layout.detail.default.fields (full record — all meaningful fields)

Usage:
  ./manage.py seed_default_layouts              # dry run
  ./manage.py seed_default_layouts --apply      # write changes
  ./manage.py seed_default_layouts --model action  # one model only
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from apps.core.models import Setting


# Fields to always skip — plumbing, not human
SKIP_FIELDS = {
    'id', 'uuid', 'version', 'security_level', 'times_used',
    'is_deleted', 'is_archived', 'is_locked', 'is_active',
    'is_staff', 'is_superuser',
    'config', 'metadata', 'refs', 'prefs', 'actions',
    'password', 'groups', 'user_permissions', 'last_login',
    'search_vector', 'row_version', 'line_increment',
}

# System timestamps — skip unless they're action-event dates
SKIP_DT = {
    'dt_created', 'dt_modified', 'dt_approved', 'dt_last_used', 'dt_joined',
    'dt_kanban', 'dt_reconciliation', 'dt_processed',
    'dt_start_original', 'dt_end_original',
}

# Priority tiers — fields are selected in this order
# Each tier: (field_names, default_width, default_align)
PRIORITY_TIERS = [
    # Tier 0: ida always first
    ({'ida'}, 100, 'left'),
    # Tier 1: WHO
    ({'company', 'attention', 'contact', 'customer', 'vendor',
      'assigned_to', 'display_name', 'rep', 'name_first', 'name_last',
      'created_by', 'manufacturer'}, 140, 'left'),
    # Tier 2: WHAT
    ({'name', 'action', 'subject', 'description', 'sku',
      'kind', 'uom', 'invoice_type', 'action_type', 'type',
      'scope', 'parent_model', 'category', 'title'}, 160, 'left'),
    # Tier 3: VALUE (promoted above WHY/WHEN — must show on transactions)
    ({'total', 'balance', 'amount', 'price', 'cost', 'sell',
      'fee_amount', 'margin_pct', 'margin_velocity'}, 100, 'right'),
    # Tier 4: WHY
    ({'purpose', 'reason', 'explanation', 'intent', 'situation',
      'objective', 'retrospection'}, 140, 'left'),
    # Tier 5: WHEN (action events only)
    ({'dt_start', 'dt_deadline', 'dt_needed', 'dt_payment',
      'dt_completed', 'dt_expected', 'dt_end'}, 100, 'center'),
    # Tier 6: STATUS (is_active removed — filter instead)
    ({'status', 'process', 'priority', 'percent_complete',
      'is_commission', 'difficulty'}, 90, 'center'),
    # Tier 7: CONTEXT
    ({'comment', 'comments', 'notes', 'conditions_description'}, 180, 'left'),
]

# Format hints by field name
FORMAT_MAP = {
    'total': 'currency', 'balance': 'currency', 'amount': 'currency',
    'price': 'currency', 'cost': 'currency', 'sell': 'currency',
    'fee_amount': 'currency', 'margin_pct': 'percent',
    'phone': 'phone',
    'totals.total': 'currency', 'totals.balance': 'currency',
    'totals.subtotal': 'currency', 'totals.tax': 'currency',
    'totals.shipping': 'currency', 'totals.margin': 'currency',
    'totals.cost': 'currency', 'totals.discount': 'currency',
    'totals.received': 'currency',
    'price.unit': 'currency', 'price.extended': 'currency',
    'cost.unit': 'currency', 'cost.extended': 'currency',
    'quantity.active': 'number', 'quantity.staged': 'number',
    'quantity.remaining': 'number',
}

# JSON envelope fields to use INSTEAD of flat JSON blob fields.
# These are dot-path fields the DataGrid already resolves (DataGrid.tsx line 640).
# Key = flat field name to replace; Value = list of dot-path specs to inject.
#
# Transaction headers: replace flat total/balance/cost/sell with totals.* envelope
TRANSACTION_ENVELOPE_FIELDS = [
    {'field': 'totals.subtotal', 'width': 100, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'totals.total', 'width': 100, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'totals.balance', 'width': 100, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'totals.margin', 'width': 100, 'align': 'right', 'format': 'currency', 'visible': True},
]

# Sell-side lines (BaseSellLineModel): quantity + price + cost envelopes
SELL_LINE_ENVELOPE_FIELDS = [
    {'field': 'quantity.active', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'quantity.staged', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'quantity.remaining', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'price.unit', 'width': 90, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'price.extended', 'width': 100, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'cost.unit', 'width': 90, 'align': 'right', 'format': 'currency', 'visible': True},
]

# Exec-side lines (BaseExecLineModel): quantity + cost only — no price envelope
EXEC_LINE_ENVELOPE_FIELDS = [
    {'field': 'quantity.active', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'quantity.staged', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'quantity.remaining', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'cost.unit', 'width': 90, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'cost.extended', 'width': 100, 'align': 'right', 'format': 'currency', 'visible': True},
]

# Item: quantity + price envelopes
ITEM_ENVELOPE_FIELDS = [
    {'field': 'quantity.active', 'width': 70, 'align': 'right', 'format': 'number', 'visible': True},
    {'field': 'price.unit', 'width': 90, 'align': 'right', 'format': 'currency', 'visible': True},
    {'field': 'cost.unit', 'width': 90, 'align': 'right', 'format': 'currency', 'visible': True},
]

# Models that get envelope fields injected instead of flat JSON blob columns
TRANSACTION_HEADER_MODELS = {'order', 'invoice', 'proposal', 'purchase', 'requisition'}
# Receipt is a receiving document (BaseModel), not a financial transaction header.
# It does not have a totals JSONField.

# Sell-side lines (BaseSellLineModel) — have quantity + price + cost
SELL_LINE_MODELS = {'order_line', 'invoice_line', 'proposal_line'}
# Exec-side lines (BaseExecLineModel) — have quantity + cost, NO price
EXEC_LINE_MODELS = {'purchase_line', 'requisition_line', 'receipt_line', 'work_order_line'}

ITEM_MODELS = {'item'}

# Flat JSON blob fields that get replaced by envelope dot-paths
FLAT_JSON_FIELDS = {'total', 'balance', 'cost', 'sell', 'totals', 'finance',
                    'commission', 'flow', 'source', 'price', 'quantity'}

# Max columns in list view — keep it scannable
MAX_LIST_COLUMNS = 12
# Detail shows everything meaningful — no hard cap, but skip plumbing
MAX_DETAIL_FIELDS = 30


# Manual aliases for parent_model names that don't match Django model_name
# even after underscore removal. Key = Setting parent_model, Value = Django model_name.
MODEL_ALIASES = {
    'other_org': 'other',
    'linkage': 'linkageentry',
    'inventory_adjustment_run': 'inventoryadjustmentprocessorrun',
}


def get_model_class(model_name):
    """Find Django model class by model_name.

    Handles the underscore mismatch: Setting parent_model uses snake_case
    (invoice_line) but Django model_name has no underscores (invoiceline).
    Falls back to MODEL_ALIASES for names that don't normalize cleanly.
    """
    normalized = model_name.replace('_', '')
    alias = MODEL_ALIASES.get(model_name)
    for model in apps.get_models():
        mn = model._meta.model_name
        if mn == model_name or mn == normalized or (alias and mn == alias):
            return model
    return None


def get_available_fields(model_class):
    """Get concrete fields minus plumbing, system timestamps, and flat JSON blobs."""
    all_fields = set()
    for f in model_class._meta.get_fields():
        if hasattr(f, 'column'):
            all_fields.add(f.name)

    # Remove FK _id suffixes that have a matching field without _id
    fk_ids = {f for f in all_fields if f.endswith('_id') and f[:-3] in all_fields}
    available = all_fields - SKIP_FIELDS - fk_ids - SKIP_DT

    # For models with envelope fields, remove flat JSON blob fields
    model_name = model_class._meta.model_name
    if model_name in TRANSACTION_HEADER_MODELS | SELL_LINE_MODELS | EXEC_LINE_MODELS | ITEM_MODELS:
        available -= FLAT_JSON_FIELDS

    return available


def make_spec(field, width, align):
    """Build a DbFieldSpec dict."""
    spec = {'field': field, 'width': width, 'align': align, 'visible': True}
    fmt = FORMAT_MAP.get(field)
    if fmt:
        spec['format'] = fmt
    if field.startswith('dt_'):
        spec['format'] = 'date'
    return spec


def get_envelope_fields(model_name):
    """Return the envelope dot-path fields for a model, or empty list."""
    if model_name in TRANSACTION_HEADER_MODELS:
        return list(TRANSACTION_ENVELOPE_FIELDS)
    if model_name in SELL_LINE_MODELS:
        return list(SELL_LINE_ENVELOPE_FIELDS)
    if model_name in EXEC_LINE_MODELS:
        return list(EXEC_LINE_ENVELOPE_FIELDS)
    if model_name in ITEM_MODELS:
        return list(ITEM_ENVELOPE_FIELDS)
    return []


def build_columns(available, max_fields, model_name=None):
    """Select fields by priority tier, up to max_fields.

    For transaction/item models, injects envelope dot-path fields
    at the VALUE tier position instead of flat JSON blob fields.
    """
    columns = []
    used = set()
    envelope_injected = False

    for tier_fields, default_width, default_align in PRIORITY_TIERS:
        # Inject envelope fields at VALUE tier (tier 3)
        if not envelope_injected and 'total' in tier_fields and model_name:
            envelope = get_envelope_fields(model_name)
            if envelope:
                for spec in envelope:
                    if len(columns) >= max_fields:
                        break
                    columns.append(dict(spec))  # copy
                envelope_injected = True
                # Skip the flat VALUE tier — envelope replaces it
                continue

        matches = tier_fields & available - used
        for field in sorted(matches):
            if len(columns) >= max_fields:
                return columns
            columns.append(make_spec(field, default_width, default_align))
            used.add(field)

    # If we still have room, add remaining fields alphabetically
    remaining = available - used
    for field in sorted(remaining):
        if len(columns) >= max_fields:
            break
        columns.append(make_spec(field, 120, 'left'))

    return columns


def build_default_list(model_name):
    """Build default list columns — compact, scannable."""
    model_class = get_model_class(model_name)
    if not model_class:
        return None, f'model {model_name} not found'

    available = get_available_fields(model_class)
    columns = build_columns(available, MAX_LIST_COLUMNS, model_name)
    desc = ', '.join(c['field'] for c in columns)
    return columns, f'{len(columns)} cols: {desc}'


def build_default_detail(model_name):
    """Build default detail fields — comprehensive, all meaningful fields."""
    model_class = get_model_class(model_name)
    if not model_class:
        return None, f'model {model_name} not found'

    available = get_available_fields(model_class)
    fields = build_columns(available, MAX_DETAIL_FIELDS, model_name)
    return fields, f'{len(fields)} fields'


class Command(BaseCommand):
    help = 'Repopulate default list and detail layouts with smart field selection'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write changes (default is dry run)')
        parser.add_argument('--model', type=str, help='Process one model only')

    def handle(self, *args, **options):
        apply = options['apply']
        model_filter = options.get('model')

        qs = Setting.objects.filter(purpose='wc:model', is_active=True)
        if model_filter:
            qs = qs.filter(parent_model=model_filter)

        total = qs.count()
        updated = 0
        skipped = 0

        self.stdout.write(f'\n{"APPLYING" if apply else "DRY RUN"} — {total} wc:model settings\n')

        for setting in qs.order_by('parent_model'):
            config = setting.config or {}
            layout = config.get('layout', {})

            # Must be in new named format
            list_layouts = layout.get('list', {})
            # Support both new (dynamic) and old (detail) key names
            dynamic_layouts = layout.get('dynamic', layout.get('detail', {}))
            if not isinstance(list_layouts, dict):
                skipped += 1
                self.stdout.write(f'  SKIP  {setting.parent_model} (id={setting.id}) — not in named format')
                continue

            list_cols, list_desc = build_default_list(setting.parent_model)
            detail_fields, detail_desc = build_default_detail(setting.parent_model)
            if list_cols is None:
                skipped += 1
                self.stdout.write(f'  SKIP  {setting.parent_model} (id={setting.id}) — {list_desc}')
                continue

            if apply:
                # Update default list layout
                if 'default' not in list_layouts:
                    list_layouts['default'] = {'dynamic': 'default', 'display': 'default', 'columns': []}
                list_layouts['default']['columns'] = list_cols
                layout['list'] = list_layouts

                # Update default dynamic layout
                if not isinstance(dynamic_layouts, dict):
                    dynamic_layouts = {}
                if 'default' not in dynamic_layouts:
                    dynamic_layouts['default'] = {'list': 'default', 'display': 'default', 'fields': []}
                dynamic_layouts['default']['fields'] = detail_fields
                layout['dynamic'] = dynamic_layouts
                # Remove old key if present
                layout.pop('detail', None)

                config['layout'] = layout
                setting.config = config
                setting.save(update_fields=['config'])

            updated += 1
            prefix = 'WRITE' if apply else 'WOULD'
            self.stdout.write(f'  {prefix} {setting.parent_model} (id={setting.id}) — list: {list_desc} | detail: {detail_desc}')

        self.stdout.write(f'\nDone: {updated} updated, {skipped} skipped\n')
