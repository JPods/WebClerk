"""Seed card layouts — populate config.layout.card in every wc:model Setting.

Gives every model a card layout for DynamicDetail (Kanban cards, floating
windows, embedded detail views). Card layouts group fields into named
card specs (identity, details, schedule, financial).

Recipe:
  1. identity card — ida, primary name/description, status, purpose
  2. details card — remaining scalar fields (not dates, not identity)
  3. schedule card — all dt_* fields
  4. financial card (transactions only) — company.name, totals.total, totals.balance, totals.tax

Usage:
    python manage.py seed_card_layouts              # dry run
    python manage.py seed_card_layouts --apply       # write changes
    python manage.py seed_card_layouts --force       # overwrite existing card layouts
    python manage.py seed_card_layouts --model action  # one model only
"""
from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
from apps.core.models import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta


# ── Skip sets ──────────────────────────────────────────────────────────

# Fields to never show in cards — plumbing
SKIP_FIELDS = {
    'id', 'uuid', 'version', 'security_level', 'times_used',
    'is_deleted', 'is_archived', 'is_locked',
    'is_staff', 'is_superuser',
    'config', 'metadata', 'refs', 'prefs', 'actions',
    'password', 'groups', 'user_permissions', 'last_login',
    'search_vector', 'row_version', 'line_increment',
}

# Identity-tier fields — go into the identity card
IDENTITY_FIELDS = {
    'ida', 'name', 'display_name', 'name_first', 'name_last',
    'action', 'description', 'subject', 'sku', 'title',
    'status', 'purpose', 'kind', 'org_type', 'role',
    'action_type', 'kanban_column', 'scope',
}

# Fields that are the model's "primary name" — checked in priority order
NAME_CANDIDATES = [
    'name', 'display_name', 'action', 'subject', 'title', 'sku',
    'name_first',
]

# Transaction header models that get a financial card
TRANSACTION_MODELS = {'order', 'invoice', 'proposal', 'purchase', 'workorder'}

# Virtual model keys — no real model class, skip
VIRTUAL_KEYS = {'wc', 'gantt', 'databrowser'}

# Manual aliases for parent_model -> Django model_name
MODEL_ALIASES = {
    'other_org': 'other',
    'linkage': 'linkageentry',
    'inventory_adjustment_run': 'inventoryadjustmentprocessorrun',
}


# ── Helpers ────────────────────────────────────────────────────────────

def get_model_class(model_name):
    """Find Django model class by model_name.

    Tries MODEL_REGISTRY first (handles dotted paths and aliases),
    then falls back to scanning Django's installed models.
    """
    # Try registry first (handles aliases, plurals, endpoint slugs)
    meta = get_model_meta(model_name)
    if meta:
        try:
            return meta.import_model()
        except Exception:
            pass

    # Fallback: scan by normalized name
    normalized = model_name.replace('_', '')
    alias = MODEL_ALIASES.get(model_name)
    for model in django_apps.get_models():
        mn = model._meta.model_name
        if mn == model_name or mn == normalized or (alias and mn == alias):
            return model
    return None


def get_concrete_fields(model_class):
    """Return list of (name, field) tuples for concrete DB columns."""
    return [
        (f.name, f)
        for f in model_class._meta.get_fields()
        if hasattr(f, 'column')
    ]


def get_field_choices(field):
    """Return list of choice values if field has choices, else None."""
    choices = getattr(field, 'choices', None)
    if not choices:
        return None
    # choices can be list of (value, label) tuples
    return [c[0] for c in choices if c[0] is not None and c[0] != '']


def make_field_spec(name, field=None, label_override=None):
    """Build a card field spec dict."""
    label = label_override or name
    spec = {'field': name, 'label': label}
    if field and get_field_choices(field):
        spec['type'] = 'select'
        spec['options'] = get_field_choices(field)
    return spec


