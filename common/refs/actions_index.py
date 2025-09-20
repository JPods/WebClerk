from __future__ import annotations
from typing import Iterator, Set, List
from django.apps import apps
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from common.refs.links import ensure_bidirectional

# Fields on Action that should not be considered "targets"
EXCLUDE_FIELDS: Set[str] = {"assignee", "assigned_to", "owner", "user", "created_by", "updated_by"}

# Fields on Action that represent assignees/responsibles (FK or M2M) for separate linking
ASSIGNEE_FIELDS: Set[str] = EXCLUDE_FIELDS | {"assignees", "owners", "participants", "followers", "watchers", "members", "responsible", "responsibles", "team", "teams"}

# Prefixes for GenericFKs considered as potential targets
GENERIC_PREFIXES = ("target", "subject", "object", "content")

def _yield_if_instance(value) -> Iterator[object]:
    try:
        v = value() if callable(value) else value
    except Exception:
        return
    if getattr(v, "_meta", None) and getattr(v, "pk", None):
        yield v

def _iter_generic_fk(action) -> Iterator[object]:
    if hasattr(action, "content_object"):
        yield from _yield_if_instance(getattr(action, "content_object"))
    for prefix in GENERIC_PREFIXES:
        ct_field = f"{prefix}_content_type"
        id_field = f"{prefix}_object_id"
        if hasattr(action, ct_field) and hasattr(action, id_field):
            try:
                ct = getattr(action, ct_field)
                oid = getattr(action, id_field)
                if ct and oid:
                    Model = ct.model_class()
                    if Model:
                        inst = Model.objects.filter(pk=oid).first()
                        if inst:
                            yield inst
            except Exception:
                continue

def _iter_relational_fields(action) -> Iterator[object]:
    for f in action._meta.get_fields():
        if f.auto_created:
            continue
        name = getattr(f, "name", "")
        if name in EXCLUDE_FIELDS:
            continue
        if getattr(f, "many_to_one", False) or getattr(f, "one_to_one", False):
            yield from _yield_if_instance(getattr(action, name, None))
        if getattr(f, "many_to_many", False):
            try:
                mgr = getattr(action, name, None)
                if mgr is not None:
                    for obj in mgr.all().iterator():
                        yield obj
            except Exception:
                continue

def iter_action_targets(action) -> Iterator[object]:
    seen = set()
    for obj in _iter_generic_fk(action):
        pk = getattr(obj, "pk", None)
        if pk is None:
            continue
        key = (obj.__class__, pk)
        if key not in seen:
            seen.add(key)
            yield obj
    for obj in _iter_relational_fields(action):
        pk = getattr(obj, "pk", None)
        if pk is None:
            continue
        key = (obj.__class__, pk)
        if key not in seen:
            seen.add(key)
            yield obj

@transaction.atomic
def ensure_action_target_links(action, *, kind: str = "acts_on") -> int:
    created = 0
    for target in iter_action_targets(action):
        if ensure_bidirectional(action, target, kind=kind):
            created += 1
    return created

# ---- New: infer kinds for targets (transactions/products) with zero heavy lifting ----

# Optional override map in settings:
# REFS_ACTION_KIND_OVERRIDES = {"transactions.invoice": "transaction", "products.product": "product"}
_ACTION_KIND_OVERRIDES = getattr(settings, "REFS_ACTION_KIND_OVERRIDES", {}) or {}

TXN_APPS = {"transactions", "orders", "billing", "purchasing", "shipping", "invoicing"}
PRODUCT_APPS = {"products", "catalog"}

def _infer_kind_for_obj(obj, default: str = "acts_on") -> str:
    try:
        label = obj._meta.label_lower  # e.g. "products.product"
        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
    except Exception:
        return default

    # Explicit overrides first
    if label in _ACTION_KIND_OVERRIDES:
        return _ACTION_KIND_OVERRIDES[label]

    # App-based heuristics
    if app_label in PRODUCT_APPS:
        return "product"
    if app_label in TXN_APPS:
        return "transaction"

    # Name-based hints (no DB lookups)
    name = model_name or ""
    if any(tok in name for tok in ("product", "sku", "variant", "item")):
        return "product"
    if any(tok in name for tok in ("invoice", "order", "quote", "shipment", "payment", "line")):
        return "transaction"
    return default
