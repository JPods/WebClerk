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
from apps.core.services.field_behaviors import (
    get_field_behaviors, get_field_groups, get_model_field_map, get_model_fields,
    SYSTEM_VIEW_ONLY, NEVER_EDIT,
)


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
    if model_key in ('order', 'invoice', 'proposal', 'purchase', 'workorder', 'requisition'):
        return {
            'customer': {'customer_id__in': '$user.org_ids.customer'},
            'vendor': {'vendor_id__in': '$user.org_ids.vendor'},
            'rep': {},
        }
    elif model_key in ('order_line', 'invoice_line', 'proposal_line', 'purchase_line',
                        'workorder_line', 'requisition_line'):
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


# ─── Behaviors and field groups now live in apps.core.services.field_behaviors



# ─── List column defaults per model family ──────────────────────────────
# Labels match field names; dot-path fields use ".leaf" convention.

def _lc(field, width=None, **kwargs):
    """Build a list column spec with auto-label."""
    label = '.' + field.rsplit('.', 1)[1] if '.' in field else field
    col = {'field': field, 'label': label, 'visible': True}
    if width:
        col['width'] = width
    col.update(kwargs)
    return col


# Transactions: order, proposal, invoice, purchase, workorder
TX_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('dt_needed', width=90),
    _lc('purpose', width=140),
    _lc('status', width=90),
    _lc('priority', width=70),
    _lc('attention', width=120),
    _lc('company', width=160),
    _lc('email', width=160),
    _lc('phone', width=110),
    _lc('balance', width=90, align='right', format='currency'),
    _lc('total', width=90, align='right', format='currency'),
    _lc('address_full', width=180),
    _lc('comments.process', width=200),
    _lc('dt_created', width=90),
]

# Orgs: customer, vendor, manufacturer, employee, rep
ORG_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('display_name', width=180),
    _lc('attention', width=120),
    _lc('type', width=100),
    _lc('status', width=90),
    _lc('purpose', width=140),
    _lc('email', width=160),
    _lc('phone', width=110),
    _lc('address_full', width=180),
    _lc('domain', width=140),
    _lc('price_level', width=90),
    _lc('terms', width=80),
    _lc('comments.process', width=200),
]

# Items
ITEM_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('name', width=180),
    _lc('description', width=200),
    _lc('kind', width=80),
    _lc('uom', width=60),
    _lc('status', width=80),
    _lc('price.retail', width=80, align='right', format='currency'),
    _lc('cost.last', width=80, align='right', format='currency'),
    _lc('quantity.on_hand', width=70, align='right'),
    _lc('quantity.on_order', width=70, align='right'),
    _lc('quantity.on_po', width=70, align='right'),
    _lc('quantity.committed', width=70, align='right'),
    _lc('margin_pct', width=70, align='right'),
    _lc('sku', width=100),
]

# Contacts
CONTACT_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('attention', width=140),
    _lc('company', width=160),
    _lc('title', width=100),
    _lc('email', width=160),
    _lc('phone', width=110),
    _lc('role', width=80),
    _lc('address_full', width=180),
    _lc('source_name', width=100),
    _lc('name_last', width=120),
    _lc('name_first', width=120),
]

# Actions
ACTION_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('action[0]', width=200),
    _lc('assigned_to[0]', width=120),
    _lc('status', width=90),
    _lc('priority', width=70),
    _lc('percent_complete', width=70, align='right'),
    _lc('project_name', width=140),
    _lc('dt_deadline', width=90),
    _lc('kanban_column', width=90),
    _lc('dt_completed', width=90),
]

# Projects
PROJECT_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('name', width=200),
    _lc('status', width=90),
    _lc('category', width=100),
    _lc('priority', width=70),
    _lc('percent_complete', width=70, align='right'),
    _lc('dt_start', width=90),
    _lc('dt_end', width=90),
    _lc('objective', width=180),
    _lc('intent', width=180),
    _lc('logistics', width=180),
]

# Payments
PAYMENT_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('type', width=80),
    _lc('amount', width=90, align='right', format='currency'),
    _lc('available', width=90, align='right', format='currency'),
    _lc('status', width=80),
    _lc('customer', width=140),
    _lc('vendor', width=140),
    _lc('dt_payment', width=90),
    _lc('method', width=100),
    _lc('reference_number', width=120),
    _lc('reconciled', width=70),
    _lc('fee_amount', width=80, align='right', format='currency'),
    _lc('comments.process', width=200),
]

