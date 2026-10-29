"""
seed_model_definitions — One Setting record per model (purpose='wc:model').

Consolidates field_access, enrichment_panels, detail_layout,
workbench_fields and db_defaults into a single config per model.

Usage:
    python manage.py seed_model_definitions
    python manage.py seed_model_definitions --force     # overwrite existing
    python manage.py seed_model_definitions --dry-run   # report only
    python manage.py seed_model_definitions --model order  # one model only

Config structure:
    {
        "access":       { roles, query_scope, publish },
        "behaviors":    { field_name: { type, action, ... }, ... },
        "field_groups":  [ { key, label, fields }, ... ],
        "selectlists": { field: [ {value, label}, ... ] },   (purpose: the door enforces it)
        "formatting":   { currency, locale, date_format, number_precision },
        "enrichment":   { panels: [ ... ] },
        "layout":       { list, column, detail, form, panel, card, tabs }  (apps/core/layouts)
        "searches":     [],
        "defaults":     {},
    }

Salvage strategy: reads existing records for each sub-purpose and merges
their config into the combined structure. Auto-generates what's missing.
"""
from django.core.management.base import BaseCommand
from apps.core import layouts
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.services.field_behaviors import (
    get_field_behaviors, get_field_groups, get_model_field_map, SEED_PURPOSES, USER_DEFINED_PURPOSE,
)


# ─── Access section (roles, query_scope, publish) ────────────────────────

COST_FIELDS = {
    'cost', 'margin', 'margin_pct', 'margin_velocity',
    'annual_turns', 'margin_floor',
}
PRICE_FIELDS = {'price', 'sell', 'price_level', 'universal_pct'}

OVERRIDES = {
    'customer': {
        'customer': {'edit': ['email', 'phone', 'attention', 'address_full']},
    },
    'vendor': {
        'vendor': {'edit': ['email', 'phone', 'attention', 'address_full']},
    },
    'item': {
        'customer': {'view': ['id', 'ida', 'name', 'description', 'sku', 'kind', 'uom', 'status']},
        'vendor': {'view': ['id', 'ida', 'name', 'description', 'sku', 'kind', 'uom', 'status', 'availability']},
    },
    'setting': {
        'customer': {'view': []},
        'vendor': {'view': []},
        'sales': {'view': [], 'edit': [], 'create': False},
    },
    'gl_account': {
        'customer': {'view': []},
        'vendor': {'view': []},
        'sales': {'view': []},
    },
    'gl_journal': {
        'customer': {'view': []},
        'vendor': {'view': []},
        'sales': {'view': []},
    },
    'contact': {
        'customer': {'view': ['id', 'email', 'name_first', 'name_last', 'phone', 'company'], 'edit': ['phone']},
        'vendor': {'view': ['id', 'email', 'name_first', 'name_last', 'phone', 'company']},
    },
}


def _build_access(model_key):
    """Default positive lists for a new model Setting (apps/core/services/access.py)."""
    from apps.core.services.access import default_access
    return default_access(model_key)

def _build_query_scope(model_key):
    if model_key in ('order', 'invoice', 'quote', 'purchase', 'workorder', 'requisition'):
        return {
            'customer': {'customer_id__in': '$user.org_ids.customer'},
            'vendor': {'vendor_id__in': '$user.org_ids.vendor'},
            'rep': {},
        }
    elif model_key in ('order_line', 'invoice_line', 'quote_line', 'purchase_line',
                        'workorder_line', 'requisition_line'):
        return {'customer': {}, 'vendor': {}}
    elif model_key in ('customer', 'vendor', 'manufacturer', 'employee', 'rep'):
        return {
            'customer': {'id__in': '$user.org_ids.customer'},
            'vendor': {'id__in': '$user.org_ids.vendor'},
        }
    elif model_key == 'cash':
        return {
            'customer': {'contact_id': '$user.contact_id'},
            'vendor': {'contact_id': '$user.contact_id'},
        }
    elif model_key in ('email', 'phone', 'address', 'domain'):
        return {
            'customer': {'contact_id': '$user.contact_id'},
            'vendor': {'contact_id': '$user.contact_id'},
        }
    elif model_key == 'ledger':
        return {
            'customer': {'org_id__in': '$user.org_ids.customer'},
            'vendor': {'org_id__in': '$user.org_ids.vendor'},
        }
    elif model_key == 'question_answer':
        return {'customer': {'parent_id__in': '$user.org_ids.customer'}}
    return {}


# ─── Behaviors and field groups now live in apps.core.services.field_behaviors


# ─── Salvage existing records ────────────────────────────────────────────

SALVAGE_PURPOSES = [
    'wc:enrichment_panels',
    'wc:db_defaults',
]


