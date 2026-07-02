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


# Fields that should appear first in detail (by priority)
HIGH_PRIORITY_DETAIL = [
    'ida', 'display_name', 'name', 'email', 'status',
    'total', 'balance', 'amount',
    'description', 'company', 'title',
    'phone', 'address_full', 'attention',
    'price_level', 'terms', 'priority',
    'account_number', 'account',
    'line_number', 'quantity', 'price', 'cost',
    'item', 'customer', 'vendor', 'manufacturer', 'contact',
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

# Fields good for list view (compact, scalar)
GOOD_LIST_FIELDS = [
    'ida', 'display_name', 'name', 'email', 'status',
    'total', 'balance', 'amount',
    'company', 'phone', 'title',
    'account_number', 'account', 'type', 'category',
    'priority', 'price_level', 'terms',
    'line_number', 'org_type',
    'debit', 'credit', 'source', 'source_model',
    'kind', 'uom', 'sku',
    'is_active', 'dt_created',
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
        })
    return fields


def _build_alice_guess(model_cls):
    """Build Alice's best guess at important field order.

    List: compact scalars only, no JSON objects, max 8 columns.
    Detail: high-priority fields first, then remaining, low-priority last.
    """
    field_info = _get_field_info(model_cls)
    all_names = [f['name'] for f in field_info]

    # --- List ---
    list_fields = []
    # First: add known good list fields in priority order
    for gf in GOOD_LIST_FIELDS:
        if gf in all_names and gf not in list_fields:
            # Check it's not a JSON field
            info = next((f for f in field_info if f['name'] == gf), None)
            if info and not info['is_json']:
                list_fields.append(gf)
    # Fill up to 8 with remaining char/number fields
    for f in field_info:
        if len(list_fields) >= 8:
            break
        if f['name'] not in list_fields and f['name'] not in EXCLUDE_FROM_LIST and not f['is_json']:
            list_fields.append(f['name'])

    # --- Detail ---
    detail_fields = []
    remaining = set(all_names)

    # High priority first (in order)
    for hp in HIGH_PRIORITY_DETAIL:
        if hp in remaining:
            detail_fields.append(hp)
            remaining.discard(hp)

    # Middle: everything not in high or low priority, alphabetically
    low_set = set(LOW_PRIORITY_DETAIL)
    middle = sorted(remaining - low_set)
    detail_fields.extend(middle)

    # Low priority last (in order)
    for lp in LOW_PRIORITY_DETAIL:
        if lp in remaining:
            detail_fields.append(lp)

    return list_fields, detail_fields


def _build_alphabetical(model_cls):
    """All fields sorted alphabetically."""
    field_info = _get_field_info(model_cls)
    all_names = sorted(f['name'] for f in field_info)

    # List: alpha but exclude JSON and internal fields
    list_fields = [
        n for n in all_names
        if n not in EXCLUDE_FROM_LIST
        and not any(f['name'] == n and f['is_json'] for f in field_info)
    ][:10]

    return list_fields, all_names


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
                purpose='workbench_fields',
            ).first()

            if not setting:
                # Create new with both layouts as views
                Setting.objects.create(
                    name=f'workbench_fields:{model_key}',
                    parent_model=model_key,
                    purpose='workbench_fields',
                    data={
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
                data = setting.data or {}
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

                setting.data = data
                setting.dt_modified = _now_ms()
                setting.save(update_fields=['data', 'dt_modified'])
                updated += 1
                self.stdout.write(f'  Updated {model_key}: alice_guess ({len(alice_list)}L/{len(alice_detail)}D), alphabetical ({len(alpha_list)}L/{len(alpha_detail)}D)')

        self.stdout.write(self.style.SUCCESS(
            f'Alice layouts: {created} created, {updated} updated, {skipped} skipped'
        ))
