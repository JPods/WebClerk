"""
seed_alice_layouts — Create two protected layouts for every model in the DataBrowser.

1. "alice_guess" — Alice's best guess at important field order for detail view.
   Lists show compact columns (ida, name/display_name, status, key scalars).
   JSON objects are excluded from lists (they belong in detail view).

2. "alphabetical" — All fields sorted alphabetically.
   Both list and detail use the same alpha-sorted order.

Both layouts are protected — users cannot overwrite them, but can load them
and "Save As" to create their own version.

Usage:
    ./manage.py seed_alice_layouts              # create/update both layouts
    ./manage.py seed_alice_layouts --force       # overwrite even if they exist
"""
from django.core.management.base import BaseCommand
from django.db import models as dj_models
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.models.setting import Setting
import time


def _now_ms():
    return int(time.time() * 1000)


# Fields that should appear first in detail — WHO, ACTION, WHEN, WHAT, STATUS, WHERE, WHY
HIGH_PRIORITY_DETAIL = [
    # WHO — identify the person/entity first
    'name_first', 'name_last', 'name_prefix', 'name_suffix',
    'display_name', 'name', 'company', 'attention',
    'customer', 'vendor', 'manufacturer', 'contact',
    'ida',
    # ACTION — what's happening
    'item', 'line_number', 'quantity', 'price', 'cost', 'commission',
    'total', 'balance', 'amount',
    'account', 'debit', 'credit',
    # WHAT — details
    'description', 'title', 'email', 'phone',
    'price_level', 'terms', 'priority',
    # STATUS
    'status', 'kanban_column',
    # WHERE
    'address_full',
]

# Fields that should appear last in detail
LOW_PRIORITY_DETAIL = [
    'metadata', 'refs', 'prefs', 'actions', 'comments',
    'stats', 'relationship_stats',
    'uuid', 'version', 'security_level',
    'is_deleted', 'is_archived', 'is_locked',
    'health_rating', 'search_vector',
    'dt_created', 'dt_modified',
]

# Fields good for list view (compact, scalar — NO timestamps)
GOOD_LIST_FIELDS = [
    # WHO
    'ida', 'display_name', 'name', 'company',
    # ACTION / WHAT
    'status', 'total', 'balance', 'amount',
    'email', 'phone', 'title',
    'account', 'type', 'category',
    'priority', 'price_level', 'terms',
    'line_number', 'org_type',
    'debit', 'credit', 'source', 'source_model',
    'kind', 'uom', 'sku',
    'is_active',
    # dt_created/dt_modified deliberately excluded — not important in lists
]

# JSON fields to exclude from lists (belong in detail only)
JSON_FIELD_TYPES = (
    dj_models.JSONField,
)

# Internal fields to always exclude from lists
EXCLUDE_FROM_LIST = {
    'id', 'uuid', 'version', 'security_level', 'health_rating',
    'is_deleted', 'is_archived', 'is_locked',
    'metadata', 'refs', 'prefs', 'actions', 'comments',
    'stats', 'relationship_stats', 'search_vector',
    'password', 'last_login',
    'dt_created', 'dt_modified',  # timestamps not important in lists
}


def _get_field_info(model_cls):
    """Get all concrete fields with their types."""
    fields = []
    for f in model_cls._meta.get_fields():
        if not hasattr(f, 'column'):
            continue  # skip relations without columns
        fields.append({
            'name': f.name,
            'is_json': isinstance(f, JSON_FIELD_TYPES),
            'is_fk': isinstance(f, (dj_models.ForeignKey,)),
            'is_char': isinstance(f, (dj_models.CharField, dj_models.EmailField, dj_models.TextField)),
            'is_number': isinstance(f, (dj_models.IntegerField, dj_models.DecimalField, dj_models.FloatField, dj_models.BigIntegerField)),
            'is_bool': isinstance(f, dj_models.BooleanField),
            'is_date': isinstance(f, (dj_models.DateField, dj_models.DateTimeField)),
            'is_decimal': isinstance(f, dj_models.DecimalField),
        })
    return fields