def _salvage_existing(model_key):
    """Read existing Setting records for this model and return salvaged config sections."""
    salvaged = {}
    existing = Setting.objects.filter(
        parent_model=model_key,
        purpose__in=SALVAGE_PURPOSES,
        is_active=True,
        )
    for s in existing:
        cfg = s.config or {}
        if s.purpose == 'wc:enrichment_panels':
            salvaged['enrichment'] = cfg
        elif s.purpose == 'wc:db_defaults':
            salvaged['defaults'] = cfg
    return salvaged


# ─── Build combined config ───────────────────────────────────────────────

def build_model_config(model_key):
    """Build the combined wc:model config for one model."""
    field_map = get_model_field_map(model_key)
    fields = list(field_map.keys())

    # Try salvage first, fall back to auto-generation
    salvaged = _salvage_existing(model_key)

    config = {
        'access': salvaged.get('access') or (
            _build_access(model_key) if fields else {}
        ),
        'behaviors': get_field_behaviors(model_key, field_map),
        'field_groups': get_field_groups(model_key, fields),
        'selectlists': ({'purpose': SEED_PURPOSES.get(model_key) or [USER_DEFINED_PURPOSE]}
                        if 'purpose' in field_map else {}),
        'formatting': salvaged.get('formatting') or {
            'currency': 'USD',
            'locale': 'en-US',
            'date_format': 'short',
            'number_precision': 2,
        },
        'default_collapsed': salvaged.get('default_collapsed') or ['system', 'dates', 'json'],
        'enrichment': salvaged.get('enrichment', {}),
        'layout': layouts.build(model_key),
        'searches': [],
        'defaults': salvaged.get('defaults', {}),
    }
    return config


# ─── Command ─────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed wc:model Setting records — one per model with combined definition'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing (requires confirmation)')
        parser.add_argument('--dry-run', action='store_true', help='Report only')
        parser.add_argument('--model', type=str, default=None, help='Seed one model only')
        parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        target = options.get('model')
        skip_confirm = options.get('yes', False)
        created = updated = skipped = errors = 0

        models = {target: MODEL_REGISTRY[target]} if target and target in MODEL_REGISTRY else MODEL_REGISTRY

        # --force on all models is destructive — require confirmation
        if force and not target and not dry_run and not skip_confirm:
            count = len(models)
            self.stdout.write(self.style.WARNING(
                f'\n  ⚠  --force will overwrite behaviors, access, schema, and field_groups '
                f'on {count} model Settings.\n'
                f'  config.layout is preserved (form sections, detail sections, cards).\n'
                f'  Use --model <name> to target one model, or --yes to skip this prompt.\n'
            ))
            confirm = input('  Type "yes" to proceed: ')
            if confirm.strip().lower() != 'yes':
                self.stdout.write('Aborted.')
                return

        for model_key in sorted(models.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                errors += 1
                self.stderr.write(f'  {model_key}: not in registry')
                continue

            # Use meta.key for DB operations — Setting.clean() normalizes
            # parent_model to meta.key, so lookups must match.
            canonical_key = meta.key

            try:
                config = build_model_config(model_key)
            except Exception as e:
                errors += 1
                self.stderr.write(f'  {model_key}: {e}')
                continue

            if dry_run:
                section_count = sum(1 for v in config.values() if v)
                self.stdout.write(f'  {model_key}: {section_count} sections')
                created += 1
                continue

            existing = Setting.objects.filter(
                parent_model=canonical_key,
                purpose='wc:model',
            ).first()

            if existing and not force:
                skipped += 1
                continue

            expl = (
                f"Model definition for {meta.singular}. "
                f"Governs named layouts (list columns, detail fields, ui sections), "
                f"field behaviors, schema metadata, and access configuration."
            )

            if existing:
                # MERGE, not REPLACE.
                # Seed regenerates: behaviors, access, schema, field_groups,
                #   formatting, searches, defaults, enrichment. selectlists are kept.
                # config.layout is the company's: kept, only the parts it lacks are added
                #   (apps/core/layouts); staff reset one part with POST /wcapi/_layout_reset/.
                config['layout'] = layouts.fill(model_key, (existing.config or {}).get('layout'))[0]
                # Select lists are an administrator's (purposes among them): kept as they are.
                old_lists = (existing.config or {}).get('selectlists')
                if isinstance(old_lists, dict):
                    config['selectlists'] = old_lists

                existing.config = config
                existing.name = f'{meta.singular} Model Definition'
                existing.explanation = expl
                existing.save()
                updated += 1
            else:
                Setting.authorized_create(
                    name=f'{meta.singular} Model Definition',
                    ida=f'wc-model-{model_key}',
                    parent_model=canonical_key,
                    purpose='wc:model',
                    scope='system',
                    config=config,
                    explanation=expl,
                )
                created += 1

            section_count = sum(1 for v in config.values() if v)
            self.stdout.write(f'  {model_key}: {section_count} sections')

        action = 'Would create' if dry_run else 'Done'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action}: {created} created, {updated} updated, '
            f'{skipped} skipped, {errors} errors'
        ))
