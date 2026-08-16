"""
seed_model_definitions — One Setting record per model (purpose='wc:model').

Consolidates schema_map, field_access, enrichment_panels, detail_layout,
workbench_fields, db_defaults, and select_lists into a single config per model.

Usage:
    python manage.py seed_model_definitions
    python manage.py seed_model_definitions --force     # overwrite existing
    python manage.py seed_model_definitions --dry-run   # report only
    python manage.py seed_model_definitions --model order  # one model only

Config structure:
    {
        "schema":       { pydantic_schema, config_schema, metadata_schema, ... },
        "access":       { roles, query_scope, publish },
        "behaviors":    { field_name: { type, action, ... }, ... },
        "field_groups":  [ { key, label, fields }, ... ],
        "select_lists": { field: { label, choices, allow_custom }, ... },
        "formatting":   { currency, locale, date_format, number_precision },
        "enrichment":   { panels: [ ... ] },
        "layout":       { list: [...], panel: [...], card: [...], views: [...], detail: {...} },
        "searches":     [],
        "defaults":     {},
    }

Salvage strategy: reads existing records for each sub-purpose and merges
their config into the combined structure. Auto-generates what's missing.
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta


# ─── Constants from seed_field_access ─────────────────────────────────────

SYSTEM_VIEW_ONLY = [
    'id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'is_locked', 'security_level',
]

NEVER_EDIT = [
    'id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'is_locked', 'security_level', 'search_vector',
]


# ─── Helpers ──────────────────────────────────────────────────────────────

def _get_model_fields(model_key):
    meta = get_model_meta(model_key)
    if not meta:
        return []
    try:
        model_cls = meta.import_model()
        return [f.name for f in model_cls._meta.get_fields() if hasattr(f, 'column')]
    except Exception:
        return []


def _get_model_field_map(model_key):
    meta = get_model_meta(model_key)
    if not meta:
        return {}
    try:
        model_cls = meta.import_model()
        return {f.name: f for f in model_cls._meta.get_fields() if hasattr(f, 'column')}
    except Exception:
        return {}


def _all_except(fields, exclude):
    return [f for f in fields if f not in exclude]


def _to_class_name(key):
    return ''.join(word.capitalize() for word in key.split('_'))


# ─── Schema section ──────────────────────────────────────────────────────

def _build_schema(model_key):
    class_name = _to_class_name(model_key)
    return {
        'pydantic_schema': f'common.schemas.{model_key}',
        'config_schema': f'{class_name}Config',
        'metadata_schema': f'{class_name}Metadata',
        'prefs_schema': f'{class_name}Prefs',
        'refs_schema': f'{class_name}Refs',
    }


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


def _build_access(model_key, fields, field_map):
    all_view = fields
    all_edit = _all_except(fields, NEVER_EDIT)

    json_fields = [
        'metadata', 'refs', 'prefs', 'comments', 'actions', 'data',
        'price', 'cost', 'totals', 'sell', 'finance', 'flow', 'source',
        'quantity', 'physical', 'tax', 'item', 'catalog', 'flags',
        'billing', 'process', 'travel', 'rates', 'gl_accounts',
        'contacts', 'addresses', 'domains', 'phones', 'emails',
        'docs', 'connections', 'relations', 'financial', 'metrics',
        'gateway_response', 'scripts', 'copyright', 'path',
        'search_vector', 'count', 'location', 'warranty', 'site',
        'op_data', 'answered_by', 'project_metadata',
    ]
    business_fields = _all_except(all_edit, json_fields)

    customer_view = [f for f in fields if f in (
        'id', 'ida', 'display_name', 'name', 'status', 'email', 'phone',
        'address_full', 'attention', 'total', 'balance', 'dt_created',
        'description', 'sku', 'kind', 'uom', 'question', 'answer',
    )]
    vendor_view = [f for f in fields if f in (
        'id', 'ida', 'display_name', 'name', 'status', 'email', 'phone',
        'total', 'dt_created', 'description', 'sku', 'availability',
    )]
    rep_view = _all_except(all_view, list(COST_FIELDS))

    access = {
        'roles': {
            'admin': {'view': '*', 'edit': all_edit, 'create': True, 'delete': True},
            'manager': {'view': '*', 'edit': business_fields, 'create': True, 'delete': True},
            'sales': {
                'view': all_view,
                'edit': [f for f in business_fields if f not in (
                    'type', 'category', 'division',
                    'debit', 'credit', 'reconciled', 'fee_amount',
                )],
                'create': True, 'delete': False,
            },
            'warehouse': {
                'view': [f for f in all_view if f not in (
                    'price_level', 'terms', 'total', 'balance', 'amount',
                    'debit', 'credit', 'discount_potential',
                )],
                'edit': [f for f in business_fields if f in (
                    'status', 'description', 'name', 'display_name',
                )],
                'create': False, 'delete': False,
            },
            'accounting': {'view': '*', 'edit': [], 'create': False, 'delete': False},
            'customer': {'view': customer_view, 'edit': [], 'create': False, 'delete': False},
            'vendor': {'view': vendor_view, 'edit': [], 'create': False, 'delete': False},
            'rep': {'view': rep_view, 'edit': [], 'create': False, 'delete': False},
        },
        'query_scope': _build_query_scope(model_key),
        'publish': {
            'web': customer_view[:8],
            'api': customer_view,
            'partner': ['id', 'ida', 'display_name', 'name', 'email'],
        },
    }

    overrides = OVERRIDES.get(model_key)
    if overrides:
        for role, role_overrides in overrides.items():
            if role in access['roles']:
                access['roles'][role].update(role_overrides)

    return access


def _build_query_scope(model_key):
    if model_key in ('order', 'invoice', 'proposal', 'purchase', 'work_order', 'requisition'):
        return {
            'customer': {'customer_id__in': '$user.org_ids.customer'},
            'vendor': {'vendor_id__in': '$user.org_ids.vendor'},
            'rep': {},
        }
    elif model_key in ('order_line', 'invoice_line', 'proposal_line', 'purchase_line',
                        'work_order_line', 'requisition_line'):
        return {'customer': {}, 'vendor': {}}
    elif model_key in ('customer', 'vendor', 'manufacturer', 'employee', 'rep'):
        return {
            'customer': {'id__in': '$user.org_ids.customer'},
            'vendor': {'id__in': '$user.org_ids.vendor'},
        }
    elif model_key == 'payment':
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


# ─── Behaviors (from seed_field_access auto-detection) ────────────────────

STATUS_OPTIONS = [
    {'value': 'active', 'label': 'Active'},
    {'value': 'prospect', 'label': 'Prospect'},
    {'value': 'inactive', 'label': 'Inactive'},
    {'value': 'retired', 'label': 'Retired'},
]
TX_STATUS_OPTIONS = [
    {'value': 'planned', 'label': 'Planned'},
    {'value': 'released', 'label': 'Released'},
    {'value': 'in_progress', 'label': 'In Progress'},
    {'value': 'hold', 'label': 'Hold'},
    {'value': 'complete', 'label': 'Complete'},
    {'value': 'canceled', 'label': 'Canceled'},
]
PRICE_LEVEL_OPTIONS = [
    {'value': 'retail', 'label': 'Retail'},
    {'value': 'wholesale', 'label': 'Wholesale'},
    {'value': 'distributor', 'label': 'Distributor'},
    {'value': 'sample', 'label': 'Sample'},
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


def _build_behaviors(model_key, field_map):
    """Auto-detect UI behaviors from field names and Django field types."""
    behaviors = {}
    for name, field in field_map.items():
        ftype = field.__class__.__name__

        if name in SYSTEM_VIEW_ONLY:
            behaviors[name] = {'type': 'readonly'}
            continue
        if ftype == 'EmailField' or name == 'email':
            behaviors[name] = {'type': 'email', 'action': 'mailto'}
            continue
        if name in ('phone', 'number', 'phone_cell') or (name.startswith('phone') and ftype == 'CharField'):
            behaviors[name] = {'type': 'phone', 'action': 'tel'}
            continue
        if name in ('address_full', 'full'):
            behaviors[name] = {'type': 'address', 'action': 'map'}
            continue
        if name == 'latitude':
            behaviors[name] = {'type': 'geo', 'action': 'map', 'pair': 'longitude'}
            continue
        if name == 'longitude':
            behaviors[name] = {'type': 'geo', 'action': 'map', 'pair': 'latitude'}
            continue
        if name in ('path', 'domain') and model_key in ('domain',):
            behaviors[name] = {'type': 'url', 'action': 'link'}
            continue
        if ftype == 'BooleanField':
            behaviors[name] = {'type': 'boolean'}
            continue
        if ftype in ('DateTimeField', 'DateField'):
            behaviors[name] = {'type': 'date'}
            continue
        if name.startswith('dt_') and ftype in ('BigIntegerField', 'IntegerField'):
            behaviors[name] = {'type': 'timestamp'}
            continue
        if ftype == 'DecimalField' and name in (
            'amount', 'total', 'balance', 'value_original', 'value_available',
            'fee_amount', 'cost_snapshot', 'discount_potential',
        ):
            behaviors[name] = {'type': 'currency'}
            continue
        if ftype in ('DecimalField', 'FloatField') and name not in (
            'latitude', 'longitude', 'scrap_factor', 'yield_pct',
        ):
            behaviors[name] = {'type': 'number'}
            continue
        if ftype == 'JSONField':
            if name in ('metadata', 'prefs', 'config', 'refs'):
                behaviors[name] = {'type': 'json-tree'}
            else:
                behaviors[name] = {'type': 'json'}
            continue
        if hasattr(field, 'related_model') and field.related_model is not None:
            related = field.related_model
            related_name = related.__name__.lower() if related else ''
            model_map = {
                'contact': 'contact', 'orgbase': 'customer', 'customer': 'customer',
                'invoice': 'invoice', 'item': 'item', 'glaccount': 'gl_account',
                'gljournal': 'gl_journal', 'paymentmethod': 'payment_method',
                'paymentterm': 'term', 'warehouse': 'warehouse', 'setting': 'setting',
                'catalog': 'catalog',
            }
            lookup_model = model_map.get(related_name, related_name)
            display = 'display_name' if related_name in ('orgbase', 'customer') else 'name' if hasattr(related, 'name') else 'ida'
            behaviors[name] = {'type': 'lookup', 'model': lookup_model, 'display': display}
            continue

        # Select lists by name convention
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
        if name == 'editor_type' and model_key == 'report':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': [
                {'value': 'plain', 'label': 'Plain text'},
                {'value': 'markdown', 'label': 'Markdown'},
                {'value': 'html', 'label': 'HTML (rich text)'},
            ]}
            continue
        if name == 'content' and model_key == 'report':
            behaviors[name] = {'type': 'editor'}
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
        if ftype == 'TextField':
            behaviors[name] = {'type': 'textarea'}
            continue
        if ftype == 'CharField':
            behaviors[name] = {'type': 'text'}

    # Inject leaf behaviors for JSON envelope fields (totals.*, price.*, etc.)
    from apps.core.management.commands.seed_field_access import _inject_leaf_behaviors
    _inject_leaf_behaviors(model_key, field_map, behaviors)

    return behaviors


# ─── Field groups ─────────────────────────────────────────────────────────

def _build_field_groups(model_key, fields):
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
    system_fields = {
        'id', 'uuid', 'version', 'security_level', 'health_rating',
        'parent_id', 'parent_model', 'line_increment',
    }
    fk_id_fields = {
        'email_id', 'phone_id', 'domain_id', 'address_id',
        'conditions_id', 'terms_fk',
    }
    financial_fields = {
        'total', 'balance', 'cost', 'sell', 'totals', 'commission',
        'price_level', 'terms', 'discount', 'amount', 'tax_rate', 'margin',
    }
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

    return [
        {'key': k, 'label': v['label'], 'fields': v['fields']}
        for k, v in groups.items()
        if v['fields']
    ]


# ─── Columns (from workbench) ────────────────────────────────────────────

def _build_columns(model_key, field_map):
    """Build default layout columns — ida leads, no plumbing (id/uuid)."""
    fields = list(field_map.keys())
    human_fields = [f for f in fields if f not in ('id', 'uuid')]
    char_fields = [
        f.name for f in field_map.values()
        if f.__class__.__name__ == 'CharField' and f.name not in ('id', 'uuid')
    ][:4]
    list_fields = []
    if 'ida' in human_fields:
        list_fields.append({'field': 'ida', 'width': 80, 'visible': True})
    for f in char_fields:
        if f != 'ida':
            list_fields.append({'field': f, 'visible': True})
    return {
        'list': list_fields,
        'detail': human_fields,
    }


def _build_layout(salvaged, model_key, field_map):
    """Build consolidated config.layout in named format.

    Named format:
      layout.active = {list: "default", column: "default", dynamic: "default", display: "default"}
      layout.list.default = {dynamic: "default", display: "default", columns: [...]}
      layout.column.default = {dynamic: "default", display: "default", columns: [...]}
      layout.dynamic.default = {list: "default", display: "default", ...DynamicDetail}
      layout.display.default = {list: "default", dynamic: "default", ...header/tabs}
      layout.panel = [...]
      layout.card = [...]
    """
    # Start with columns (old path) or auto-generate
    cols = salvaged.get('columns') or (
        _build_columns(model_key, field_map) if field_map else {}
    )
    db_cols = cols.get('db', cols) if isinstance(cols, dict) else {}

    list_cols = db_cols.get('list', []) if isinstance(db_cols, dict) else []
    detail_fields = db_cols.get('detail', []) if isinstance(db_cols, dict) else []
    panel = db_cols.get('panel', []) if isinstance(db_cols, dict) else []
    card = db_cols.get('card', []) if isinstance(db_cols, dict) else []

    # Preserve DynamicDetail sections
    dd_sections = salvaged.get('layout', {})

    # Build named format
    layout = {
        'active': {'list': 'default', 'column': 'default', 'dynamic': 'default', 'display': 'default'},
        'list': {
            'default': {
                'dynamic': 'default',
                'display': 'default',
                'columns': list_cols,
            },
        },
        'column': {
            'default': {
                'dynamic': 'default',
                'display': 'default',
                'columns': panel,
            },
        },
        'dynamic': {
            'default': {
                'list': 'default',
                'display': 'default',
            },
        },
        'display': {
            'default': {
                'list': 'default',
                'dynamic': 'default',
            },
        },
        'panel': panel,
        'card': card,
    }

    # Embed DynamicDetail sections into the default dynamic layout
    if dd_sections and isinstance(dd_sections, dict) and ('sections' in dd_sections or 'model' in dd_sections):
        layout['dynamic']['default'].update(dd_sections)

    # Migrate old views[] into additional named list layouts
    old_views = db_cols.get('views', []) if isinstance(db_cols, dict) else []
    for view in old_views:
        if not isinstance(view, dict) or not view.get('name'):
            continue
        name = view['name']
        if name == 'default':
            continue
        layout['list'][name] = {
            'dynamic': 'default',
            'display': 'default',
            'columns': view.get('list', []),
        }

    return layout


# ─── Salvage existing records ────────────────────────────────────────────

SALVAGE_PURPOSES = [
    'wc:schema_map',
    'wc:field_access',
    'wc:enrichment_panels',
    'wc:detail_layout',
    'wc:workbench_fields',
    'wc:db_defaults',
]


def _salvage_existing(model_key):
    """Read existing Setting records for this model and return salvaged config sections."""
    salvaged = {}
    existing = Setting.objects.filter(
        parent_model=model_key,
        purpose__in=SALVAGE_PURPOSES,
        is_active=True,
        is_deleted=False,
    )
    for s in existing:
        cfg = s.config or {}
        if s.purpose == 'wc:schema_map':
            salvaged['schema'] = cfg
        elif s.purpose == 'wc:field_access':
            # Split the combined field_access config into sections
            salvaged['access'] = {
                'roles': cfg.get('roles', {}),
                'query_scope': cfg.get('query_scope', {}),
                'publish': cfg.get('publish', {}),
            }
            salvaged['behaviors'] = cfg.get('field_behaviors', {})
            salvaged['field_groups'] = cfg.get('field_groups', [])
            salvaged['select_lists'] = cfg.get('select_lists', {})
            salvaged['formatting'] = cfg.get('formatting', {})
            salvaged['default_collapsed'] = cfg.get('default_collapsed', [])
        elif s.purpose == 'wc:enrichment_panels':
            salvaged['enrichment'] = cfg
        elif s.purpose == 'wc:detail_layout':
            salvaged['layout'] = cfg
        elif s.purpose == 'wc:workbench_fields':
            salvaged['columns'] = cfg
        elif s.purpose == 'wc:db_defaults':
            salvaged['defaults'] = cfg
    return salvaged


# ─── Build combined config ───────────────────────────────────────────────

def build_model_config(model_key):
    """Build the combined wc:model config for one model."""
    field_map = _get_model_field_map(model_key)
    fields = list(field_map.keys())

    # Try salvage first, fall back to auto-generation
    salvaged = _salvage_existing(model_key)

    config = {
        'schema': salvaged.get('schema') or _build_schema(model_key),
        'access': salvaged.get('access') or (
            _build_access(model_key, fields, field_map) if fields else {}
        ),
        'behaviors': salvaged.get('behaviors') or (
            _build_behaviors(model_key, field_map) if field_map else {}
        ),
        'field_groups': salvaged.get('field_groups') or (
            _build_field_groups(model_key, fields) if fields else []
        ),
        'select_lists': salvaged.get('select_lists', {}),
        'formatting': salvaged.get('formatting') or {
            'currency': 'USD',
            'locale': 'en-US',
            'date_format': 'short',
            'number_precision': 2,
        },
        'default_collapsed': salvaged.get('default_collapsed') or ['system', 'dates'],
        'enrichment': salvaged.get('enrichment', {}),
        'layout': _build_layout(salvaged, model_key, field_map),
        'searches': [],
        'defaults': salvaged.get('defaults', {}),
    }
    return config


# ─── Command ─────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed wc:model Setting records — one per model with combined definition'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing')
        parser.add_argument('--dry-run', action='store_true', help='Report only')
        parser.add_argument('--model', type=str, default=None, help='Seed one model only')

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        target = options.get('model')
        created = updated = skipped = errors = 0

        models = {target: MODEL_REGISTRY[target]} if target and target in MODEL_REGISTRY else MODEL_REGISTRY

        for model_key in sorted(models.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                errors += 1
                self.stderr.write(f'  {model_key}: not in registry')
                continue

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
                parent_model=model_key,
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
                existing.config = config
                existing.name = f'{meta.singular} Model Definition'
                existing.explanation = expl
                existing.save()
                updated += 1
            else:
                Setting.objects.create(
                    name=f'{meta.singular} Model Definition',
                    ida=f'wc-model-{model_key}',
                    parent_model=model_key,
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
