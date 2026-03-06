"""Denormalize org (customer / vendor / manufacturer) data into transaction refs.links.

When a transaction is saved with FK references to OrgBase records, we snapshot
the display-relevant fields into ``refs.links.<role>`` so that the React 2025
frontend can render address blocks, email, phone, and attention without extra
API round-trips.

Rules
-----
* **proposal / order / invoice** — always snapshot ``customer`` if present;
  optionally snapshot ``vendor`` and ``manufacturer`` when referenced.
* **purchase** — always snapshot ``vendor`` if present;
  optionally snapshot ``customer`` and ``manufacturer`` when referenced.

Each snapshot is a **dict** (not a list) stored under the role key::

    refs.links.customer = {
        "id": 42,
        "company": "Acme Corp",
        "address_full": "123 Main St, Springfield, IL 62701",
        "email": "orders@acme.com",
        "phone": "555-1234",
        "attention": "Jane Doe",
    }
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

if TYPE_CHECKING:
    from django.db.models import Model

logger = logging.getLogger(__name__)

# Fields copied from OrgBase into refs.links.<role>  (single source of truth: common.denorm_registry)
from common.denorm_registry import get_org_denorm_fields as _get_org_fields
ORG_LINK_FIELDS = tuple(_get_org_fields())

# Import link templates for keyword extraction
try:
    from apps.core.services.link_defaults import get_keyword_fields, extract_keywords
    _HAS_LINK_DEFAULTS = True
except ImportError:
    _HAS_LINK_DEFAULTS = False

# Which transaction types treat which role as "primary" (always captured)
# and which roles are "optional" (captured only when FK is set).
_SALES_TYPES: Set[str] = {"proposal", "order", "invoice"}
_PURCHASE_TYPES: Set[str] = {"purchase"}

# All org-role FK column names we inspect
_ORG_ROLES = ("customer", "vendor", "manufacturer")


def _snapshot_org(org: "Model") -> Dict[str, Any]:
    """Return the denormalized dict for one OrgBase record."""
    snap: Dict[str, Any] = {}
    for field in ORG_LINK_FIELDS:
        val = getattr(org, field, None)
        if field == "display_name":
            # Keep display_name AND expose as "company" for frontend consistency
            snap["display_name"] = val or ""
            snap["company"] = val or ""
        else:
            snap[field] = val
    return snap


def denormalize_org_links(obj: "Model", model_key: str) -> bool:
    """Populate ``refs.links.customer / vendor / manufacturer`` from FK fields.

    Parameters
    ----------
    obj : Model
        A saved transaction instance (Proposal, Order, Invoice, Purchase, …).
    model_key : str
        Lowercase model key, e.g. ``"invoice"``, ``"purchase"``.

    Returns
    -------
    bool
        ``True`` if ``refs`` was mutated (caller should persist).
    """
    norm_key = model_key.lower().replace("_", "")

    # Determine which roles apply
    if norm_key in _SALES_TYPES:
        roles_to_check = _ORG_ROLES  # customer, vendor, manufacturer
    elif norm_key in _PURCHASE_TYPES:
        roles_to_check = _ORG_ROLES
    else:
        # workorder, receipt, etc. — skip for now
        return False

    # Collect non-null FK IDs and their roles
    fk_map: Dict[str, int] = {}
    for role in roles_to_check:
        fk_attr = f"{role}_id"
        fk_id = getattr(obj, fk_attr, None)
        if fk_id:
            fk_map[role] = int(fk_id)

    if not fk_map:
        return False

    # Batch-fetch all referenced orgs in one query
    from apps.orgs.models.base import OrgBase

    org_ids = list(set(fk_map.values()))
    orgs_by_id: Dict[int, "Model"] = {}
    try:
        qs = OrgBase.objects.filter(pk__in=org_ids)
        orgs_by_id = {o.pk: o for o in qs}
    except Exception as exc:
        logger.warning("denormalize_org_links: failed to fetch orgs %s — %s", org_ids, exc)
        return False

    # Build link snapshots
    refs: Dict[str, Any] = obj.refs if isinstance(obj.refs, dict) else {}
    links: Dict[str, Any] = refs.get("links", {})
    if not isinstance(links, dict):
        links = {}

    mutated = False
    for role, org_id in fk_map.items():
        org = orgs_by_id.get(org_id)
        if org is None:
            logger.debug("denormalize_org_links: org #%s not found (role=%s)", org_id, role)
            continue
        new_snap = _snapshot_org(org)
        if links.get(role) != new_snap:
            links[role] = new_snap
            mutated = True

    # Clear roles whose FK was removed (set to None/0)
    for role in _ORG_ROLES:
        if role not in fk_map and role in links:
            del links[role]
            mutated = True

    # Extract keywords from linked orgs for search
    if _HAS_LINK_DEFAULTS and fk_map:
        all_keywords: set = set()
        existing_keywords = refs.get("keywords", [])
        if isinstance(existing_keywords, list):
            all_keywords.update(existing_keywords)
        
        for role, org_id in fk_map.items():
            org = orgs_by_id.get(org_id)
            if org:
                keywords = extract_keywords(org, role)
                all_keywords.update(keywords)
        
        new_keywords = sorted(all_keywords)
        if refs.get("keywords") != new_keywords:
            refs["keywords"] = new_keywords
            mutated = True

    if mutated:
        refs["links"] = links
        obj.refs = refs

    return mutated
