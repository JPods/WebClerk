"""
field_behaviors — compute UI behaviors and field groups from Django model metadata.

This is the single source of truth for how fields render in the frontend.
Auto-detection from field types covers ~95% of cases. The remaining 5%
(model-specific select lists, special status fields) are overrides stored
in Setting.config.behaviors on the wc:model record.

Usage:
    from apps.core.services.field_behaviors import (
        get_field_behaviors, get_field_groups, get_model_field_map,
    )

    # Compute behaviors for a model — no database hit
    field_map = get_model_field_map('order')
    behaviors = get_field_behaviors('order', field_map)
    groups = get_field_groups('order', list(field_map.keys()))

    # With Setting overrides merged
    behaviors = get_field_behaviors('order', field_map, overrides=setting.config.get('behaviors'))
"""
from apps.core.constants.model_registry import get_model_meta


# ── System constants ────────────────────────────────────────────────────

SYSTEM_VIEW_ONLY = [
    'id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'is_locked', 'security_level',
    'times_used', 'health_rating',
]

NEVER_EDIT = [
    'id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'is_locked', 'security_level', 'search_vector',
    'health_rating',
    'groups', 'user_permissions',
]


# ── Select list options ─────────────────────────────────────────────────

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
SHIPPING_STATUS_OPTIONS = [
    {'value': 'pending', 'label': 'Pending'},
    {'value': 'partial', 'label': 'Partial'},
    {'value': 'shipped', 'label': 'Shipped'},
    {'value': 'in_transit', 'label': 'In Transit'},
    {'value': 'delivered', 'label': 'Delivered'},
    {'value': 'returned', 'label': 'Returned'},
]
SHIPPING_CARRIER_OPTIONS = [
    {'value': 'fedex', 'label': 'FedEx'},
    {'value': 'ups', 'label': 'UPS'},
    {'value': 'usps', 'label': 'USPS'},
    {'value': 'dhl', 'label': 'DHL'},
    {'value': 'freight', 'label': 'Freight'},
    {'value': 'local', 'label': 'Local Delivery'},
    {'value': 'will_call', 'label': 'Will Call'},
]
SHIPPING_SERVICE_OPTIONS = [
    {'value': 'ground', 'label': 'Ground'},
    {'value': '2day', 'label': '2-Day'},
    {'value': 'next_day', 'label': 'Next Day'},
    {'value': 'priority', 'label': 'Priority'},
    {'value': 'economy', 'label': 'Economy'},
    {'value': 'freight', 'label': 'Freight/LTL'},
]
WEIGHT_UNIT_OPTIONS = [
    {'value': 'lbs', 'label': 'lbs'},
    {'value': 'kg', 'label': 'kg'},
    {'value': 'oz', 'label': 'oz'},
    {'value': 'g', 'label': 'g'},
]

# ── Best-guess baselines for common fields ─────────────────────────────
# Users add/delete from these. Better to start with a menu than a blank page.

