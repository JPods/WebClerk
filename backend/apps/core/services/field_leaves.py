"""Field leaves — every path a positive view/edit list may name.

A leaf is a value, never a container: a scalar column (``status``), a foreign
key id (``customer_id``), or the end of a path through a JSON envelope
(``totals.total``, ``refs.links.customer.id``). Lists of objects contribute the
leaves of their elements under the list's own path — ``lines.quantity.ordered``
means that value on every line.

The positive list in each wc:model Setting (config.access.roles.<role>.view /
.edit) may name only leaves from this registry. There is no wildcard and no
parent path: to expose something, name it; to name it, describe it in a schema.

Where a JSON field's schema lives:
  1. metadata / refs / prefs / config → common.schemas.defaults.schema_class,
     the one code-side map of envelope schemas.
  2. Any other JSON field → a class named in FIELD_SCHEMAS below.
  3. Otherwise the field has no schema, has no leaves, and cannot be exposed.
     ``missing_schemas`` reports it.

A field mapped to LEAF is itself one leaf: a list of plain values
(action.languages), or an outside system's payload that is shown whole and never
walked (bundle.payload, cash.gateway_response — Bill, 2026-09-18). A field in
NEVER_EXPOSED (secrets) is a leaf of no role, superuser included.

A dict[str, X] with open keys (price levels, user-defined fields) has no
leaves of its own. Its known keys are named in OPEN_MAP_KEYS; an unnamed key
cannot be exposed.
"""
from __future__ import annotations

import importlib
import logging
import types
import typing
from functools import lru_cache

from pydantic import BaseModel as PydanticModel

logger = logging.getLogger(__name__)

ENVELOPES = ('metadata', 'refs', 'prefs', 'config')

_TE = 'common.schemas.transaction_envelopes'

# JSON field → "module:Class". Header fields on transactions, then line fields.
# A model-specific entry ("order.cost") wins over a shared one ("cost").
_AS = 'common.schemas.aspects'
_AC = 'common.schemas.action_aspects'
_RA = 'common.schemas.record_aspects'
LEAF = 'leaf'

# Secrets. Never a leaf, for any role.
NEVER_EXPOSED = frozenset({'connection.encryption', 'sync_bundle.encryption'})

FIELD_SCHEMAS: dict[str, str] = {
    'comments': 'common.schemas.envelopes:CommentsBase',
    'actions': 'common.schemas.envelopes:ActionsBase',
    'item.price': f'{_TE}:ItemPrice',
    'item.cost': f'{_TE}:ItemCost',
    'item.catalog': f'{_TE}:ItemCatalog',
    'item.quantity': 'apps.products.models.item_pydantic:ItemQuantity',
    'purchase.capital_asset': 'apps.transactions.models.purchase_pydantic:CapitalAsset',
    'action.project_metadata': 'apps.transactions.models.project_pydantic:ProjectMetadata',
    'cash.company': f'{_TE}:TransactionCompany',
    'action.action': f'{_AC}:LocalizedText',
    'action.description': f'{_AC}:LocalizedText',
    'action.languages': LEAF,
    'action.impact': f'{_AC}:ActionImpact',
    'action.retrospection': f'{_AC}:ActionRetrospection',
    **{f'action.{s}_by': f'{_AC}:UserStamp' for s in
       ('created', 'updated', 'start', 'deadline', 'expected', 'completed', 'end')},
    'question_answer.answered_by': f'{_AC}:UserStamp',
    'action.assigned_to': f'{_AC}:AssignedPerson',   # list of
    'item.gls': f'{_RA}:ItemGls',
    'item.flags': f'{_RA}:ItemFlags',
    'item.tax_code': f'{_RA}:ItemTaxCode',
    'project.objective': f'{_RA}:ProjectObjective',
    'project.tasks': f'{_RA}:ProjectTasks',
    'project.logistics': f'{_RA}:ProjectLogistics',
    **{f'{m}.paths': f'{_RA}:SettingPaths' for m in ('setting', 'report', 'wc', 'databrowser', 'gantt')},
    'document.path': f'{_RA}:DocumentPath',
    'bill_of_material.op_data': f'{_TE}:BomOperationalData',
    'serial.site': f'{_RA}:SerialSite',
    'serial.warranty': f'{_RA}:SerialWarranty',
    'warehouse.location': f'{_RA}:WarehouseLocation',
    'warehouse.count': f'{_RA}:WarehouseCount',
    # Outside payloads and free-form logs: shown whole (Bill, 2026-09-18).
    **{ref: LEAF for ref in (
        'sync_bundle.payload', 'sync_bundle.response', 'sync_bundle.maps',
        'sync_bundle.rules', 'sync_bundle.conflicts',
        'cash.gateway_response', 'ai_message.context',
        'connection.maps', 'connection.rules', 'connection.scripts',
        'connection.relationships', 'connection.changes', 'connection.conflicts',
        'audit.changes', 'audit.conflicts', 'audit.recommendations',
        'pending.changes', 'tax_jurisdiction.scripts',
    )},
    'inventory_layer.source': f'{_TE}:TransactionSource',
    'inventory_layer.cost': f'{_TE}:TransactionCost',
    'item_xref.cost': f'{_TE}:TransactionCost',
}

