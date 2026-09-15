"""Centralized registry of fields denormalized into ``refs.links``.

Every model that can appear inside a record's ``refs.links.<bucket>`` is
listed here with the exact fields that should be snapshot-copied.  Both the
generic ``RefsMixin.denormalize_links()`` path and the transaction-specific
``denormalize_org_links()`` service read from this single source of truth.

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
    # ── Org roles (source: OrgBase) ─────────────────────────────────────
    # All org-role buckets share the same field list.  When an OrgBase record
    # is snapshot into refs.links.customer (or vendor, manufacturer, etc.)
    # these are the fields that get copied.
    "customer":     ["ida", "display_name", "email", "phone", "address_full", "attention", "status"],
    "vendor":       ["ida", "display_name", "email", "phone", "address_full", "attention", "status"],
    "manufacturer": ["ida", "display_name", "email", "phone", "address_full", "attention", "status"],
    "rep":          ["ida", "display_name", "email", "phone", "address_full", "attention", "status"],
    "employee":     ["id", "display_name", "email", "phone", "address_full", "attention", "status"],

    # ── Contact (source: Contact) ───────────────────────────────────────
    "contact": [
        "id",
        "ida", "display_name",
        "company", "title", "role", "email", "phone", "attention",
    ],

    # ── Communication records ───────────────────────────────────────────
    "email":   ["id", "ida", "email", "name", "type", "is_primary", "is_verified", "opt_out"],
    "phone":   ["id", "ida", "number", "country_code", "format", "name", "opt_out"],
    "address": ["id", "ida", "address1", "city", "state", "zip", "country", "full"],
    "domain":  ["id", "ida", "path", "type", "status"],

    # ── Catalog / Inventory ─────────────────────────────────────────────
    "item":      ["ida", "name", "sku", "description", "kind", "uom"],
    "variant":   ["ida", "name"],
    "warehouse": ["ida", "name", "code"],
    "catalog":   ["ida  ", "name", "code", "currency"],

    # ── Financial / Accounting ──────────────────────────────────────────
    "currency":       ["ida", "code", "name", "symbol"],
    "exchangerate":   ["ida", "from_currency", "to_currency", "rate"],
    "glaccount":      ["ida", "account_credit"],
    "taxjurisdiction":["ida", "name", "code"],
    "paymentmethod":  ["ida", "name", "type"],
    "paymentterm":    ["ida", "name", "terms"],

    # ── Project / Document ──────────────────────────────────────────────
    "project":  ["ida", "name", "status"],
    "document": ["ida", "name", "type"],
    "template": ["ida", "purpose"],
    "report":   ["ida", "name"],
    "bundle":   ["ida", "name"],

    # ── Workflow / Logistics ────────────────────────────────────────────
    "action":       ["ida", "name"],
    "connection":   ["ida", "name", "type"],
    "notification": ["ida", "name"],
    "setting":      ["ida", "name"],
    "tag":          ["ida", "name"],
    "linkage":      ["ida", "name"],

    # ── Child / Detail records ──────────────────────────────────────────
    "questionanswer":              ["ida", "question"],
    "seriallog":                   ["ida", "serial_number"],
    "inventorycheck":              ["ida", "name"],
    "deliveryvisit":               ["ida", "status"],
    "purchasereceipt":             ["ida", "receipt_number"],
    "paymentapplication":          ["ida", "amount_applied"],
    "projectassociation":          ["ida", "project_id"],
    "inventoryreservation":        ["ida", "quantity_reserved"],
    "inventoryadjustmentprocessor":["ida", "status"],
    "inventorymetricssnapshot":    ["ida", "snapshot_date"],
    "pendinginventoryadjustment":  ["ida", "adjustment_type"],
    "auditlog":                    ["ida", "action"],
    "term":                        ["ida", "name"],
    "billofmaterial":              ["ida", "parent_item_id", "child_item_id", "child_ida", "child_description", "quantity", "sequence"],
    "service":                     ["ida", "name"],
    "campaign":                    ["ida", "name"],
    "support":                     ["id", "name"],
}

# The generic "orgbase" key used by RefsMixin.denormalize_links()
# shares the same denorm fields as the role-specific keys.
DENORM_REGISTRY["orgbase"] = DENORM_REGISTRY["customer"]

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

    return list(DENORM_REGISTRY.get(key, ["id"]))


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
    if not model_label:
        # Try direct lookup by model_key
        try:
            model_cls = apps.get_model(model_key)
        except (LookupError, ValueError):
            return None
    else:
        try:
            model_cls = apps.get_model(model_label)
        except (LookupError, ValueError):
            return None

    fields = getattr(model_cls, 'DENORM_FIELDS', None)
    if fields is not None:
        return list(fields)
    return None


def get_org_denorm_fields() -> List[str]:
    """Return fields denormalized for any org-role bucket (customer, vendor, …)."""
    return list(DENORM_REGISTRY["customer"])


def describe_registry() -> Dict[str, List[str]]:
    """Return a copy of the full registry for introspection / documentation."""
    return {k: list(v) for k, v in sorted(DENORM_REGISTRY.items())}


def print_registry() -> None:
    """Pretty-print the registry to stdout (useful in ``manage.py shell``)."""
    for key, fields in sorted(DENORM_REGISTRY.items()):
        print(f"  {key:30s} → {fields}")