PRIORITY_OPTIONS = [
    {'value': 'low', 'label': 'Low'},
    {'value': 'normal', 'label': 'Normal'},
    {'value': 'high', 'label': 'High'},
    {'value': 'urgent', 'label': 'Urgent'},
]
TERMS_OPTIONS = [
    {'value': 'due_on_receipt', 'label': 'Due on Receipt'},
    {'value': 'net_10', 'label': 'Net 10'},
    {'value': 'net_15', 'label': 'Net 15'},
    {'value': 'net_30', 'label': 'Net 30'},
    {'value': 'net_45', 'label': 'Net 45'},
    {'value': 'net_60', 'label': 'Net 60'},
    {'value': '2_10_net_30', 'label': '2/10 Net 30'},
    {'value': 'prepaid', 'label': 'Prepaid'},
    {'value': 'cod', 'label': 'COD'},
]
PAYMENT_METHOD_OPTIONS = [
    {'value': 'check', 'label': 'Check'},
    {'value': 'ach', 'label': 'ACH'},
    {'value': 'wire', 'label': 'Wire'},
    {'value': 'credit_card', 'label': 'Credit Card'},
    {'value': 'cash', 'label': 'Cash'},
    {'value': 'other', 'label': 'Other'},
]
PAYMENT_CATEGORY_OPTIONS = [
    {'value': 'standard', 'label': 'Standard'},
    {'value': 'deposit', 'label': 'Deposit'},
    {'value': 'refund', 'label': 'Refund'},
    {'value': 'credit_memo', 'label': 'Credit Memo'},
    {'value': 'write_off', 'label': 'Write-off'},
]
PURPOSE_OPTIONS = [
    {'value': 'standard', 'label': 'Standard'},
    {'value': 'template', 'label': 'Template'},
    {'value': 'test', 'label': 'Test'},
    {'value': 'internal', 'label': 'Internal'},
]
CHANNEL_OPTIONS = [
    {'value': 'call', 'label': 'Phone Call'},
    {'value': 'email', 'label': 'Email'},
    {'value': 'visit', 'label': 'Visit'},
    {'value': 'text', 'label': 'Text/SMS'},
    {'value': 'meeting', 'label': 'Meeting'},
    {'value': 'web', 'label': 'Web'},
    {'value': 'mail', 'label': 'Mail'},
]
DIRECTION_OPTIONS = [
    {'value': 'in', 'label': 'Inbound'},
    {'value': 'out', 'label': 'Outbound'},
]
SUPPORT_STATUS_OPTIONS = [
    {'value': 'active', 'label': 'Active'},
    {'value': 'inactive', 'label': 'Inactive'},
    {'value': 'archived', 'label': 'Archived'},
]
ITEM_STATUS_OPTIONS = [
    {'value': 'active', 'label': 'Active'},
    {'value': 'inactive', 'label': 'Inactive'},
    {'value': 'discontinued', 'label': 'Discontinued'},
    {'value': 'pending', 'label': 'Pending'},
]
ITEM_KIND_OPTIONS = [
    {'value': 'product', 'label': 'Product'},
    {'value': 'service', 'label': 'Service'},
    {'value': 'assembly', 'label': 'Assembly'},
    {'value': 'non_inventory', 'label': 'Non-Inventory'},
    {'value': 'shipping', 'label': 'Shipping'},
    {'value': 'discount', 'label': 'Discount'},
    {'value': 'tax', 'label': 'Tax'},
]
SERIAL_STATUS_OPTIONS = [
    {'value': 'available', 'label': 'Available'},
    {'value': 'sold', 'label': 'Sold'},
    {'value': 'reserved', 'label': 'Reserved'},
    {'value': 'in_repair', 'label': 'In Repair'},
    {'value': 'returned', 'label': 'Returned'},
    {'value': 'scrapped', 'label': 'Scrapped'},
]
CONTACT_ROLE_OPTIONS = [
    {'value': 'user', 'label': 'User'},
    {'value': 'admin', 'label': 'Admin'},
    {'value': 'buyer', 'label': 'Buyer'},
    {'value': 'manager', 'label': 'Manager'},
    {'value': 'viewer', 'label': 'Viewer'},
]
GL_JOURNAL_TYPE_OPTIONS = [
    {'value': 'general', 'label': 'General'},
    {'value': 'sales', 'label': 'Sales'},
    {'value': 'purchase', 'label': 'Purchase'},
    {'value': 'payment', 'label': 'Payment'},
    {'value': 'adjustment', 'label': 'Adjustment'},
    {'value': 'closing', 'label': 'Closing'},
]
PROJECT_CATEGORY_OPTIONS = [
    {'value': 'sprint', 'label': 'Sprint'},
    {'value': 'maintenance', 'label': 'Maintenance'},
    {'value': 'implementation', 'label': 'Implementation'},
    {'value': 'support', 'label': 'Support'},
    {'value': 'internal', 'label': 'Internal'},
]
REPORT_CATEGORY_OPTIONS = [
    {'value': 'transaction', 'label': 'Transaction'},
    {'value': 'financial', 'label': 'Financial'},
    {'value': 'inventory', 'label': 'Inventory'},
    {'value': 'contact', 'label': 'Contact'},
    {'value': 'admin_tool', 'label': 'Admin Tool'},
    {'value': 'dashboard', 'label': 'Dashboard'},
]
EMAIL_TYPE_OPTIONS = [
    {'value': 'work', 'label': 'Work'},
    {'value': 'personal', 'label': 'Personal'},
    {'value': 'billing', 'label': 'Billing'},
    {'value': 'support', 'label': 'Support'},
    {'value': 'other', 'label': 'Other'},
]
DOMAIN_TYPE_OPTIONS = [
    {'value': 'website', 'label': 'Website'},
    {'value': 'social', 'label': 'Social Media'},
    {'value': 'marketplace', 'label': 'Marketplace'},
    {'value': 'other', 'label': 'Other'},
]
ADDRESS_PURPOSE_OPTIONS = [
    {'value': 'billing', 'label': 'Billing'},
    {'value': 'shipping', 'label': 'Shipping'},
    {'value': 'mailing', 'label': 'Mailing'},
    {'value': 'location', 'label': 'Location'},
    {'value': 'other', 'label': 'Other'},
]
RESERVATION_REASON_OPTIONS = [
    {'value': 'sales_order', 'label': 'Sales Order'},
    {'value': 'work_order', 'label': 'Work Order'},
    {'value': 'transfer', 'label': 'Transfer'},
    {'value': 'hold', 'label': 'Hold'},
]
INVENTORY_MOVEMENT_OPTIONS = [
    {'value': 'receipt', 'label': 'Receipt'},
    {'value': 'shipment', 'label': 'Shipment'},
    {'value': 'adjustment', 'label': 'Adjustment'},
    {'value': 'transfer', 'label': 'Transfer'},
    {'value': 'return', 'label': 'Return'},
    {'value': 'scrap', 'label': 'Scrap'},
]
DOCUMENT_PURPOSE_OPTIONS = [
    {'value': 'attachment', 'label': 'Attachment'},
    {'value': 'template', 'label': 'Template'},
    {'value': 'image', 'label': 'Image'},
    {'value': 'reference', 'label': 'Reference'},
    {'value': 'certificate', 'label': 'Certificate'},
]
BUNDLE_DIRECTION_OPTIONS = [
    {'value': 'import', 'label': 'Import'},
    {'value': 'export', 'label': 'Export'},
    {'value': 'sync', 'label': 'Sync'},
]
CONNECTION_TYPE_OPTIONS = [
    {'value': 'api', 'label': 'API'},
    {'value': 'sftp', 'label': 'SFTP'},
    {'value': 'webhook', 'label': 'Webhook'},
    {'value': 'manual', 'label': 'Manual'},
    {'value': 'internal', 'label': 'Internal'},
]


