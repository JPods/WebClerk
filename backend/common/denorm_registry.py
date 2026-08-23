"""Centralized registry of fields denormalized into ``refs.links``.

Every model that can appear inside a record's ``refs.links.<bucket>`` is
listed here with the exact fields that should be snapshot-copied.  Both the
generic ``RefsMixin.denormalize_links()`` path and the transaction-specific
``denormalize_org_links()`` service read from this single source of truth.

Usage
-----
>>> from common.denorm_registry import DENORM_REGISTRY, get_denorm_fields
>>> get_denorm_fields("customer")   # → ["id", "display_name", ...]
>>> get_denorm_fields("contact")    # → ["id", "name_first", ...]

Maintenance
-----------
When adding a new column to a model that should be visible in denormalized
snapshots, add it here **and** run the corresponding backfill command to
propagate the change to existing records (see ``readmes/denorm-fields.md``).
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

# Convenience alias: the generic "orgbase" key used by RefsMixin.denormalize_links()
# maps to the same fields as the role-specific keys.
DENORM_REGISTRY["orgbase"] = DENORM_REGISTRY["customer"]

# ── Org-role keys (all share the same source model) ────────────────────
ORG_ROLE_KEYS = frozenset({"customer", "vendor", "manufacturer", "rep", "employee"})


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_denorm_fields(model_key: str) -> List[str]:
    """Return the list of fields for a given model/role key.

    Falls back to ``["id"]`` for unknown keys so callers always get a usable list.
    """
    return list(DENORM_REGISTRY.get(model_key.lower(), ["id"]))


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
