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
NEVER_EXPOSED = frozenset({'connection.encryption', 'bundle.encryption'})

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
        'bundle.payload', 'bundle.response', 'bundle.maps', 'bundle.rules', 'bundle.conflicts',
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
    'physical': f'{_TE}:LinePhysical',
    'item': f'{_TE}:LineItem',
    'commission': f'{_TE}:LineCommission',
}
TRANSACTION_HEADERS = ('order', 'invoice', 'proposal', 'purchase', 'receipt',
                       'requisition', 'workorder')
TRANSACTION_LINES = tuple(f'{m}_line' for m in TRANSACTION_HEADERS)

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


def resolve_model(model_key: str):
    """The Django model for a MODEL_REGISTRY key. Raises when unknown."""
    from apps.core.constants.model_registry import MODEL_REGISTRY
    meta = MODEL_REGISTRY.get(model_key)
    if meta is None:
        raise LookupError(f'not in MODEL_REGISTRY: {model_key}')
    return meta.import_model()


@lru_cache(maxsize=None)
def model_leaves(model_key: str) -> dict:
    """{'leaves', 'opaque', 'missing_schemas', 'open_maps'} for one model."""
    from django.db.models import JSONField

    model = resolve_model(model_key)

    leaves: set[str] = set()
    open_maps: set[str] = set()
    opaque: set[str] = set()
    missing: list[str] = []
    for f in model._meta.concrete_fields:
        if not isinstance(f, JSONField):
            leaves.add(f.attname)
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

    # A transaction's lines are rows of the line model, served under "lines".
    if model_key in TRANSACTION_HEADERS:
        line = model_leaves(f'{model_key}_line')
        leaves.update(f'lines.{p}' for p in line['leaves'])
        opaque.update(f'lines.{p}' for p in line['opaque'])
        open_maps.update(f'lines.{p}' for p in line['open_maps'])
        missing.extend(f'lines.{p}' for p in line['missing_schemas'])
    return {
        'leaves': frozenset(leaves),
        'opaque': frozenset(opaque),
        'missing_schemas': tuple(missing),
        'open_maps': tuple(sorted(open_maps)),
    }


def is_leaf(model_key: str, path: str) -> bool:
    return path in model_leaves(model_key)['leaves']


def clear_cache() -> None:
    model_leaves.cache_clear()