# ── JSON leaf behaviors ─────────────────────────────────────────────────
# PJPV: derived from Pydantic schemas in common/schemas/transaction_envelopes.py.
# The schema is the single source of truth for types, labels, and formatting.
# Comments envelope is not a business envelope — stays hardcoded.

def _build_leaf_behaviors():
    """Build LEAF_BEHAVIORS from Pydantic schemas + comments (non-schema)."""
    try:
        from common.schemas.transaction_envelopes import get_all_leaf_behaviors
        behaviors = get_all_leaf_behaviors()
    except Exception:
        # Fallback if schemas not yet available (e.g., during migrations)
        behaviors = {}

    # Comments envelope is structural, not business — no Pydantic schema needed
    behaviors['comments'] = {
        'public':  {'type': 'json-tree', 'label': 'Public Comments'},
        'process': {'type': 'json-tree', 'label': 'Process Notes'},
        'partner': {'type': 'json-tree', 'label': 'Partner Notes'},
        'notes':   {'type': 'json-tree', 'label': 'Internal Notes'},
    }

    # Header-level cost envelope uses TransactionCost schema but is mapped
    # to the 'cost' key alongside LineCost fields. Merge both.
    if 'cost' in behaviors:
        try:
            from common.schemas.transaction_envelopes import (
                TransactionCost, schema_to_leaf_behaviors,
            )
            header_cost = schema_to_leaf_behaviors(TransactionCost)
            # LineCost fields take precedence; header-only fields get added
            for k, v in header_cost.items():
                if k not in behaviors['cost']:
                    behaviors['cost'][k] = v
        except Exception:
            pass

    return behaviors

LEAF_BEHAVIORS = _build_leaf_behaviors()

# Map selectlist_key → options for JSON leaf select fields
SELECTLIST_KEY_OPTIONS = {
    'shipping_status': SHIPPING_STATUS_OPTIONS,
    'shipping_carrier': SHIPPING_CARRIER_OPTIONS,
    'shipping_service': SHIPPING_SERVICE_OPTIONS,
    'weight_unit': WEIGHT_UNIT_OPTIONS,
}