# Documents
DOCUMENT_LIST_COLUMNS = [
    _lc('ida', width=100),
    _lc('name', width=200),
    _lc('purpose', width=140),
    _lc('status', width=80),
    _lc('description', width=200),
    _lc('mime_type', width=100),
    _lc('size_bytes', width=70, align='right'),
    _lc('count_accessed', width=70, align='right'),
    _lc('comments.process', width=200),
]

# ── Communications ──
PHONE_LIST_COLUMNS = [
    _lc('purpose', width=100), _lc('name', width=140), _lc('attention', width=120),
    _lc('number', width=110), _lc('opt_out', width=70), _lc('contact', width=140),
    _lc('country_code', width=70), _lc('format', width=80), _lc('comments.process', width=200),
]
EMAIL_LIST_COLUMNS = [
    _lc('purpose', width=100), _lc('name', width=140), _lc('attention', width=120),
    _lc('address', width=180), _lc('opt_out', width=70), _lc('contact', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
ADDRESS_LIST_COLUMNS = [
    _lc('purpose', width=100), _lc('name', width=140), _lc('attention', width=120),
    _lc('address1', width=180), _lc('city', width=120), _lc('state', width=60),
    _lc('zip', width=80), _lc('country', width=80), _lc('contact', width=140),
    _lc('comments.process', width=200),
]
DOMAIN_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('path', width=200), _lc('type', width=80),
    _lc('status', width=80), _lc('comments.process', width=200),
]
TOUCH_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=140),
    _lc('status', width=80), _lc('contact', width=140), _lc('type', width=80),
    _lc('comments.process', width=200),
]

# ── Accounts ──
GL_ACCOUNT_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('type', width=80),
    _lc('category', width=100), _lc('status', width=80), _lc('balance', width=90, align='right', format='currency'),
    _lc('division', width=70), _lc('comments.process', width=200),
]
GL_JOURNAL_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('debit', width=90, align='right', format='currency'),
    _lc('credit', width=90, align='right', format='currency'),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
JOURNAL_BATCH_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('dt_created', width=90), _lc('comments.process', width=200),
]
LEDGER_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('amount', width=90, align='right', format='currency'),
    _lc('balance', width=90, align='right', format='currency'),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
AUDIT_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
CURRENCY_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=140), _lc('purpose', width=100),
    _lc('status', width=80), _lc('comments.process', width=200),
]
TAX_JURISDICTION_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('status', width=80),
    _lc('comments.process', width=200),
]
TERM_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
STATEMENT_LINE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('amount', width=90, align='right', format='currency'),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]

# ── Transaction lines (sell) ──
SELL_LINE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('item_ida', width=100), _lc('description', width=200),
    _lc('quantity.ordered', width=70, align='right'), _lc('price.unit', width=80, align='right', format='currency'),
    _lc('price.extended', width=90, align='right', format='currency'),
    _lc('cost.unit', width=80, align='right', format='currency'),
    _lc('totals.margin', width=80, align='right', format='currency'),
    _lc('status', width=80), _lc('comments.process', width=200),
]
# ── Transaction lines (exec) ──
EXEC_LINE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('item_ida', width=100), _lc('description', width=200),
    _lc('quantity.ordered', width=70, align='right'), _lc('cost.unit', width=80, align='right', format='currency'),
    _lc('cost.extended', width=90, align='right', format='currency'),
    _lc('status', width=80), _lc('comments.process', width=200),
]

# ── Payment sub-models ──
PAYMENT_APPLICATION_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('amount', width=90, align='right', format='currency'),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
PAYMENT_METHOD_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
PAYMENT_TERM_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]

# ── Products (secondary) ──
BOM_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('comments.process', width=200),
]
CATALOG_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
ITEM_XREF_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('comments.process', width=200),
]
ITEM_USAGE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
ORG_ITEM_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('comments.process', width=200),
]
SERIAL_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('comments.process', width=200),
]
SERIAL_LOG_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
SERVICE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
VARIANT_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('comments.process', width=200),
]
WAREHOUSE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('address_full', width=180), _lc('comments.process', width=200),
]
INVENTORY_CHECK_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]
INVENTORY_RESERVATION_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('item_ida', width=100), _lc('purpose', width=140),
    _lc('status', width=80), _lc('quantity.reserved', width=80, align='right'),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]

# ── Docs ──
QA_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('question', width=300), _lc('answer', width=300),
    _lc('status', width=80), _lc('comments.process', width=200),
]
LINKAGE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('comments.process', width=200),
]
TAG_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]

