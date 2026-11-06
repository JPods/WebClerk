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
from apps.core.services.dt_fields import SYSTEM_DT_FIELDS


# ── System constants ────────────────────────────────────────────────────

SYSTEM_VIEW_ONLY = [
    'id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_archived', 'security_level',
    'times_used', 'health_rating',
]

NEVER_EDIT = [
    'id', 'ida', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_archived', 'security_level', 'search_vector',
    'health_rating',
    'groups', 'user_permissions',
]


# ── Select list options ─────────────────────────────────────────────────


# ── Best-guess baselines for common fields ─────────────────────────────
# Users add/delete from these. Better to start with a menu than a blank page.

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


LEAF_MAP = {
    'order': ['totals', 'shipping'],
    'invoice': ['totals', 'shipping'],
    'quote': ['totals', 'shipping'],
    'purchase': ['totals', 'shipping'],
    'requisition': ['totals'],
    'workorder': ['totals', 'shipping'],
    'order_line': ['quantity', 'price', 'cost'],
    'invoice_line': ['quantity', 'price', 'cost'],
    'quote_line': ['quantity', 'price', 'cost'],
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


# ── Core: field behavior detection ───────────────────────────────────────

#: FK names that are an org role; each is its own registry key.
_ORG_ROLE_FIELDS = ('customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org')


def _registry_key_for(model_cls) -> str:
    """The MODEL_REGISTRY key for a Django model class — read from the registry, never a
    hand-kept map (one drifted: ai_message's FKs pointed at 'aimessage'). OrgBase is
    inheritance only, never a model (Bill); its FKs look up customers."""
    from apps.core.constants.model_registry import MODEL_REGISTRY
    name = model_cls.__name__.lower()
    if name == 'orgbase':
        return 'customer'
    path = f'{model_cls.__module__}.{model_cls.__name__}'
    keys = [k for k, meta in MODEL_REGISTRY.items() if meta.model == path]
    for k in keys:
        if k.replace('_', '') == name:
            return k
    return keys[0] if keys else name


_INTEGER_TYPES = ('IntegerField', 'BigIntegerField', 'PositiveIntegerField', 'PositiveBigIntegerField')
#: Pointer stems that are not the model's own name.
_POINTER_STEMS = {'assigned_to': 'contact', 'user': 'contact', 'child': 'item', 'parent_item': 'item'}
#: How a looked-up record is named: a contact by its attention, an org by its company.
_POINTER_DISPLAY = {'contact': 'attention', 'customer': 'company', 'vendor': 'company',
                    'manufacturer': 'company', 'rep': 'company', 'employee': 'company', 'other_org': 'company'}


def _pointed_model(name, ftype):
    """The lookup behavior for an integer ``<model>_id`` or a text ``<model>_ida`` column, or
    None when the stem names no registered model (parent_line_id, batch_id)."""
    if name.endswith('_id') and ftype in _INTEGER_TYPES:
        stem, by_ida = name[:-3], False
    elif name.endswith('_ida') and ftype == 'CharField':
        stem, by_ida = name[:-4], True
    else:
        return None
    model = _POINTER_STEMS.get(stem, stem)
    if model == 'parent_line' or get_model_meta(model) is None:
        return None
    out = {'type': 'lookup', 'model': model}
    if by_ida:
        out['value'] = 'ida'
    if model in _POINTER_DISPLAY:
        out['display'] = _POINTER_DISPLAY[model]
    return out


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
        # A dt_ is a system stamp (shown, never typed) or a plan date a person enters with the
        # one date-and-time tool (Bill, 2026-11-03). dt_fields names each; the column type does
        # not decide: 167 plan dates read 'timestamp' (view only) because they are epoch columns.
        if name.startswith('dt_') or ftype in ('DateTimeField', 'DateField'):
            behaviors[name] = {'type': 'timestamp' if name in SYSTEM_DT_FIELDS else 'date'}
            continue
        if ftype == 'DecimalField' and name in (
            'amount', 'total', 'balance', 'value_original', 'value_available',
            'fee_amount', 'cost_snapshot', 'discount_potential',
            'tendered', 'change', 'available',   # cash: money entered shows .00 (Bill, 2026-11-03)
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
            # An OrgBase pointer looks up the role the field names: item.vendor searches
            # vendors, not customers (found 2026-11-03: 17 lookups on 9 models searched
            # customers for a vendor, manufacturer or rep).
            lookup_model = (name if related_name == 'orgbase' and name in _ORG_ROLE_FIELDS
                            else _registry_key_for(related))
            display = 'display_name' if related_name in ('orgbase', 'customer') else 'name' if hasattr(related, 'name') else 'ida'
            behaviors[name] = {'type': 'lookup', 'model': lookup_model, 'display': display}
            continue

        # A pointer held as a plain integer (Cash.contact_id, OrderLine.rep_id, Serial.item_id)
        # is still a record: found by name, shown as a name — never a bare number (lead's review
        # on contact_id, 2026-11-05; Bill the same day: "the vast majority of user input fields
        # should have a selectlist"). The stem names the model; an ida column the same, by ida.
        pointed = _pointed_model(name, ftype)
        if pointed:
            behaviors[name] = pointed
            continue
        # Select lists by name convention. A status list is the model's own
        # (definition config.selectlists, services/select_lists.py), never code's (readme 105).
        if name == 'status':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'price_level':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'kanban_column':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'type' and model_key == 'cash':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'line_type' and model_key.endswith('_line'):
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'org_type':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'output_type' and model_key == 'report':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'editor_type' and model_key == 'report':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'content' and model_key == 'report':
            behaviors[name] = {'type': 'editor'}
            continue
        if name == 'category' and model_key == 'gl_account':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'type' and model_key == 'gl_account':
            behaviors[name] = {'type': 'select'}
            continue
        # ── Best-guess baselines — users add/delete from these ──
        if name == 'priority':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'terms':
            # Terms point at Term records and store the ida (Bill, 2026-10-22): a lookup on the
            # model, never a copied list that drifts when a Term is added (readme 105 step d).
            # pick: list — a dozen records a person picks from a select, never searches (Bill, 2026-11-05).
            behaviors[name] = {'type': 'lookup', 'model': 'term', 'display': 'ida', 'value': 'ida', 'pick': 'list'}
            continue
        if name == 'method' and model_key == 'cash':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'category' and model_key == 'cash':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'category' and model_key == 'project':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'category' and model_key == 'report':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'ship_via':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'source_name':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'purpose':
            # A model's purposes are its definition's list (config.selectlists.purpose): the
            # browser makes it the dropdown, the door enforces it (Bill, 2026-10-28). With no
            # list the field is free text and unchecked.
            behaviors[name] = {'type': 'text'}
            continue
        if name == 'channel':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'direction' and model_key == 'bundle':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'direction':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'role' and model_key == 'contact':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'kind' and model_key == 'item':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'type' and model_key == 'gl_journal':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'type' and model_key == 'email':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'type' and model_key == 'domain':
            behaviors[name] = {'type': 'select'}
            continue
        if name == 'type' and model_key == 'connection':
            behaviors[name] = {'type': 'select'}
            continue
            continue
        if name == 'movement_type':
            behaviors[name] = {'type': 'select'}
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

    # Add labels from Django verbose_name — users override via Setting
    for name, beh in behaviors.items():
        if 'label' not in beh:
            field = field_map.get(name)
            if field and hasattr(field, 'verbose_name'):
                vn = str(field.verbose_name)
                # Django auto-generates verbose_name from field name — keep it
                # only if it differs meaningfully (not just underscore→space)
                beh['label'] = vn if vn != name else name
            else:
                beh['label'] = name

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
    'cost', 'totals', 'commission', 'finance', 'flow',
    'source', 'price', 'quantity', 'physical', 'tax', 'item',
    'catalog', 'flags', 'spec', 'quality', 'bom', 'routing',
    'tracking', 'dimensions', 'hazmat', 'compliance', 'yield_data',
    'conditions', 'scoring', 'benchmark',
    'contacts', 'addresses', 'domains', 'phones', 'emails',
    'docs', 'connections', 'relations', 'financial', 'metrics',
    'gl_accounts', 'gls', 'tax_code',
    'impact', 'retrospection', 'project_metadata',
    'objective', 'tasks', 'logistics',
    'created_by', 'updated_by', 'languages',
    'path', 'gateway_response',
}
_SYSTEM_FIELDS = {
    'id', 'uuid', 'version', 'security_level', 'health_rating',
    'parent_id', 'parent_model', 'line_increment',
}
_FK_ID_FIELDS = {
    'email_id', 'phone_id', 'domain_id', 'address_id',
    'conditions_id',
}
_FINANCIAL_FIELDS = {
    'total', 'balance', 'cost', 'totals', 'commission',
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
    'created_by', 'updated_by',
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


#: The purpose lists a new model definition starts with (seed_model_definitions). After that
#: the definition's own list (config.selectlists.purpose) is the source, kept by an admin;
#: a model with no list here starts with USER_DEFINED_PURPOSE for an admin to replace.
USER_DEFINED_PURPOSE = {'value': 'user_defined', 'label': 'User defined'}
SEED_PURPOSES = {
    'action': [{'value': 'alice', 'label': 'Alice — her to-do'}],
    'address': [{'value': v, 'label': v.title()} for v in
                ('billing', 'shipping', 'mailing', 'location', 'other')],
    'document': [{'value': v, 'label': v.title()} for v in
                 ('attachment', 'template', 'image', 'reference', 'certificate')],
    'log': [
        {'value': 'audit', 'label': 'Audit — a change to an audited record'},
        {'value': 'alice', 'label': 'Alice — what Alice observed'},
        {'value': 'refs_mismatch', 'label': "Refs mismatch — a record's FK and refs.links disagree"},
        {'value': 'coaching', 'label': 'Coaching — a drill a person ran'},
        {'value': 'inventory', 'label': "Inventory — a document line changed an item's quantity"},
        {'value': 'quiz', 'label': "Quiz — a person's answer to a training question"},
    ],
    'setting': [{'value': v, 'label': v} for v in (
        'wc:model', 'wc:system', 'wc:admin', 'wc:company_profile', 'wc:wchq_connection',
        'wc:cash_gateway', 'wc:shipping_service', 'wc:security', 'wc:dd_card', 'wc:escalation',
        'wc:hook_points', 'wc:ai', 'wc:page_help', 'wc:ui', 'wc:db_defaults', 'wc:keywords',
        'wc:feature', 'wc:schema_map', 'wc:collaborate', 'wc:qa_counters',
        'wc:qa_questions', 'wc:test_parade', 'device_status', 'accounting_interface',
        'user:campaign')],
}