LEAF_MAP = {
    'order': ['totals', 'shipping'],
    'invoice': ['totals', 'shipping'],
    'proposal': ['totals', 'shipping'],
    'purchase': ['totals', 'shipping'],
    'requisition': ['totals'],
    'workorder': ['totals', 'shipping'],
    'order_line': ['quantity', 'price', 'cost'],
    'invoice_line': ['quantity', 'price', 'cost'],
    'proposal_line': ['quantity', 'price', 'cost'],
    'purchase_line': ['quantity', 'cost'],
    'requisition_line': ['quantity', 'cost'],
    'receipt_line': ['quantity', 'cost'],
    'workorder_line': ['quantity', 'cost'],
    'item': ['quantity', 'price'],
}


# ── Model introspection ─────────────────────────────────────────────────

_DJANGO_AUTH_FIELDS = {'groups', 'user_permissions', 'logentry'}


def get_model_field_map(model_key):
    """Get {field_name: field_object} for a model. No DB hit."""
    meta = get_model_meta(model_key)
    if not meta:
        return {}
    try:
        model_cls = meta.import_model()
        return {
            f.name: f for f in model_cls._meta.get_fields()
            if hasattr(f, 'column') and f.name not in _DJANGO_AUTH_FIELDS
        }
    except Exception:
        return {}


def get_model_fields(model_key):
    """Get field names for a model. No DB hit."""
    return list(get_model_field_map(model_key).keys())


# ── Leaf injection ───────────────────────────────────────────────────────

def _inject_leaf_behaviors(model_key, field_map, behaviors):
    """Add dot-path leaf behaviors for JSON envelope fields."""
    UNIVERSAL_LEAF_FIELDS = ['comments']
    leaf_sets = list(LEAF_MAP.get(model_key, []))
    for uf in UNIVERSAL_LEAF_FIELDS:
        if uf not in leaf_sets and uf in field_map:
            leaf_sets.append(uf)
    for json_field in leaf_sets:
        if json_field not in field_map:
            continue
        leaves = LEAF_BEHAVIORS.get(json_field, {})
        for leaf_key, leaf_spec in leaves.items():
            dot_path = f'{json_field}.{leaf_key}'
            entry = dict(leaf_spec)
            # Resolve selectlist_key → options for select-type leaf fields
            sl_key = entry.get('selectlist_key')
            if sl_key and entry.get('type') == 'select' and 'options' not in entry:
                opts = SELECTLIST_KEY_OPTIONS.get(sl_key)
                if opts:
                    entry['options'] = opts
            behaviors[dot_path] = entry


# ── Core: field behavior detection ───────────────────────────────────────