def build_card_layout(model_name):
    """Build card layout dict for a model.

    Returns dict of named card specs, or None if model class not found.
    """
    model_class = get_model_class(model_name)
    if not model_class:
        return None

    concrete = get_concrete_fields(model_class)
    field_map = {name: f for name, f in concrete}
    all_names = set(field_map.keys())

    # Remove FK _id suffixes that duplicate a relationship field
    fk_ids = {n for n in all_names if n.endswith('_id') and n[:-3] in all_names}
    available = all_names - SKIP_FIELDS - fk_ids

    # ── Classify fields ────────────────────────────────────────────

    identity_names = available & IDENTITY_FIELDS
    date_names = {n for n in available if n.startswith('dt_')}
    bool_names = {n for n in available
                  if hasattr(field_map.get(n), 'get_internal_type')
                  and field_map[n].get_internal_type() == 'BooleanField'
                  and n not in IDENTITY_FIELDS}

    # Everything else is "details"
    detail_names = available - identity_names - date_names - bool_names - {'ida'}

    # ── Build identity card ────────────────────────────────────────

    identity_fields = []

    # ida always first
    if 'ida' in available:
        identity_fields.append(make_field_spec('ida'))

    # Primary name/description
    for candidate in NAME_CANDIDATES:
        if candidate in available and candidate not in {'ida'}:
            f = field_map.get(candidate)
            # JSON fields (action, description) use .en path
            if f and f.get_internal_type() == 'JSONField':
                identity_fields.append(make_field_spec(f'{candidate}.en', label_override=candidate))
            else:
                identity_fields.append(make_field_spec(candidate, f))
            identity_names.discard(candidate)
            break

    # Add name_last if name_first was used (contacts)
    if 'name_first' in {spec['field'] for spec in identity_fields} and 'name_last' in available:
        identity_fields.append(make_field_spec('name_last', field_map.get('name_last')))
        identity_names.discard('name_last')

    # description if not already used as primary name
    if 'description' not in {spec['field'].split('.')[0] for spec in identity_fields}:
        if 'description' in available:
            f = field_map.get('description')
            if f and f.get_internal_type() == 'JSONField':
                identity_fields.append(make_field_spec('description.en'))
            else:
                identity_fields.append(make_field_spec('description', f))
            identity_names.discard('description')

    # status with choices
    if 'status' in available:
        f = field_map.get('status')
        identity_fields.append(make_field_spec('status', f))
        identity_names.discard('status')

    # purpose with choices
    if 'purpose' in available and 'purpose' not in {spec['field'] for spec in identity_fields}:
        f = field_map.get('purpose')
        identity_fields.append(make_field_spec('purpose', f))
        identity_names.discard('purpose')

    # Remaining identity-tier fields
    for name in sorted(identity_names - {'ida', 'status', 'purpose'}):
        if name not in {spec['field'].split('.')[0] for spec in identity_fields}:
            identity_fields.append(make_field_spec(name, field_map.get(name)))

    # ── Build details card ─────────────────────────────────────────

    # Remove fields already in identity
    used_bases = {spec['field'].split('.')[0] for spec in identity_fields}
    detail_remaining = detail_names - used_bases

    detail_fields = []
    for name in sorted(detail_remaining):
        f = field_map.get(name)
        if not f:
            continue
        # Skip large JSON envelope fields that aren't useful in cards
        if f.get_internal_type() == 'JSONField' and name in {
            'comments', 'cost', 'sell', 'totals', 'finance', 'commission',
            'flow', 'source', 'addresses', 'emails', 'phones', 'company',
            'shipping', 'assigned_to', 'created_by', 'start_by', 'deadline_by',
            'expected_by', 'completed_by', 'updated_by', 'end_by',
            'impact', 'retrospection', 'project_metadata', 'languages',
            'stats', 'gls', 'flags', 'price', 'tax_code', 'catalog',
            'quantity', 'specification', 'conversion',
        }:
            continue
        detail_fields.append(make_field_spec(name, f))

    # ── Build schedule card ────────────────────────────────────────

    schedule_fields = []
    for name in sorted(date_names):
        schedule_fields.append(make_field_spec(name))

    # ── Build financial card (transactions only) ───────────────────

    cards = {}

    if identity_fields:
        cards['identity'] = {
            'title': 'identity',
            'fields': identity_fields,
        }

    if detail_fields:
        cards['details'] = {
            'title': 'details',
            'fields': detail_fields,
        }

    if schedule_fields:
        cards['schedule'] = {
            'title': 'schedule',
            'fields': schedule_fields,
        }

    # Financial card for transaction headers
    if model_name in TRANSACTION_MODELS:
        financial_fields = [
            make_field_spec('company.name'),
            make_field_spec('totals.subtotal'),
            make_field_spec('totals.total'),
            make_field_spec('totals.balance'),
            make_field_spec('totals.tax'),
            make_field_spec('totals.margin'),
        ]
        cards['financial'] = {
            'title': 'financial',
            'fields': financial_fields,
        }

    return cards


class Command(BaseCommand):
    help = 'Seed card layouts for all wc:model Settings'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Write changes (default is dry run)')
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing card layouts')
        parser.add_argument('--model', type=str,
                            help='Process one model only')

    def handle(self, *args, **options):
        apply = options['apply']
        force = options['force']
        model_filter = options.get('model')

        qs = Setting.objects.filter(purpose='wc:model', is_active=True)
        if model_filter:
            qs = qs.filter(parent_model=model_filter)

        total = qs.count()
        created = 0
        updated = 0
        skipped = 0

        mode = 'APPLYING' if apply else 'DRY RUN'
        if force:
            mode += ' (--force)'
        self.stdout.write(f'\n{mode} — {total} wc:model settings\n')

        for setting in qs.order_by('parent_model'):
            model_name = setting.parent_model
            if model_name in VIRTUAL_KEYS:
                skipped += 1
                continue

            config = setting.config or {}
            layout = config.get('layout', {})
            if not isinstance(layout, dict):
                layout = {}

            existing_card = layout.get('card')
            has_existing = (
                isinstance(existing_card, dict) and len(existing_card) > 0
            ) or (
                isinstance(existing_card, list) and len(existing_card) > 0
            )

            if has_existing and not force:
                skipped += 1
                self.stdout.write(
                    f'  SKIP  {model_name} (id={setting.id}) — '
                    f'card layout exists ({len(existing_card)} cards), use --force to overwrite'
                )
                continue

            card_layout = build_card_layout(model_name)
            if card_layout is None:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  SKIP  {model_name} (id={setting.id}) — model class not found'
                    )
                )
                continue

            card_count = len(card_layout)
            total_fields = sum(len(c.get('fields', [])) for c in card_layout.values())

            if apply:
                layout['card'] = card_layout
                config['layout'] = layout
                setting.config = config
                setting._setting_update_authorized = True
                setting.save(update_fields=['config'])

            action = 'UPDATE' if has_existing else 'CREATE'
            if has_existing:
                updated += 1
            else:
                created += 1

            prefix = action if apply else f'WOULD {action}'
            card_names = ', '.join(card_layout.keys())
            self.stdout.write(
                f'  {prefix}  {model_name} (id={setting.id}) — '
                f'{card_count} cards ({total_fields} fields): {card_names}'
            )

        self.stdout.write(
            f'\nDone: {created} created, {updated} updated, {skipped} skipped\n'
        )