# ── Sync ──
CONNECTION_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('type', width=80),
    _lc('status', width=80), _lc('purpose', width=140), _lc('comments.process', width=200),
]
BUNDLE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('dt_created', width=90), _lc('comments.process', width=200),
]

# ── Core ──
SETTING_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('parent_model', width=100), _lc('scope', width=80), _lc('status', width=80),
    _lc('comments.process', width=200),
]
REPORT_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('output_type', width=80), _lc('comments.process', width=200),
]
NOTIFICATION_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('dt_created', width=90), _lc('comments.process', width=200),
]
WORKSPACE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
GANTT_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]
DATABROWSER_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('name', width=200), _lc('purpose', width=140),
    _lc('status', width=80), _lc('comments.process', width=200),
]

# ── Alice ──
ALICE_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('name', width=200),
    _lc('status', width=80), _lc('dt_created', width=90), _lc('comments.process', width=200),
]

# ── Other ──
OTHER_ORG_LIST_COLUMNS = ORG_LIST_COLUMNS
DELIVERY_LIST_COLUMNS = [
    _lc('ida', width=100), _lc('purpose', width=140), _lc('status', width=80),
    _lc('dt_created', width=90), _lc('comments.process', width=200),
]

# Map model_key → custom list columns
MODEL_LIST_COLUMNS = {
    # Transactions
    'order': TX_LIST_COLUMNS, 'proposal': TX_LIST_COLUMNS, 'invoice': TX_LIST_COLUMNS,
    'purchase': TX_LIST_COLUMNS, 'workorder': TX_LIST_COLUMNS,
    'requisition': TX_LIST_COLUMNS, 'receipt': TX_LIST_COLUMNS,
    # Transaction lines
    'order_line': SELL_LINE_LIST_COLUMNS, 'invoice_line': SELL_LINE_LIST_COLUMNS,
    'proposal_line': SELL_LINE_LIST_COLUMNS, 'purchase_line': EXEC_LINE_LIST_COLUMNS,
    'receipt_line': EXEC_LINE_LIST_COLUMNS, 'requisition_line': EXEC_LINE_LIST_COLUMNS,
    'workorder_line': EXEC_LINE_LIST_COLUMNS,
    # Orgs
    'customer': ORG_LIST_COLUMNS, 'vendor': ORG_LIST_COLUMNS,
    'manufacturer': ORG_LIST_COLUMNS, 'employee': ORG_LIST_COLUMNS,
    'rep': ORG_LIST_COLUMNS, 'other_org': OTHER_ORG_LIST_COLUMNS,
    # Products
    'item': ITEM_LIST_COLUMNS, 'bill_of_material': BOM_LIST_COLUMNS,
    'catalog': CATALOG_LIST_COLUMNS, 'item_xref': ITEM_XREF_LIST_COLUMNS,
    'item_usage': ITEM_USAGE_LIST_COLUMNS, 'org_item': ORG_ITEM_LIST_COLUMNS,
    'serial': SERIAL_LIST_COLUMNS, 'serial_log': SERIAL_LOG_LIST_COLUMNS,
    'service': SERVICE_LIST_COLUMNS, 'variant': VARIANT_LIST_COLUMNS,
    'warehouse': WAREHOUSE_LIST_COLUMNS,
    'inventory_check': INVENTORY_CHECK_LIST_COLUMNS,
    'inventory_check_line': INVENTORY_CHECK_LIST_COLUMNS,
    'inventory_metrics_snapshot': INVENTORY_CHECK_LIST_COLUMNS,
    'inventory_adjustment_run': INVENTORY_CHECK_LIST_COLUMNS,
    'inventory_reservation': INVENTORY_RESERVATION_LIST_COLUMNS,
    # Core
    'contact': CONTACT_LIST_COLUMNS, 'action': ACTION_LIST_COLUMNS,
    'project': PROJECT_LIST_COLUMNS, 'setting': SETTING_LIST_COLUMNS,
    'report': REPORT_LIST_COLUMNS, 'notification': NOTIFICATION_LIST_COLUMNS,
    'workspace': WORKSPACE_LIST_COLUMNS, 'gantt': GANTT_LIST_COLUMNS,
    'databrowser': DATABROWSER_LIST_COLUMNS,
    # Communications
    'phone': PHONE_LIST_COLUMNS, 'email': EMAIL_LIST_COLUMNS,
    'address': ADDRESS_LIST_COLUMNS, 'domain': DOMAIN_LIST_COLUMNS,
    'touch': TOUCH_LIST_COLUMNS,
    # Accounts
    'gl_account': GL_ACCOUNT_LIST_COLUMNS, 'gl_journal': GL_JOURNAL_LIST_COLUMNS,
    'journal_batch': JOURNAL_BATCH_LIST_COLUMNS, 'ledger': LEDGER_LIST_COLUMNS,
    'audit': AUDIT_LIST_COLUMNS, 'currency': CURRENCY_LIST_COLUMNS,
    'tax_jurisdiction': TAX_JURISDICTION_LIST_COLUMNS, 'term': TERM_LIST_COLUMNS,
    'statement_line': STATEMENT_LINE_LIST_COLUMNS,
    # Payments
    'payment': PAYMENT_LIST_COLUMNS, 'payment_application': PAYMENT_APPLICATION_LIST_COLUMNS,
    'payment_method': PAYMENT_METHOD_LIST_COLUMNS, 'payment_term': PAYMENT_TERM_LIST_COLUMNS,
    'pending_payment_application': PAYMENT_APPLICATION_LIST_COLUMNS,
    # Docs
    'document': DOCUMENT_LIST_COLUMNS, 'question_answer': QA_LIST_COLUMNS,
    'linkage': LINKAGE_LIST_COLUMNS, 'tag': TAG_LIST_COLUMNS,
    # Sync
    'connection': CONNECTION_LIST_COLUMNS, 'bundle': BUNDLE_LIST_COLUMNS,
    # Alice
    'alice_coaching_log': ALICE_LIST_COLUMNS, 'alice_observation': ALICE_LIST_COLUMNS,
    'alice_preset': ALICE_LIST_COLUMNS,
    # Other
    'delivery_line': DELIVERY_LIST_COLUMNS, 'delivery_visit': DELIVERY_LIST_COLUMNS,
    'project_association': DELIVERY_LIST_COLUMNS,
}