# Organisations share one shape for contact channels.
ORG_MODELS = ('customer', 'employee', 'manufacturer', 'other_org', 'rep', 'vendor')
_OA = 'common.schemas.org_aspects'
for _m in ORG_MODELS:
    FIELD_SCHEMAS.update({
        f'{_m}.addresses': f'{_AS}:OrgAddresses',
        f'{_m}.emails': f'{_AS}:OrgEmails',
        f'{_m}.phones': f'{_AS}:OrgPhones',
        f'{_m}.financial': f'{_OA}:OrgFinancial',
        f'{_m}.relations': f'{_OA}:OrgRelations',
        f'{_m}.relationship_stats': f'{_OA}:OrgRelationshipStats',
        f'{_m}.stats': f'{_OA}:RecordStats',
        f'{_m}.contacts': f'{_OA}:OrgContactRef',   # list of
        f'{_m}.domains': f'{_OA}:OrgDomain',        # list of
        f'{_m}.docs': f'{_OA}:OrgDoc',              # list of
        f'{_m}.connections': f'{_OA}:OrgConnections',
        f'{_m}.gl_accounts': f'{_OA}:OrgGlAccounts',
        f'{_m}.metrics': 'common.schemas.record_aspects:PeriodMetrics',
    })
FIELD_SCHEMAS['item.stats'] = f'{_OA}:RecordStats'

TRANSACTION_HEADER_SCHEMAS = {
    'company': f'{_TE}:TransactionCompany',
    'totals': f'{_TE}:TransactionTotals',
    'allocations': f'{_TE}:TransactionAllocations',
    'finance': f'{_TE}:TransactionFinance',
    'cost': f'{_TE}:TransactionCost',
    'tax': f'{_TE}:TransactionTax',
    'commission': f'{_TE}:TransactionCommission',
    'flow': f'{_TE}:TransactionFlow',
    'source': f'{_TE}:TransactionSource',
    'addresses': f'{_AS}:TransactionAddresses',
    'emails': f'{_AS}:TransactionEmails',
    'phones': f'{_AS}:TransactionPhones',
    'shipping': f'{_TE}:TransactionShipping',
}
TRANSACTION_LINE_SCHEMAS = {
    'quantity': f'{_TE}:LineQuantity',
    'price': f'{_TE}:LinePrice',
    'cost': f'{_TE}:LineCost',
    'tax': f'{_TE}:LineTax',
    'totals': f'{_TE}:LineTotals',
    'physical': f'{_TE}:LinePhysical',
    'item': f'{_TE}:LineItem',
    'commission': f'{_TE}:LineCommission',
}
TRANSACTION_HEADERS = ('order', 'invoice', 'quote', 'purchase', 'receipt',
                       'requisition', 'workorder')
TRANSACTION_LINES = tuple(f'{m}_line' for m in TRANSACTION_HEADERS)