def get_field_behaviors(model_key, field_map=None, overrides=None):
    """Compute UI behaviors for every field on a model.

    Auto-detects from Django field metadata. If overrides dict is provided
    (from Setting.config.behaviors), those entries win over auto-detection.

    Returns: {field_name: {type, action?, options?, model?, ...}, ...}
    """
    if field_map is None:
        field_map = get_model_field_map(model_key)

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
        if ftype in ('DecimalField', 'FloatField') and name in (
            'scrap_factor', 'yield_pct',
        ):
            behaviors[name] = {'type': 'percentage'}
            continue
        if ftype in ('DecimalField', 'FloatField') and name not in (
            'latitude', 'longitude',
        ):
            behaviors[name] = {'type': 'number'}
            continue
        if ftype == 'JSONField':
            if name in _ENVELOPE_FIELDS:
                behaviors[name] = {'type': 'json-tree'}
            elif name in _I18N_FIELDS:
                behaviors[name] = {'type': 'i18n'}
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
                'catalog': 'catalog', 'taxjurisdiction': 'tax_jurisdiction',
                'workorder': 'workorder', 'workorderline': 'workorder_line',
                'purchaseline': 'purchase_line', 'inventorycheck': 'inventory_check',
                'inventorylayer': 'inventory_layer', 'orgitem': 'org_item',
                'deliveryvisit': 'delivery_visit',
            }
            lookup_model = model_map.get(related_name, related_name)
            display = 'display_name' if related_name in ('orgbase', 'customer') else 'name' if hasattr(related, 'name') else 'ida'
            behaviors[name] = {'type': 'lookup', 'model': lookup_model, 'display': display}
            continue

        # Select lists by name convention
        if name == 'status' and model_key in ('customer', 'vendor', 'manufacturer', 'employee', 'rep'):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': STATUS_OPTIONS}
            continue
        if name == 'status' and model_key in ('invoice', 'order', 'proposal', 'purchase', 'workorder', 'requisition'):
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
        if name == 'category' and model_key == 'gl_account':
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
        # ── Best-guess baselines — users add/delete from these ──
        if name == 'priority':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PRIORITY_OPTIONS}
            continue
        if name == 'terms':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': TERMS_OPTIONS}
            continue
        if name == 'method' and model_key == 'payment':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PAYMENT_METHOD_OPTIONS}
            continue
        if name == 'category' and model_key == 'payment':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PAYMENT_CATEGORY_OPTIONS}
            continue
        if name == 'category' and model_key == 'project':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PROJECT_CATEGORY_OPTIONS}
            continue
        if name == 'category' and model_key == 'report':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': REPORT_CATEGORY_OPTIONS}
            continue
        if name == 'purpose' and model_key == 'address':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': ADDRESS_PURPOSE_OPTIONS}
            continue
        if name == 'purpose' and model_key == 'document':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': DOCUMENT_PURPOSE_OPTIONS}
            continue
        if name == 'purpose':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': PURPOSE_OPTIONS}
            continue
        if name == 'channel':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': CHANNEL_OPTIONS}
            continue
        if name == 'direction' and model_key == 'bundle':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': BUNDLE_DIRECTION_OPTIONS}
            continue
        if name == 'direction':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': DIRECTION_OPTIONS}
            continue
        if name == 'role' and model_key == 'contact':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': CONTACT_ROLE_OPTIONS}
            continue
        if name == 'kind' and model_key == 'item':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': ITEM_KIND_OPTIONS}
            continue
        if name == 'status' and model_key == 'item':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': ITEM_STATUS_OPTIONS}
            continue
        if name == 'status' and model_key in ('serial', 'serial_log'):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': SERIAL_STATUS_OPTIONS}
            continue
        if name == 'type' and model_key == 'gl_journal':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': GL_JOURNAL_TYPE_OPTIONS}
            continue
        if name == 'type' and model_key == 'email':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': EMAIL_TYPE_OPTIONS}
            continue
        if name == 'type' and model_key == 'domain':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': DOMAIN_TYPE_OPTIONS}
            continue
        if name == 'type' and model_key == 'connection':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': CONNECTION_TYPE_OPTIONS}
            continue
        if name == 'reason' and model_key == 'inventory_reservation':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': RESERVATION_REASON_OPTIONS}
            continue
        if name == 'movement_type':
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': INVENTORY_MOVEMENT_OPTIONS}
            continue
        if name == 'status' and model_key not in (
            'customer', 'vendor', 'manufacturer', 'employee', 'rep',
            'invoice', 'order', 'proposal', 'purchase', 'workorder', 'requisition',
            'item', 'serial', 'serial_log',
        ):
            behaviors[name] = {'type': 'select', 'source': 'inline', 'options': SUPPORT_STATUS_OPTIONS}
            continue
        if ftype == 'TextField':
            behaviors[name] = {'type': 'textarea'}
            continue
        if ftype == 'SearchVectorField':
            behaviors[name] = {'type': 'hidden'}
            continue
        if ftype == 'UUIDField':
            behaviors[name] = {'type': 'readonly'}
            continue
        if ftype == 'SlugField':
            behaviors[name] = {'type': 'text'}
            continue
        if ftype in ('IntegerField', 'BigIntegerField', 'SmallIntegerField',
                      'PositiveIntegerField', 'PositiveSmallIntegerField'):
            behaviors[name] = {'type': 'number'}
            continue
        if ftype == 'CharField':
            behaviors[name] = {'type': 'text'}

    # Inject leaf behaviors for JSON envelope fields
    _inject_leaf_behaviors(model_key, field_map, behaviors)

    # Apply overrides from Setting — these win over auto-detection
    if overrides and isinstance(overrides, dict):
        for field_name, override in overrides.items():
            if isinstance(override, dict):
                if field_name in behaviors:
                    behaviors[field_name].update(override)
                else:
                    behaviors[field_name] = override

    return behaviors


# ── Core: field groups ───────────────────────────────────────────────────