def _field_spec(name, field_info=None):
    """Build a FieldSpec dict with smart defaults — mirrors wc2 listboxK._setColumnName."""
    spec = {'field': name, 'visible': True}
    fl = name.lower()

    # WHO — names
    if fl in ('display_name', 'company', 'name'):
        spec.update(width=180, align='left')
    elif fl in ('name_first', 'name_last'):
        spec.update(width=120, align='left')
    elif fl in ('attention',):
        spec.update(width=140, align='left')
    # Identifiers
    elif fl in ('ida', 'sku'):
        spec.update(width=100, align='left')
    elif fl == 'id':
        spec.update(width=60, align='right')
    # Contact info
    elif 'phone' in fl:
        spec.update(width=120, align='left', format='phone')
    elif 'email' in fl:
        spec.update(width=180, align='left')
    elif 'zip' in fl or 'postal' in fl:
        spec.update(width=70, align='left')
    elif fl in ('state', 'province'):
        spec.update(width=60, align='center')
    elif 'address' in fl:
        spec.update(width=220, align='left')
    elif fl == 'city':
        spec.update(width=120, align='left')
    elif fl == 'country':
        spec.update(width=80, align='center')
    # Text
    elif fl in ('description', 'title'):
        spec.update(width=220, align='left')
    elif fl in ('notes', 'comments'):
        spec.update(width=200, align='left', wrap=True)
    # Terms / level (must check before price pattern)
    elif fl in ('terms', 'price_level'):
        spec.update(width=80, align='left')
    # Currency
    elif any(k in fl for k in ('price', 'cost', 'extended')) or fl in ('total', 'balance', 'amount', 'debit', 'credit'):
        spec.update(width=100, align='right', format='currency')
    # Rates
    elif any(k in fl for k in ('rate', 'percent')) or fl in ('discount', 'commission'):
        spec.update(width=80, align='right', format='percent')
    # Weight
    elif 'weight' in fl or fl.endswith('_wt'):
        spec.update(width=60, align='right', format='number')
    # Quantities
    elif fl in ('qty', 'quantity', 'line_number', 'sequence') or fl.startswith('qty_'):
        spec.update(width=60, align='right')
    # Status/type
    elif fl in ('status', 'type', 'category', 'kind', 'org_type', 'kanban_column', 'priority'):
        spec.update(width=100, align='left')
    # Dates
    elif fl.startswith('dt_') or 'date' in fl or '_dt' in fl or fl in ('deadline_by', 'start_by', 'end_by', 'expected_by', 'completed_by'):
        spec.update(width=100, align='center', format='date')
    # Booleans
    elif fl.startswith('is_'):
        spec.update(width=50, align='center')
    # Small numbers
    elif fl in ('version', 'security_level', 'health_rating', 'difficulty', 'burndown', 'linkage', 'count_accessed'):
        spec.update(width=60, align='right')
    # JSON
    elif fl in ('metadata', 'refs', 'prefs', 'actions', 'stats'):
        spec.update(width=60, align='left', format='json')
    # UUID
    elif fl == 'uuid':
        spec.update(width=100, align='left')
    elif fl in ('uom', 'unit_of_measure'):
        spec.update(width=60, align='center')
    elif fl in ('source', 'source_model'):
        spec.update(width=100, align='left')
    # Use field_info for type-based defaults if no name match
    elif field_info:
        if field_info.get('is_bool'):
            spec.update(width=50, align='center')
        elif field_info.get('is_decimal'):
            spec.update(width=100, align='right', format='number')
        elif field_info.get('is_number'):
            spec.update(width=80, align='right')
        elif field_info.get('is_date'):
            spec.update(width=100, align='center', format='date')
        elif field_info.get('is_json'):
            spec.update(width=60, align='left', format='json')
        else:
            spec.update(width=120, align='left')
    else:
        spec.update(width=120, align='left')

    return spec


