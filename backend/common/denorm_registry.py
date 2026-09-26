"""Centralized registry of fields denormalized into ``refs.links``.

Every model that can appear inside a record's ``refs.links.<bucket>`` is
listed here with the exact fields that should be snapshot-copied. Every link element is
built by ``link_entry()`` from ``get_denorm_fields()`` (Bill, 2026-09-26: a rich {} that
shows the key facts without a query); ``normalize_links`` rewrites stored lists to it.

Migration toward schema-driven denormalization (started 2026-08-24)
-------------------------------------------------------------------
The authoritative declaration for models that have it is ``DENORM_FIELDS``
on the Django model class itself.  ``get_denorm_fields()`` checks the model
class first and falls back to this registry for models without that
attribute.  Over time all models declare DENORM_FIELDS and this registry
shrinks to zero.

Usage
-----
>>> from common.denorm_registry import DENORM_REGISTRY, get_denorm_fields
>>> get_denorm_fields("customer")   # → ["id", "display_name", ...]
>>> get_denorm_fields("contact")    # → ["id", "name_first", ...]

Maintenance
-----------
For models WITH ``DENORM_FIELDS``: update the model class attribute.
For models WITHOUT it (legacy): update this registry **and** run the
corresponding backfill command (see ``readmes/denorm-fields.md``).
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Registry: model_key → list of fields to copy into the snapshot dict
# ---------------------------------------------------------------------------
# Keys use the **canonical singular** form (e.g. "customer" not "customers").
# For org-type buckets (customer, vendor, manufacturer, rep, employee) the
# source model is always OrgBase; the key distinguishes the *role*.
# ---------------------------------------------------------------------------

DENORM_REGISTRY: Dict[str, List[str]] = {
    # Org roles (OrgBase) and Contact declare DENORM_FIELDS on the model — the one definition;
    # they are not repeated here (a second copy here kept the renamed display_name alive).
    # ── Communication records ───────────────────────────────────────────
    "email":   ["id", "ida", "email", "name", "type", "is_primary", "is_verified", "opt_out"],
    "phone":   ["id", "ida", "number", "country_code", "format", "name", "opt_out"],
    "address": ["id", "ida", "address1", "city", "state", "zip", "country", "full"],
    "domain":  ["id", "ida", "path", "type", "status"],
    # ── Catalog / Inventory ─────────────────────────────────────────────
    "item":      ["ida", "name", "sku", "description", "kind", "uom"],
    "variant":   ["item_ida", "description"],
    "warehouse": ["ida", "name", "code"],
    "catalog":   ["name", "code", "currency"],
    # ── Financial / Accounting ──────────────────────────────────────────
    "currency":       ["ida", "code", "name", "symbol"],
    "glaccount":      ["ida", "account_credit"],
    "taxjurisdiction":["ida", "tax_jurisdiction", "tax_name"],
    # ── Project / Document ──────────────────────────────────────────────
    "project":  ["ida", "name", "status"],
    "document": ["ida", "name", "mime_type", "size_bytes"],
    "report":   ["ida", "name"],
    "bundle":   ["ida", "purpose", "status", "direction"],
    # ── Workflow / Logistics ────────────────────────────────────────────
    "action":       ["ida", "action", "status"],
    "connection":   ["ida", "name", "type"],
    "notification": ["ida", "name"],
    "setting":      ["ida", "name"],
    "tag":          ["ida", "name"],
    # ── Child / Detail records ──────────────────────────────────────────
    "questionanswer": ["ida", "question"],
    "seriallog":      ["serial", "action"],
    "auditlog":       ["ida", "action"],
    "term":           ["ida", "name"],
    "billofmaterial": ["ida", "parent_item_id", "child_item_id", "child_ida", "child_description", "quantity", "sequence"],
}

# ── Org-role keys (all share the same source model) ────────────────────
ORG_ROLE_KEYS = frozenset({"customer", "vendor", "manufacturer", "rep", "employee"})


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_denorm_fields(model_key: str) -> List[str]:
    """Return the list of fields for a given model/role key.

    Resolution order:
      1. Django model class ``DENORM_FIELDS`` attribute (authoritative)
      2. This registry (fallback for models without DENORM_FIELDS)
      3. ``["id"]`` if model is completely unknown

    Org-role keys (customer, vendor, etc.) resolve to OrgBase's DENORM_FIELDS
    when available.
    """
    key = model_key.lower()

    # Try model-class declaration first (schema-driven)
    model_fields = _get_model_denorm_fields(key)
    if model_fields is not None:
        return list(model_fields)

    if key in ORG_ROLE_KEYS or key == 'orgbase' or key == 'contact':
        raise LookupError(f'{key} links are defined by DENORM_FIELDS on the model, which was not found.')
    return list(DENORM_REGISTRY.get(key, ["id"]))


def _json_value(value):
    """A snapshot value as JSON holds it: Decimal → float, dates → ISO text, a model → its id."""
    from datetime import date, datetime
    from decimal import Decimal
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, '_meta') and hasattr(value, 'pk'):
        return value.pk
    if hasattr(value, 'hex') and type(value).__name__ == 'UUID':
        return str(value)
    return value


def link_entry(obj, bucket: str) -> Dict[str, object]:
    """The one writer of a refs.links element: {"id": pk, <the bucket's fields>}.

    Bill, 2026-09-26: a link is a rich {} that shows the key facts without a query (a
    contact's refs.links.phone shows the numbers). Which facts: get_denorm_fields(bucket) —
    DENORM_FIELDS on the model, else this registry. Every writer calls this; nothing else
    builds a link element.
    """
    entry: Dict[str, object] = {"id": obj.pk}
    for field in get_denorm_fields(bucket):
        field = field.strip()
        if field != "id":
            entry[field] = _json_value(getattr(obj, field, None))
    return entry


def _get_model_denorm_fields(model_key: str) -> Optional[List[str]]:
    """Look up DENORM_FIELDS on the Django model class, if available.

    Returns None if the model class can't be found or doesn't declare
    DENORM_FIELDS, so callers fall back to the registry.
    """
    try:
        from django.apps import apps
    except ImportError:
        return None

    # Map org-role keys to the actual model
    _ROLE_TO_MODEL = {
        'customer': 'orgs.OrgBase',
        'vendor': 'orgs.OrgBase',
        'manufacturer': 'orgs.OrgBase',
        'rep': 'orgs.OrgBase',
        'employee': 'orgs.OrgBase',
        'orgbase': 'orgs.OrgBase',
    }

    model_label = _ROLE_TO_MODEL.get(model_key)
    if model_label:
        model_cls = apps.get_model(model_label)
    else:
        # The model registry resolves a bare key (contact, phone…). apps.get_model(key)
        # without an app label always raised, so DENORM_FIELDS was never read (Fable #4).
        from apps.core.utils import registry
        resolved = registry.resolve(model_key)
        if resolved is None:
            return None
        model_cls = resolved if hasattr(resolved, '_meta') else resolved.import_model()

    fields = getattr(model_cls, 'DENORM_FIELDS', None)
    if fields is not None:
        return list(fields)
    return None


def get_org_denorm_fields() -> List[str]:
    """Return fields denormalized for any org-role bucket (customer, vendor, …)."""
    return get_denorm_fields("orgbase")


def describe_registry() -> Dict[str, List[str]]:
    """Return a copy of the full registry for introspection / documentation."""
    return {k: list(v) for k, v in sorted(DENORM_REGISTRY.items())}


def print_registry() -> None:
    """Pretty-print the registry to stdout (useful in ``manage.py shell``)."""
    for key, fields in sorted(DENORM_REGISTRY.items()):
        print(f"  {key:30s} → {fields}")