# ─── Columns (from workbench) ────────────────────────────────────────────

def _build_columns(model_key, field_map):
    """Build default layout columns — ida leads, no plumbing (id/uuid).
    Uses MODEL_LIST_COLUMNS if defined for the model, otherwise auto-generates."""
    if model_key in MODEL_LIST_COLUMNS:
        list_fields = MODEL_LIST_COLUMNS[model_key]
    else:
        fields = list(field_map.keys())
        human_fields = [f for f in fields if f not in ('id', 'uuid')]
        char_fields = [
            f.name for f in field_map.values()
            if f.__class__.__name__ == 'CharField' and f.name not in ('id', 'uuid')
        ][:4]
        list_fields = []
        if 'ida' in human_fields:
            list_fields.append(_lc('ida', width=80))
        for f in char_fields:
            if f != 'ida':
                list_fields.append(_lc(f))

    # Detail fields: human-meaningful first, system/JSON last
    SYSTEM = {'id', 'uuid', 'version', 'security_level', 'health_rating',
              'is_deleted', 'is_archived', 'is_locked', 'search_vector',
              'dt_created', 'dt_modified', 'dt_approved', 'times_used', 'dt_last_used',
              'parent_id', 'parent_model', 'line_increment', 'row_version'}
    JSON_ENVELOPES = {
        'metadata', 'refs', 'prefs', 'config', 'comments', 'actions',
        'cost', 'sell', 'totals', 'commission', 'finance', 'flow', 'source',
        'price', 'quantity', 'physical', 'tax', 'item', 'catalog', 'flags',
        'contacts', 'addresses', 'domains', 'phones', 'emails', 'docs',
        'connections', 'relations', 'financial', 'metrics', 'gl_accounts',
        'gls', 'tax_code', 'impact', 'retrospection', 'project_metadata',
        'objective', 'tasks', 'logistics', 'assigned_to', 'created_by',
        'start_by', 'deadline_by', 'expected_by', 'completed_by',
        'updated_by', 'end_by', 'languages', 'copyright', 'path',
        'gateway_response', 'op_data', 'answered_by', 'billing',
        'process', 'travel', 'rates', 'scripts',
        'spec', 'quality', 'bom', 'routing', 'tracking', 'dimensions',
        'hazmat', 'compliance', 'yield_data', 'conditions', 'scoring',
        'benchmark', 'warranty', 'site', 'location', 'count',
        'action', 'description',
    }
    FK_ID_FIELDS = {'email_id', 'phone_id', 'domain_id', 'address_id',
                    'conditions_id', 'terms_fk', 'specification_id'}

    all_fields = list(field_map.keys())
    human = [f for f in all_fields if f not in SYSTEM and f not in JSON_ENVELOPES and f not in FK_ID_FIELDS]
    json_fields = [f for f in all_fields if f in JSON_ENVELOPES]
    system = [f for f in all_fields if f in SYSTEM or f in FK_ID_FIELDS]
    detail_fields = human + json_fields + system

    return {
        'list': list_fields,
        'detail': detail_fields,
    }