def _build_alice_guess(model_cls):
    """Build Alice's best guess at important field order.

    List: compact scalars only, no JSON objects, max 8 columns — as FieldSpec objects.
    Detail: high-priority fields first, then remaining, low-priority last — as FieldSpec objects.
    """
    field_info = _get_field_info(model_cls)
    info_map = {f['name']: f for f in field_info}
    all_names = [f['name'] for f in field_info]

    # --- List ---
    list_names = []
    for gf in GOOD_LIST_FIELDS:
        if gf in all_names and gf not in list_names:
            info = info_map.get(gf)
            if info and not info['is_json']:
                list_names.append(gf)
    for f in field_info:
        if len(list_names) >= 8:
            break
        if f['name'] not in list_names and f['name'] not in EXCLUDE_FROM_LIST and not f['is_json']:
            list_names.append(f['name'])

    list_fields = [_field_spec(n, info_map.get(n)) for n in list_names]

    # --- Detail ---
    detail_names = []
    remaining = set(all_names)

    for hp in HIGH_PRIORITY_DETAIL:
        if hp in remaining:
            detail_names.append(hp)
            remaining.discard(hp)

    low_set = set(LOW_PRIORITY_DETAIL)
    middle = sorted(remaining - low_set)
    detail_names.extend(middle)

    for lp in LOW_PRIORITY_DETAIL:
        if lp in remaining:
            detail_names.append(lp)

    detail_fields = [_field_spec(n, info_map.get(n)) for n in detail_names]

    return list_fields, detail_fields


def _build_alphabetical(model_cls):
    """All fields sorted alphabetically — as FieldSpec objects."""
    field_info = _get_field_info(model_cls)
    info_map = {f['name']: f for f in field_info}
    all_names = sorted(f['name'] for f in field_info)

    list_names = [
        n for n in all_names
        if n not in EXCLUDE_FROM_LIST
        and not any(f['name'] == n and f['is_json'] for f in field_info)
    ][:10]

    list_fields = [_field_spec(n, info_map.get(n)) for n in list_names]
    detail_fields = [_field_spec(n, info_map.get(n)) for n in all_names]

    return list_fields, detail_fields


class Command(BaseCommand):
    help = 'Create alice_guess and alphabetical protected layouts for all models'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing layouts')

    def handle(self, *args, **options):
        force = options.get('force', False)
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

            alice_list, alice_detail = _build_alice_guess(model_cls)
            alpha_list, alpha_detail = _build_alphabetical(model_cls)

            # Get existing setting
            setting = Setting.objects.filter(
                parent_model=model_key,
                purpose='wc:workbench_fields',
            ).first()

            if not setting:
                # Create new with both layouts as views
                Setting.objects.create(
                    name=f'workbench_fields:{model_key}',
                    parent_model=model_key,
                    purpose='wc:workbench_fields',
                    config={
                        'list': alice_list,
                        'detail': alice_detail,
                        'views': [
                            {'name': 'alice_guess', 'list': alice_list, 'detail': alice_detail, 'listWidths': {}},
                            {'name': 'alphabetical', 'list': alpha_list, 'detail': alpha_detail, 'listWidths': {}},
                        ],
                    },
                )
                created += 1
                self.stdout.write(f'  Created {model_key}: alice_guess ({len(alice_list)}L/{len(alice_detail)}D), alphabetical ({len(alpha_list)}L/{len(alpha_detail)}D)')
            else:
                # Update: add/replace alice_guess and alphabetical views, preserve user views
                data = setting.config or {}
                views = data.get('views', [])

                # Remove old alice_guess/alphabetical if they exist
                views = [v for v in views if v.get('name') not in ('alice_guess', 'alphabetical', 'initial', 'alpha', 'best_guess')]

                # Add fresh ones
                views.append({'name': 'alice_guess', 'list': alice_list, 'detail': alice_detail, 'listWidths': {}})
                views.append({'name': 'alphabetical', 'list': alpha_list, 'detail': alpha_detail, 'listWidths': {}})

                data['views'] = views

                # If current default list/detail is the old initial layout, update to alice_guess
                if force or data.get('list') == data.get('views', [{}])[0].get('list') if data.get('views') else True:
                    data['list'] = alice_list
                    data['detail'] = alice_detail

                setting.config = data
                setting.dt_modified = _now_ms()
                setting.save(update_fields=['config', 'dt_modified'])
                updated += 1
                self.stdout.write(f'  Updated {model_key}: alice_guess ({len(alice_list)}L/{len(alice_detail)}D), alphabetical ({len(alpha_list)}L/{len(alpha_detail)}D)')

        self.stdout.write(self.style.SUCCESS(
            f'Alice layouts: {created} created, {updated} updated, {skipped} skipped'
        ))