#: The most rows one payload may carry in a single collection. A caller with more than
#: this is refused before any of it is walked or saved: a positive list cannot bound a
#: payload's size, only its shape. Matches refs/policy.max_items_per_kind.
#: Depth is bounded separately by schemas.envelopes.JSON_MAX_DEPTH.
COLLECTION_MAX_ROWS = 500

# Known keys of open maps. path → keys. An unnamed key is not a leaf.
OPEN_MAP_KEYS: dict[str, list[str]] = {}


def _unwrap(annotation):
    """Optional[X] / X | None → X. Leaves real unions alone."""
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return _unwrap(args[0]) if len(args) == 1 else annotation
    return annotation


def _is_schema(t) -> bool:
    return isinstance(t, type) and issubclass(t, PydanticModel)


def walk_schema(cls, prefix: str, leaves: set, open_maps: set, _depth: int = 0,
                opaque: set | None = None) -> None:
    """Add every leaf path under ``cls`` to ``leaves``; open dicts to ``open_maps``.

    A leaf whose type is an untyped dict, Any, or a list of those is opaque: it
    carries content no schema describes. Opaque leaves go into ``opaque`` too.
    """
    if _depth > 8:
        raise ValueError(f'schema nesting deeper than 8 at {prefix}')
    for name, field in cls.model_fields.items():
        path = f'{prefix}.{field.alias or name}'
        t = _unwrap(field.annotation)
        origin = typing.get_origin(t)
        if _is_schema(t):
            walk_schema(t, path, leaves, open_maps, _depth + 1, opaque)
        elif origin is list:
            args = typing.get_args(t)
            inner = _unwrap(args[0]) if args else None
            if _is_schema(inner):
                walk_schema(inner, path, leaves, open_maps, _depth + 1, opaque)
            else:
                leaves.add(path)
                if opaque is not None and inner in (None, dict, typing.Any):
                    opaque.add(path)
        elif origin is dict:
            known = OPEN_MAP_KEYS.get(path)
            if known is None:
                open_maps.add(path)
                continue
            args = typing.get_args(t)
            inner = _unwrap(args[1]) if len(args) == 2 else None
            for key in known:
                if _is_schema(inner):
                    walk_schema(inner, f'{path}.{key}', leaves, open_maps, _depth + 1, opaque)
                else:
                    leaves.add(f'{path}.{key}')
        else:
            leaves.add(path)
            if opaque is not None and (t is dict or t is typing.Any or t is list):
                opaque.add(path)


def _import(ref: str):
    module, _, attr = ref.partition(':')
    return getattr(importlib.import_module(module), attr)


def _ref_for(model_key: str, field_name: str):
    ref = FIELD_SCHEMAS.get(f'{model_key}.{field_name}')
    if ref is None and model_key in TRANSACTION_HEADERS:
        ref = TRANSACTION_HEADER_SCHEMAS.get(field_name)
    if ref is None and model_key in TRANSACTION_LINES:
        ref = TRANSACTION_LINE_SCHEMAS.get(field_name)
    if ref is None:
        ref = FIELD_SCHEMAS.get(field_name)
    return ref


def schema_for(model_key: str, field_name: str):
    """The Pydantic class describing one JSON field, or None (also None for LEAF)."""
    if field_name in ENVELOPES:
        from common.schemas.defaults import schema_class
        return schema_class(model_key, field_name)
    ref = _ref_for(model_key, field_name)
    return _import(ref) if ref and ref != LEAF else None


def canonical_key(name: str):
    """The ModelMeta.key for any name the API accepts, or None.

    Registry key, meta key, alias or plural (get_model_meta), or a Django model
    name such as 'workorderline' (registry.resolve) mapped back to its meta.
    """
    from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
    meta = get_model_meta(name)
    if meta is not None:
        return meta.key
    from apps.core.utils import registry
    model = registry.resolve(name)
    if model is None:
        return None
    path = f'{model.__module__}.{model.__name__}'
    for m in MODEL_REGISTRY.values():
        if m.model == path or m.model.rsplit('.', 1)[-1] == model.__name__ and \
                m.import_model() is model:
            return m.key
    return None


def resolve_model(model_key: str):
    """The Django model for any accepted name. Raises when unknown."""
    from apps.core.constants.model_registry import get_model_meta
    key = canonical_key(model_key)
    if key is None:
        raise LookupError(f'not in MODEL_REGISTRY: {model_key}')
    return get_model_meta(key).import_model()


