"""
Role-Based Query Filter Service.

Applies role-based access restrictions to database queries.
The rules live in each model's wc:model Setting (config.access.roles) — see
apps/core/services/access.py. This module turns a role's block into Q objects
and field lists. No superuser bypass: superuser has its own full lists.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.services import access

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


# =============================================================================
# Variable Resolution
# =============================================================================

VARIABLE_PATTERN = re.compile(r"\$user\.(\w+)(?:\.(\w+))?")


def resolve_filter_variables(filter_dict: dict, user_context: dict) -> dict:
    """
    Resolve $user.* variables in a filter dictionary.
    
    Variables:
    - $user.id → user_context["user_id"]
    - $user.org_ids.customer → user_context["org_ids"]["customer"]
    - $user.org_ids.vendor → user_context["org_ids"]["vendor"]
    
    Args:
        filter_dict: Dict with potential variable placeholders
        user_context: Dict with user_id, org_ids, contact_id, etc.
    
    Returns:
        New dict with variables resolved
    
    Example:
        resolve_filter_variables(
            {"customer_id__in": "$user.org_ids.customer"},
            {"org_ids": {"customer": [1, 2, 3]}}
        )
        → {"customer_id__in": [1, 2, 3]}
    """
    resolved = {}
    
    for key, value in filter_dict.items():
        if isinstance(value, str) and value.startswith("$user."):
            match = VARIABLE_PATTERN.match(value)
            if match:
                var_name = match.group(1)
                sub_key = match.group(2)
                
                if sub_key:
                    # Nested lookup: $user.org_ids.customer
                    resolved[key] = user_context.get(var_name, {}).get(sub_key, [])
                else:
                    # Direct lookup: $user.id
                    resolved[key] = user_context.get(var_name)
            else:
                resolved[key] = value
        elif isinstance(value, dict):
            # Recurse for nested dicts
            resolved[key] = resolve_filter_variables(value, user_context)
        elif isinstance(value, list):
            # Handle lists (could contain dicts or variables)
            resolved[key] = [
                resolve_filter_variables(v, user_context) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            resolved[key] = value
    
    return resolved


# =============================================================================
# User Context Builder
# =============================================================================

def build_user_context(user: AbstractUser) -> dict:
    """
    Build the user context dict for variable resolution.
    
    Args:
        user: Django User instance
    
    Returns:
        Dict with:
        - user_id: int
        - contact_id: int or None
        - org_ids: {customer: [ids], vendor: [ids], ...}
        - roles: [role strings]
        - is_superuser: bool
    """
    context = {
        "user_id": user.id,
        "contact_id": None,
        "org_ids": {
            "customer": [],
            "vendor": [],
            "manufacturer": [],
            "employee": [],
            "rep": [],
        },
        "roles": [],
        "is_superuser": user.is_superuser,
    }
    
    # The login is the Contact (AUTH_USER_MODEL = core.Contact).
    context["contact_id"] = user.id
    role = access.user_role(user)
    context["roles"] = [role] if role else []
    links = ((getattr(user, 'refs', None) or {}).get('links') or {})
    # 'rep' joined these on 2026-09-20: a rep is staff, and their rows are the customers
    # and documents assigned to their rep org (contacts.rep_id). Without it there was no
    # token a rep's scope could be written against.
    for org_type in ("customer", "vendor", "manufacturer", "employee", "rep"):
        ids = []
        fk_id = getattr(user, f"{org_type}_id", None)
        if fk_id:
            ids.append(fk_id)
        for link in links.get(org_type, []) or []:
            link_id = link.get("id") if isinstance(link, dict) else None
            if link_id and link_id not in ids:
                ids.append(link_id)
        context["org_ids"][org_type] = ids
    return context


# =============================================================================
# Filter Configuration Lookup
# =============================================================================

def get_user_filter_config(user: AbstractUser, model_name: str) -> Optional[dict]:
    """The access block for this user on this model, or None (no access).

    Block keys: view, edit, scope, edit_scope, create, delete (access.py).
    """
    return access.block_for(user, model_name)


# =============================================================================
# Q Object Builder
# =============================================================================

def build_filter_q(filter_dict: dict) -> Q:
    """
    Build a Django Q object from a filter dictionary.
    
    Handles:
    - Simple filters: {"customer_id": 5}
    - __in lookups: {"customer_id__in": [1, 2, 3]}
    - OR conditions via $or key: {"$or": [{"customer_id": 1}, {"vendor_id": 2}]}
    
    Args:
        filter_dict: Resolved filter dictionary
    
    Returns:
        Django Q object
    """
    if not filter_dict:
        return Q()
    
    # Handle $or / OR at top level
    or_key = "$or" if "$or" in filter_dict else ("OR" if "OR" in filter_dict else None)
    if or_key:
        or_conditions = filter_dict.pop(or_key)
        or_q = Q()
        for condition in or_conditions:
            or_q |= build_filter_q(condition)
        
        # Combine with any remaining AND conditions
        and_q = Q(**filter_dict) if filter_dict else Q()
        return and_q & or_q
    
    # Handle links lookups (refs.links.<model>[*].id)
    # These require JSON containment queries
    links_filters = {}
    standard_filters = {}
    
    for key, value in filter_dict.items():
        if key.startswith("refs__links__"):
            links_filters[key] = value
        else:
            standard_filters[key] = value
    
    q = Q(**standard_filters) if standard_filters else Q()
    
    # Build JSON containment queries for links
    for key, value in links_filters.items():
        q &= _links_contains_q(key, value)

    return q


def _links_contains_q(key: str, value) -> Q:
    """JSON containment for refs.links lookups.

    `[{"id": "$user.org_ids.vendor"}]` resolves to `[{"id": [5530, 5531]}]`, which
    never matches stored `[{"id": 5530}]`. Expand each list-valued key into one
    containment clause per id, OR'd together. An empty id list matches nothing.
    """
    if not isinstance(value, list):
        return Q(**{key: value})
    q = Q()
    matched_any = False
    for entry in value:
        if isinstance(entry, dict):
            list_key = next((k for k, v in entry.items() if isinstance(v, list)), None)
            if list_key is not None:
                for item_id in entry[list_key]:
                    q |= Q(**{key: [{**entry, list_key: item_id}]})
                    matched_any = True
                continue
        q |= Q(**{key: [entry]})
        matched_any = True
    return q if matched_any else Q(pk__in=[])


# =============================================================================
# Main API
# =============================================================================

def inject_role_filters(
    user: AbstractUser,
    model_name: str,
    existing_q: Optional[Q] = None
) -> Q:
    """
    Inject role-based query filters for a user/model.
    
    Main entry point for RBAC query filtering.
    
    Args:
        user: Django User instance
        model_name: Model being queried
        existing_q: Optional existing Q object to combine with
    
    Returns:
        Q object with role filters applied
    
    Example:
        # In view:
        q = inject_role_filters(request.user, "order")
        orders = Order.objects.filter(q)
    """
    existing_q = existing_q or Q()

    if access.is_open_read(model_name):
        return existing_q if access.user_role(user) else Q(pk__isnull=True)

    config = get_user_filter_config(user, model_name)
    if not config:
        # No block for this role on this model: no rows.
        return Q(pk__isnull=True)

    query_filters = dict(config.get("scope") or {})
    if not query_filters:
        # An empty scope is every row (a row rule, not a field wildcard).
        return existing_q
    
    # Resolve variables
    user_context = build_user_context(user)
    resolved_filters = resolve_filter_variables(query_filters, user_context)
    
    # Handle empty org_ids (user has role but no orgs assigned)
    # Replace empty lists with impossible condition
    for key, value in list(resolved_filters.items()):
        if isinstance(value, list) and len(value) == 0:
            if "__in" in key:
                # Empty __in list: no results for this path
                # Keep it - Django handles empty __in as no match
                pass
    
    # Build Q object
    role_q = build_filter_q(resolved_filters)
    
    return existing_q & role_q


def get_allowed_fields(
    user: AbstractUser,
    model_name: str,
    mode: str = "view"
) -> list:
    """
    Get list of allowed fields for user/model.

    Args:
        user: Django User instance
        model_name: Model name
        mode: "view" or "edit"

    Returns:
        List of leaf paths. Empty = nothing.
    """
    if access.is_open_read(model_name):
        from apps.core.services import field_leaves as fl
        if not access.user_role(user) or (mode != "view" and not access.open_read_can_write(user)):
            return []
        return sorted(fl.model_leaves(access.model_key(model_name))['leaves'])
    config = get_user_filter_config(user, model_name)
    if not config:
        return []
    return _resolve_field_tokens(config.get("view" if mode == "view" else "edit", []), user)


def user_price_level(user: AbstractUser) -> str:
    """The price level of the org this user belongs to ('' when there is none).

    A customer sees their own price, not every tier — so a role's view_fields can
    say price.$user.price_level (Bill, 2026-09-17).
    """
    try:
        org = getattr(user, 'customer', None) or getattr(user, 'vendor', None)
        return (getattr(org, 'price_level', '') or '').strip()
    except Exception:
        return ''


def _resolve_field_tokens(fields, user) -> list:
    """Replace $user.price_level in field paths. A path whose token cannot be
    resolved is dropped — never widened to every tier."""
    if not isinstance(fields, list) or not any(
            isinstance(f, str) and '$user.' in f for f in fields):
        return fields
    level = user_price_level(user)
    resolved = []
    for field in fields:
        if isinstance(field, str) and '$user.price_level' in field:
            if not level:
                continue
            field = field.replace('$user.price_level', level)
        resolved.append(field)
    return resolved


def get_edit_filters(
    user: AbstractUser,
    model_name: str,
) -> Optional[dict]:
    """Row-level edit rule for user/model, variables resolved; None when every
    visible row may be edited. Wide visibility, narrow edit (e.g. a customer sees
    the project's actions but edits only those assigned to them)."""
    config = get_user_filter_config(user, model_name)
    if not config or not config.get("edit_scope"):
        return None
    return resolve_filter_variables(config["edit_scope"], build_user_context(user))


def can_create(user: AbstractUser, model_name: str) -> bool:
    """Check if user can create records for a model."""
    if access.is_open_read(model_name):
        return access.open_read_can_write(user)
    config = get_user_filter_config(user, model_name)
    return bool(config and config.get("create"))


def can_delete(user: AbstractUser, model_name: str) -> bool:
    """Check if user can delete records for a model."""
    if access.is_open_read(model_name):
        return access.open_read_can_write(user)
    config = get_user_filter_config(user, model_name)
    return bool(config and config.get("delete"))