# Classification sets for field grouping
_JSON_ENVELOPE_FIELDS = {
    'metadata', 'refs', 'prefs', 'config', 'comments', 'actions',
    'cost', 'sell', 'totals', 'commission', 'finance', 'flow',
    'source', 'price', 'quantity', 'physical', 'tax', 'item',
    'catalog', 'flags', 'spec', 'quality', 'bom', 'routing',
    'tracking', 'dimensions', 'hazmat', 'compliance', 'yield_data',
    'conditions', 'scoring', 'benchmark',
    'contacts', 'addresses', 'domains', 'phones', 'emails',
    'docs', 'connections', 'relations', 'financial', 'metrics',
    'gl_accounts', 'gls', 'tax_code',
    'impact', 'retrospection', 'project_metadata',
    'objective', 'tasks', 'logistics',
    'created_by', 'start_by', 'deadline_by',
    'expected_by', 'completed_by', 'updated_by', 'end_by', 'languages',
    'copyright', 'path', 'gateway_response',
}
_SYSTEM_FIELDS = {
    'id', 'uuid', 'version', 'security_level', 'health_rating',
    'parent_id', 'parent_model', 'line_increment',
}
_FK_ID_FIELDS = {
    'email_id', 'phone_id', 'domain_id', 'address_id',
    'conditions_id', 'terms_fk',
}
_FINANCIAL_FIELDS = {
    'total', 'balance', 'cost', 'sell', 'totals', 'commission',
    'price_level', 'terms', 'discount', 'amount', 'tax_rate', 'margin',
}
_COMM_FIELDS = {'email', 'phone', 'fax', 'mobile', 'website', 'url'}
_STATUS_FIELDS = {'status', 'priority', 'stage', 'state'}


def get_field_groups(model_key, fields=None):
    """Group fields by semantic category for detail view rendering.

    Returns: [{key, label, fields}, ...] — only groups with fields.
    """
    if fields is None:
        fields = get_model_fields(model_key)

    groups = {
        'identity':      {'label': 'Identity', 'fields': []},
        'communication': {'label': 'Communication', 'fields': []},
        'financial':     {'label': 'Financial', 'fields': []},
        'status':        {'label': 'Status', 'fields': []},
        'dates':         {'label': 'Dates', 'fields': []},
        'system':        {'label': 'System', 'fields': []},
        'json':          {'label': 'Data', 'fields': []},
    }

    for name in fields:
        if name in _JSON_ENVELOPE_FIELDS:
            groups['json']['fields'].append(name)
        elif name in _SYSTEM_FIELDS or name in _FK_ID_FIELDS:
            groups['system']['fields'].append(name)
        elif name in _FINANCIAL_FIELDS:
            groups['financial']['fields'].append(name)
        elif name in _COMM_FIELDS or name.startswith('address'):
            groups['communication']['fields'].append(name)
        elif name in _STATUS_FIELDS or name.startswith('is_'):
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


# ── Envelope fields — structural JSON, rendered as json-tree ────────────
_ENVELOPE_FIELDS = {'metadata', 'refs', 'prefs', 'config', 'comments', 'actions'}

# ── i18n display fields — {"en": "text"} objects, rendered as text ──────
# These are JSONFields that store language-keyed display values.
# Declared explicitly — React does not guess.
_I18N_FIELDS = {
    'action', 'description', 'assigned_to', 'languages',
    'created_by', 'start_by', 'deadline_by', 'expected_by',
    'completed_by', 'updated_by', 'end_by',
}


def get_leaf_declarations(model_key, field_map=None):
    """Declare every JSONField's leaf type — no guessing on the frontend.

    Returns: {field_name: {type, extract?, widget?}, ...}
      type='i18n'     → extract [0], render as text/textarea
      type='envelope' → render as json-tree
      type='json'     → generic JSON (fallback)
    """
    if field_map is None:
        field_map = get_model_field_map(model_key)

    leaves = {}
    for name, field in field_map.items():
        ftype = field.get_internal_type() if hasattr(field, 'get_internal_type') else ''
        if ftype != 'JSONField':
            continue

        if name in _ENVELOPE_FIELDS:
            leaves[name] = {'type': 'envelope'}
        elif name in _I18N_FIELDS:
            leaves[name] = {'type': 'i18n', 'extract': '[0]'}
        else:
            # Check Pydantic schema for this model — if it declares leaves, use them
            leaves[name] = {'type': 'json'}

    return leaves