def _build_layout(salvaged, model_key, field_map):
    """Build consolidated config.layout in named format.

    Named format (terms established 2026-08-18):
      layout.active = {list: "default", column: "default", detail: "default", form: "default"}
      layout.list.default = {detail: "default", form: "default", columns: [...]}
      layout.column.default = {detail: "default", form: "default", columns: [...]}
      layout.detail.default = {list: "default", form: "default", ...DynamicDetail}
      layout.form.default = {list: "default", detail: "default", ...header/tabs}
      layout.panel = [...]
      layout.card = [...]
    """
    # Start with columns — MODEL_LIST_COLUMNS wins for list, salvage for other parts
    cols = salvaged.get('columns') or (
        _build_columns(model_key, field_map) if field_map else {}
    )
    db_cols = cols.get('db', cols) if isinstance(cols, dict) else {}

    # MODEL_LIST_COLUMNS overrides salvaged list columns when defined
    if model_key in MODEL_LIST_COLUMNS:
        list_cols = MODEL_LIST_COLUMNS[model_key]
    else:
        list_cols = db_cols.get('list', []) if isinstance(db_cols, dict) else []
    detail_fields = db_cols.get('detail', []) if isinstance(db_cols, dict) else []
    panel = db_cols.get('panel', []) if isinstance(db_cols, dict) else []
    card = db_cols.get('card', []) if isinstance(db_cols, dict) else []

    # Preserve DynamicDetail sections
    dd_sections = salvaged.get('layout', {})

    # Build named format
    layout = {
        'active': {'list': 'default', 'column': 'default', 'detail': 'default', 'form': 'default'},
        'list': {
            'default': {
                'detail': 'default',
                'form': 'default',
                'columns': list_cols,
            },
        },
        'column': {
            'default': {
                'detail': 'default',
                'form': 'default',
                'columns': panel,
            },
        },
        'detail': {
            'default': {
                'list': 'default',
                'form': 'default',
                'fields': detail_fields,
            },
        },
        'form': {
            'default': {
                'list': 'default',
                'detail': 'default',
            },
        },
        'panel': panel,
        'card': card,
    }

    # Embed DynamicDetail sections into the default detail layout
    if dd_sections and isinstance(dd_sections, dict) and ('sections' in dd_sections or 'model' in dd_sections):
        layout['detail']['default'].update(dd_sections)

    # Migrate old views[] into additional named list layouts
    old_views = db_cols.get('views', []) if isinstance(db_cols, dict) else []
    for view in old_views:
        if not isinstance(view, dict) or not view.get('name'):
            continue
        name = view['name']
        if name == 'default':
            continue
        layout['list'][name] = {
            'detail': 'default',
            'form': 'default',
            'columns': view.get('list', []),
        }

    return layout


# ─── Salvage existing records ────────────────────────────────────────────

SALVAGE_PURPOSES = [
    'wc:schema_map',
    'wc:enrichment_panels',
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
    field_map = get_model_field_map(model_key)
    fields = list(field_map.keys())

    # Try salvage first, fall back to auto-generation
    salvaged = _salvage_existing(model_key)

    config = {
        'schema': salvaged.get('schema') or _build_schema(model_key),
        'access': salvaged.get('access') or (
            _build_access(model_key, fields, field_map) if fields else {}
        ),
        'behaviors': get_field_behaviors(model_key, field_map),
        'field_groups': get_field_groups(model_key, fields),
        'select_lists': salvaged.get('select_lists', {}),
        'formatting': salvaged.get('formatting') or {
            'currency': 'USD',
            'locale': 'en-US',
            'date_format': 'short',
            'number_precision': 2,
        },
        'default_collapsed': salvaged.get('default_collapsed') or ['system', 'dates', 'json'],
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
                existing.config = config
                existing.name = f'{meta.singular} Model Definition'
                existing.explanation = expl
                existing.save()
                updated += 1
            else:
                Setting.objects.create(
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
