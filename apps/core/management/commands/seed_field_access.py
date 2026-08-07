"""
seed_field_access — One Setting record per model defining role-based field access.

Usage:
    ./bin/python manage.py seed_field_access
    ./bin/python manage.py seed_field_access --force   # overwrite existing

Each Setting record (purpose='field_access') contains:
  data.roles.<role> = { view: [...], edit: [...], create: bool, delete: bool }
  data.publish.<channel> = [fields visible externally]
  data.query_scope.<role> = { <filter_field>: "$user.org_ids.<type>" }

Roles:
  admin       — all fields, view+edit (id/ida/uuid view-only)
  manager     — most fields, edit business fields
  sales       — customer-facing fields
  warehouse   — inventory/shipping fields
  accounting  — financial fields (view-only in WC — accounting is external)
  customer    — own data only, limited fields, no edit
  vendor      — own data only, supply-related fields, no edit
  rep         — commission-relevant fields

Query scoping:
  customer role  → queries filtered by customer_id IN $user.org_ids.customer
  vendor role    → queries filtered by vendor_id IN $user.org_ids.vendor
  rep role       → queries filtered by rep_id or salesperson-linked records

This is the SINGLE SOURCE OF TRUTH for field access per model.
wcapi/get reads this Setting to scope queries and filter response fields.
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta


# System fields — always view-only for everyone
SYSTEM_VIEW_ONLY = ['id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version', 'is_deleted', 'is_archived', 'is_locked', 'security_level']

# Fields nobody should edit via API
NEVER_EDIT = ['id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version', 'is_deleted', 'is_archived', 'is_locked', 'security_level', 'search_vector']


def _get_model_fields(model_key):
    """Get all field names for a model."""
    meta = get_model_meta(model_key)
    if not meta:
        return []
    try:
        model_cls = meta.import_model()
        return [f.name for f in model_cls._meta.get_fields() if hasattr(f, 'column')]
    except Exception:
        return []


def _get_model_field_map(model_key):
    """Get {field_name: field_object} for a model."""
    meta = get_model_meta(model_key)
    if not meta:
        return {}
    try:
        model_cls = meta.import_model()
        return {f.name: f for f in model_cls._meta.get_fields() if hasattr(f, 'column')}
    except Exception:
        return {}


def _all_except(fields, exclude):
    """All fields except the excluded ones."""
    return [f for f in fields if f not in exclude]


# ─────────────────────────────────────────────────────────────────────────────
# Field behavior detection — auto-detect from field names and Django types
# ─────────────────────────────────────────────────────────────────────────────

# Status/select options shared across models
STATUS_OPTIONS = [
    {'value': 'active', 'label': 'Active'},
    {'value': 'prospect', 'label': 'Prospect'},
    {'value': 'inactive', 'label': 'Inactive'},
    {'value': 'retired', 'label': 'Retired'},
]

PRICE_LEVEL_OPTIONS = [
    {'value': 'retail', 'label': 'Retail'},
    {'value': 'wholesale', 'label': 'Wholesale'},
    {'value': 'distributor', 'label': 'Distributor'},
    {'value': 'sample', 'label': 'Sample'},
]

TX_STATUS_OPTIONS = [
    {'value': 'planned', 'label': 'Planned'},
    {'value': 'released', 'label': 'Released'},
    {'value': 'in_progress', 'label': 'In Progress'},
    {'value': 'hold', 'label': 'Hold'},
    {'value': 'complete', 'label': 'Complete'},
    {'value': 'canceled', 'label': 'Canceled'},
]

KANBAN_OPTIONS = [
    {'value': 'backlog', 'label': 'Backlog'},
    {'value': 'todo', 'label': 'To Do'},
    {'value': 'in_progress', 'label': 'In Progress'},
    {'value': 'review', 'label': 'Review'},
    {'value': 'done', 'label': 'Done'},
]

PAYMENT_TYPE_OPTIONS = [
    {'value': 'received', 'label': 'Received (AR)'},
    {'value': 'disbursed', 'label': 'Disbursed (AP)'},
]

LINE_TYPE_OPTIONS = [
    {'value': 'product', 'label': 'Product'},
    {'value': 'tax', 'label': 'Tax'},
    {'value': 'shipping', 'label': 'Shipping'},
    {'value': 'discount', 'label': 'Discount'},
]


def _build_field_behaviors(model_key, field_map):
    """Auto-detect UI behaviors from field names and Django field types."""
    behaviors = {}

    for name, field in field_map.items():
        ftype = field.__class__.__name__

        # ── System fields — readonly ──
        if name in SYSTEM_VIEW_ONLY:
            behaviors[name] = {'type': 'readonly'}
            continue

        # ── Email fields — mailto action ──
        if ftype == 'EmailField' or name == 'email':
            behaviors[name] = {'type': 'email', 'action': 'mailto'}
            continue

        # ── Phone fields — tel action ──
        if name in ('phone', 'number', 'phone_cell') or (name.startswith('phone') and ftype == 'CharField'):
            behaviors[name] = {'type': 'phone', 'action': 'tel'}
            continue

        # ── Address fields — map action ──
        if name in ('address_full', 'full'):
            behaviors[name] = {'type': 'address', 'action': 'map'}
            continue

        # ── Geo fields — map action with pair ──
        if name == 'latitude':
            behaviors[name] = {'type': 'geo', 'action': 'map', 'pair': 'longitude'}
            continue
        if name == 'longitude':
            behaviors[name] = {'type': 'geo', 'action': 'map', 'pair': 'latitude'}
            continue

        # ── URL/domain fields — link action ──
        if name in ('path', 'domain') and model_key in ('domain',):
            behaviors[name] = {'type': 'url', 'action': 'link'}
            continue

        # ── Boolean fields ──
        if ftype == 'BooleanField':
            behaviors[name] = {'type': 'boolean'}
            continue

        # ── Date/timestamp fields ──
        if ftype in ('DateTimeField', 'DateField'):
            behaviors[name] = {'type': 'date'}
            continue
        if name.startswith('dt_') and ftype in ('BigIntegerField', 'IntegerField'):
            behaviors[name] = {'type': 'timestamp'}
            continue

        # ── Decimal/currency fields ──
        if ftype == 'DecimalField' and name in ('amount', 'total', 'balance', 'value_original', 'value_available',
                                                  'fee_amount', 'cost_snapshot', 'discount_potential'):
            behaviors[name] = {'type': 'currency'}
            continue
        if ftype in ('DecimalField', 'FloatField') and name not in ('latitude', 'longitude', 'scrap_factor', 'yield_pct'):
            behaviors[name] = {'type': 'number'}
            continue

        # ── JSON fields ──
        if ftype == 'JSONField':
            # Envelope fields get the tree editor — all editable for expert users
            if name in ('metadata', 'prefs', 'config', 'refs'):
                behaviors[name] = {'type': 'json-tree'}
            else:
                behaviors[name] = {'type': 'json'}
            continue

        # ── FK fields — lookup from related model ──
        if hasattr(field, 'related_model') and field.related_model is not None:
            related = field.related_model
            related_name = related.__name__.lower() if related else ''
            # Map to model_name for wcapi lookup
            model_map = {
                'contact': 'contact', 'orgbase': 'customer', 'customer': 'customer',
                'invoice': 'invoice', 'item': 'item', 'glaccount': 'gl_account',
                'gljournal': 'gl_journal', 'paymentmethod': 'payment_method',
                'paymentterm': 'term', 'warehouse': 'warehouse', 'setting': 'setting',
                'catalog': 'catalog',
            }
            lookup_model = model_map.get(related_name, related_name)
            # Determine display field
            display = 'display_name' if related_name in ('orgbase', 'customer') else 'name' if hasattr(related, 'name') else 'ida'
            behaviors[name] = {'type': 'lookup', 'model': lookup_model, 'display': display}
            continue

        # ── Select list fields (by name convention) ──
        if name == 'status' and model_key in ('customer', 'vendor', 'manufacturer', 'employee', 'rep'):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': STATUS_OPTIONS}
            continue
        if name == 'status' and model_key in ('invoice', 'order', 'proposal', 'purchase', 'work_order', 'requisition'):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': TX_STATUS_OPTIONS}
            continue
        if name == 'price_level':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PRICE_LEVEL_OPTIONS}
            continue
        if name == 'kanban_column':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': KANBAN_OPTIONS}
            continue
        if name == 'type' and model_key == 'payment':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PAYMENT_TYPE_OPTIONS}
            continue
        if name == 'line_type' and model_key.endswith('_line'):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': LINE_TYPE_OPTIONS}
            continue
        if name == 'org_type':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': [
                {'value': 'customer', 'label': 'Customer'}, {'value': 'vendor', 'label': 'Vendor'},
                {'value': 'manufacturer', 'label': 'Manufacturer'}, {'value': 'employee', 'label': 'Employee'},
                {'value': 'rep', 'label': 'Rep'},
            ]}
            continue
        if name == 'output_type' and model_key == 'report':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': [
                {'value': 'print', 'label': 'Print/PDF'}, {'value': 'email', 'label': 'Email'},
                {'value': 'export', 'label': 'CSV/Excel'}, {'value': 'label', 'label': 'Label'},
                {'value': 'json', 'label': 'JSON'}, {'value': 'api', 'label': 'API POST'},
            ]}
            continue
        if name == 'category' and model_key in ('gl_account',):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': [
                {'value': 'cash', 'label': 'Cash'}, {'value': 'receivables', 'label': 'Receivables'},
                {'value': 'inventory', 'label': 'Inventory'}, {'value': 'payables', 'label': 'Payables'},
                {'value': 'sales', 'label': 'Sales'}, {'value': 'cogs', 'label': 'COGS'},
                {'value': 'expense', 'label': 'Expense'}, {'value': 'equity', 'label': 'Equity'},
            ]}
            continue
        if name == 'type' and model_key == 'gl_account':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': [
                {'value': 'asset', 'label': 'Asset'}, {'value': 'liability', 'label': 'Liability'},
                {'value': 'equity', 'label': 'Equity'}, {'value': 'revenue', 'label': 'Revenue'},
                {'value': 'expense', 'label': 'Expense'},
            ]}
            continue

        # ── Long text ──
        if ftype == 'TextField':
            behaviors[name] = {'type': 'textarea'}
            continue

        # ── Default: text ──
        if ftype == 'CharField':
            behaviors[name] = {'type': 'text'}

    return behaviors


def _build_field_groups(model_key, fields):
    """Auto-generate field groups based on field name patterns.

    Group order matters — users see Identity first, then the groups most
    likely to contain what they're looking for. Communication is placed
    early because contact/order records are looked up by email/phone/address
    more often than by system IDs or dates.
    """
    # Ordered dict — insertion order = display order
    groups = {
        'identity': {'label': 'Identity', 'fields': []},
        'communication': {'label': 'Communication', 'fields': []},
        'financial': {'label': 'Financial', 'fields': []},
        'status': {'label': 'Status', 'fields': []},
        'dates': {'label': 'Dates', 'fields': []},
        'system': {'label': 'System', 'fields': []},
        'json': {'label': 'Data', 'fields': []},
    }

    json_envelope_fields = {
        'metadata', 'refs', 'prefs', 'config', 'comments', 'actions',
        'cost', 'sell', 'totals', 'commission', 'finance', 'flow',
        'source', 'price', 'quantity', 'physical', 'tax', 'item',
        'catalog', 'flags', 'spec', 'quality', 'bom', 'routing',
        'tracking', 'dimensions', 'hazmat', 'compliance', 'yield_data',
        'conditions', 'scoring', 'benchmark',
    }
    system_fields = {'id', 'uuid', 'version', 'security_level',
                     'health_rating', 'parent_id', 'parent_model',
                     'line_increment'}
    # FK ID fields — these are internal references, not identity
    fk_id_fields = {'email_id', 'phone_id', 'domain_id', 'address_id',
                    'conditions_id', 'terms_fk'}
    financial_fields = {'total', 'balance', 'cost', 'sell', 'totals',
                        'commission', 'price_level', 'terms', 'discount',
                        'amount', 'tax_rate', 'margin'}
    comm_fields = {'email', 'phone', 'fax', 'mobile', 'website', 'url'}
    status_fields = {'status', 'priority', 'stage', 'state'}

    for name in fields:
        if name in json_envelope_fields:
            groups['json']['fields'].append(name)
        elif name in system_fields or name in fk_id_fields:
            groups['system']['fields'].append(name)
        elif name in financial_fields:
            groups['financial']['fields'].append(name)
        elif name in comm_fields or name.startswith('address'):
            groups['communication']['fields'].append(name)
        elif name in status_fields or name.startswith('is_'):
            groups['status']['fields'].append(name)
        elif name.startswith('dt_'):
            groups['dates']['fields'].append(name)
        elif name.startswith('security_') or name.startswith('health_'):
            groups['system']['fields'].append(name)
        else:
            groups['identity']['fields'].append(name)

    # Only include groups that have fields
    result = [
        {'key': k, 'label': v['label'], 'fields': v['fields']}
        for k, v in groups.items()
        if v['fields']
    ]
    return result


def _build_config(model_key, fields, overrides=None, field_map=None):
    """Build a standard field_access config for a model."""
    all_view = fields
    all_edit = _all_except(fields, NEVER_EDIT)

    # Business fields — exclude JSON blobs and system fields from basic roles
    json_fields = ['metadata', 'refs', 'prefs', 'comments', 'actions', 'data',
                   'price', 'cost', 'totals', 'sell', 'finance', 'flow', 'source',
                   'quantity', 'physical', 'tax', 'item', 'catalog', 'flags',
                   'billing', 'process', 'travel', 'rates', 'gl_accounts',
                   'contacts', 'addresses', 'domains', 'phones', 'emails',
                   'docs', 'connections', 'relations', 'financial', 'metrics',
                   'gateway_response', 'scripts', 'copyright', 'path',
                   'search_vector', 'count', 'location', 'warranty', 'site',
                   'op_data', 'answered_by', 'project_metadata']
    business_fields = _all_except(all_edit, json_fields)

    # ── Role-based field exclusions ──────────────────────────────────────
    # Customers and Reps see prices, never costs.
    # Vendors and Manufacturers see their costs to us, never our prices.
    # Decision: 2026-08-06. Review due: 2026-11-06.

    # Cost fields — hidden from customer and rep roles
    COST_FIELDS = {'cost', 'margin', 'margin_pct', 'margin_velocity',
                   'annual_turns', 'margin_floor'}

    # Price fields — hidden from vendor and manufacturer roles
    PRICE_FIELDS = {'price', 'sell', 'price_level', 'universal_pct'}

    # Customer-visible fields — conservative whitelist, no cost data
    customer_view = [f for f in fields if f in (
        'id', 'ida', 'display_name', 'name', 'status', 'email', 'phone',
        'address_full', 'attention', 'total', 'balance', 'dt_created',
        'description', 'sku', 'kind', 'uom', 'question', 'answer',
    )]

    # Vendor-visible fields — no price data
    vendor_view = [f for f in fields if f in (
        'id', 'ida', 'display_name', 'name', 'status', 'email', 'phone',
        'total', 'dt_created', 'description', 'sku', 'availability',
    )]

    # Rep-visible fields — sees prices, never costs
    rep_view = _all_except(all_view, list(COST_FIELDS))

    config = {
        'roles': {
            'admin': {
                'view': '*',
                'edit': all_edit,
                'create': True,
                'delete': True,
            },
            'manager': {
                'view': '*',
                'edit': business_fields,
                'create': True,
                'delete': True,
            },
            'sales': {
                'view': all_view,
                'edit': [f for f in business_fields if f not in (
                    'type', 'category', 'division',
                    'debit', 'credit', 'reconciled', 'fee_amount',
                )],
                'create': True,
                'delete': False,
            },
            'warehouse': {
                'view': [f for f in all_view if f not in (
                    'price_level', 'terms', 'total', 'balance', 'amount',
                    'debit', 'credit', 'discount_potential',
                )],
                'edit': [f for f in business_fields if f in (
                    'status', 'description', 'name', 'display_name',
                )],
                'create': False,
                'delete': False,
            },
            'accounting': {
                'view': '*',
                'edit': [],  # WC is not an accounting program — view only
                'create': False,
                'delete': False,
            },
            'customer': {
                'view': customer_view,
                'edit': [],
                'create': False,
                'delete': False,
            },
            'vendor': {
                'view': vendor_view,
                'edit': [],
                'create': False,
                'delete': False,
            },
            'rep': {
                'view': rep_view,
                'edit': [],
                'create': False,
                'delete': False,
            },
        },
        'query_scope': {},
        'publish': {
            'web': customer_view[:8],
            'api': customer_view,
            'partner': ['id', 'ida', 'display_name', 'name', 'email'],
        },
        'field_behaviors': _build_field_behaviors(model_key, field_map or {}),
        'field_groups': _build_field_groups(model_key, fields),
        'default_collapsed': ['system', 'dates'],
        'formatting': {
            'currency': 'USD',
            'locale': 'en-US',
            'date_format': 'short',  # short | medium | long | iso
            'number_precision': 2,
        },
    }

    # Add query scoping for transaction models
    if model_key in ('order', 'invoice', 'proposal', 'purchase', 'work_order', 'requisition'):
        config['query_scope'] = {
            'customer': {'customer_id__in': '$user.org_ids.customer'},
            'vendor': {'vendor_id__in': '$user.org_ids.vendor'},
            'rep': {},  # TODO: filter by sales rep linkage
        }
    elif model_key in ('order_line', 'invoice_line', 'proposal_line', 'purchase_line', 'work_order_line', 'requisition_line'):
        config['query_scope'] = {
            'customer': {},  # scoped via parent header
            'vendor': {},
        }
    elif model_key in ('customer', 'vendor', 'manufacturer', 'employee', 'rep'):
        config['query_scope'] = {
            'customer': {'id__in': '$user.org_ids.customer'},
            'vendor': {'id__in': '$user.org_ids.vendor'},
        }
    elif model_key == 'payment':
        config['query_scope'] = {
            'customer': {'contact_id': '$user.contact_id'},
            'vendor': {'contact_id': '$user.contact_id'},
        }
    elif model_key in ('email', 'phone', 'address', 'domain'):
        config['query_scope'] = {
            'customer': {'contact_id': '$user.contact_id'},
            'vendor': {'contact_id': '$user.contact_id'},
        }
    elif model_key == 'ledger':
        config['query_scope'] = {
            'customer': {'org_id__in': '$user.org_ids.customer'},
            'vendor': {'org_id__in': '$user.org_ids.vendor'},
        }
    elif model_key == 'question_answer':
        config['query_scope'] = {
            'customer': {'parent_id__in': '$user.org_ids.customer'},
        }

    # Apply overrides
    if overrides:
        for role, role_overrides in overrides.items():
            if role in config['roles']:
                config['roles'][role].update(role_overrides)

    return config


# Model-specific overrides
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


class Command(BaseCommand):
    help = 'Seed field_access Setting records — one per model with role-based view/edit matrix'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing')

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = updated = skipped = errors = 0

        for model_key in sorted(MODEL_REGISTRY.keys()):
            field_map = _get_model_field_map(model_key)
            fields = list(field_map.keys())
            if not fields:
                errors += 1
                continue

            config = _build_config(model_key, fields, OVERRIDES.get(model_key), field_map)

            existing = Setting.objects.filter(
                parent_model=model_key,
                purpose='field_access',
            ).first()

            if existing and not force:
                skipped += 1
                continue

            if existing:
                existing.config = config
                existing.save()
                updated += 1
            else:
                Setting.objects.create(
                    name=f'field_access:{model_key}',
                    parent_model=model_key,
                    purpose='field_access',
                    config=config,
                )
                created += 1

            self.stdout.write(f'  {model_key}: {len(fields)} fields, {len(config["roles"])} roles')

        self.stdout.write(self.style.SUCCESS(
            f'Field access: {created} created, {updated} updated, {skipped} skipped, {errors} errors'
        ))