@transaction.atomic
def ensure_action_targets_with_kinds(action, default_kind: str = "acts_on") -> int:
    """
    Ensure Action -> target links using inferred kind per target:
    'product' for product-like targets, 'transaction' for transaction-like targets, else default_kind.
    """
    created = 0
    for target in iter_action_targets(action):
        kind = _infer_kind_for_obj(target, default=default_kind)
        if ensure_bidirectional(action, target, kind=kind):
            created += 1
    return created

def _iter_action_assignees(action) -> Iterator[object]:
    """
    Yield assignee/responsible related objects from common fields (FK or M2M).
    """
    seen = set()
    for f in action._meta.get_fields():
        if getattr(f, "auto_created", False):
            continue
        name = getattr(f, "name", "")
        if name not in ASSIGNEE_FIELDS:
            continue
        try:
            value = getattr(action, name, None)
            if value is None:
                continue
            if getattr(f, "many_to_many", False):
                for obj in value.all().iterator():
                    pk = getattr(obj, "pk", None)
                    if pk is None:
                        continue
                    key = (obj.__class__, pk)
                    if key not in seen:
                        seen.add(key)
                        yield obj
            else:
                for obj in _yield_if_instance(value):
                    pk = getattr(obj, "pk", None)
                    if pk is None:
                        continue
                    key = (obj.__class__, pk)
                    if key not in seen:
                        seen.add(key)
                        yield obj
        except Exception:
            continue

# Named field hints for related linking
DOC_M2M_FIELDS = {"documents", "files", "attachments", "docs"}
COMM_M2M_FIELDS = {"messages", "emails", "communications", "notes", "comments"}
SYNC_M2M_FIELDS = {"sync_artifacts", "integrations", "webhooks", "syncs"}
ORG_FIELDS = {"organization", "org", "account", "customer", "vendor", "company"}

def _iter_named_m2m(action, field_names: Set[str]) -> Iterator[object]:
    for name in field_names:
        try:
            mgr = getattr(action, name, None)
            if mgr is None:
                continue
            for obj in mgr.all().iterator():
                yield obj
        except Exception:
            continue

def _iter_named_fk(action, field_names: Set[str]) -> Iterator[object]:
    for name in field_names:
        try:
            value = getattr(action, name, None)
            if value is None:
                continue
            yield from _yield_if_instance(value)
        except Exception:
            continue

@transaction.atomic
def ensure_action_all_links(action) -> int:
    """
    Ensure Action.refs includes:
    - inferred targets (kind='product' | 'transaction' | 'acts_on')
    - documents (kind='doc')
    - communications (kind='comm')
    - sync artifacts (kind='sync')
    - org/account entities (kind='org')
    - assignee/responsible (kind='assignee')
    """
    created = 0

    # Use lightweight kind inference for targets (replaces fixed 'acts_on')
    created += ensure_action_targets_with_kinds(action, default_kind="acts_on")

    for obj in _iter_named_m2m(action, DOC_M2M_FIELDS):
        if ensure_bidirectional(action, obj, kind="doc"):
            created += 1

    for obj in _iter_named_m2m(action, COMM_M2M_FIELDS):
        if ensure_bidirectional(action, obj, kind="comm"):
            created += 1

    for obj in _iter_named_m2m(action, SYNC_M2M_FIELDS):
        if ensure_bidirectional(action, obj, kind="sync"):
            created += 1

    for obj in _iter_named_fk(action, ORG_FIELDS):
        if ensure_bidirectional(action, obj, kind="org"):
            created += 1
    for obj in _iter_action_assignees(action):
        if ensure_bidirectional(action, obj, kind="assignee"):
            created += 1

    return created
    return created