def model_leaves(model_key: str) -> dict:
    """{'leaves', 'opaque', 'missing_schemas', 'open_maps'} for one model.

    Any registry key, meta key or alias; answered for the canonical key (ModelMeta.key).
    """
    key = canonical_key(model_key)
    if key is None:
        raise LookupError(f'not in MODEL_REGISTRY: {model_key}')
    return _model_leaves(key)


@lru_cache(maxsize=None)
def _model_leaves(model_key: str) -> dict:
    from django.db.models import JSONField

    model = resolve_model(model_key)

    leaves: set[str] = set()
    open_maps: set[str] = set()
    opaque: set[str] = set()
    missing: list[str] = []
    for f in model._meta.concrete_fields:
        if not isinstance(f, JSONField):
            # A foreign key is one fact under two names: serializers emit
            # 'invoice', the column is 'invoice_id'. Both are its leaf.
            leaves.add(f.attname)
            if f.is_relation:
                leaves.add(f.name)
            continue
        if f'{model_key}.{f.name}' in NEVER_EXPOSED:
            continue
        if _ref_for(model_key, f.name) == LEAF:
            leaves.add(f.name)
            opaque.add(f.name)
            continue
        cls = schema_for(model_key, f.name)
        if cls is None:
            missing.append(f.name)
            continue
        walk_schema(cls, f.name, leaves, open_maps, opaque=opaque)

    # A collection carries the child model's leaves under its own key: a transaction's
    # lines are rows of the line model, served under "lines". Declared in collections(),
    # which the save walker reads too, so neither can drift from the other.
    for _key, (_child, _max_rows) in collections(model_key).items():
        child = model_leaves(_child)
        leaves.update(f'{_key}.{p}' for p in child['leaves'])
        opaque.update(f'{_key}.{p}' for p in child['opaque'])
        open_maps.update(f'{_key}.{p}' for p in child['open_maps'])
        missing.extend(f'{_key}.{p}' for p in child['missing_schemas'])
    return {
        'leaves': frozenset(leaves),
        'opaque': frozenset(opaque),
        'missing_schemas': tuple(missing),
        'open_maps': tuple(sorted(open_maps)),
    }


def collections(model_key: str) -> dict[str, tuple[str, int]]:
    """The collections this model accepts as objects: payload key → (child model, max rows).

    Bill, 2026-09-20: *"We will constantly use lines as objects in parents. So our solution
    should be generic... We can narrowly define what objects can be accepted as objects. To
    address malicious behavior we can limit their size."*

    One declaration, two readers. ``model_leaves`` builds the child's leaves under the key
    (``lines.quantity.ordered``), and the save walker knows which lists to walk into. They
    cannot drift, because there is nothing to keep in sync.

    **Narrow.** A list under any key not named here is a value, not a collection: it stays a
    leaf, and a leaf no role enumerates is refused. An undeclared collection fails closed.

    **Bounded.** Each entry carries its own row cap. Shape is what an enumeration can
    govern; size is not, so size is declared beside it.

    To accept a new collection, add it here. Nothing else changes.

    **``data`` is reserved and may never be a collection key** (Bill, 2026-09-20). It
    already means four things: DRF's request body, the response envelope, a legacy nested
    payload, and a model column that became ``config``. A collection named ``data`` would
    reach save_view's legacy unwrapping (``save_view.py:335``) and be merged into the
    record as fields — the rows silently flattened. Name the thing, not the container.
    """
    key = canonical_key(model_key)
    if key in TRANSACTION_HEADERS:
        return {'lines': (f'{key}_line', COLLECTION_MAX_ROWS)}
    return {}


#: Payload keys a collection may never be called, because something else already
#: unwraps or claims them before the walker ever sees the payload.
RESERVED_COLLECTION_KEYS = frozenset({'data', 'record', 'options'})


def is_leaf(model_key: str, path: str) -> bool:
    return path in model_leaves(model_key)['leaves']


def clear_cache() -> None:
    _model_leaves.cache_clear()
