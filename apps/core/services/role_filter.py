"""
Role-Based Query Filter Service.

Applies role-based access restrictions to database queries.
Resolves role configuration → query filter variables → Django Q objects.

See readmes/topics/architecture/role-based-access-plan.md for full documentation.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.models import ModelRoleConfig, RoleConfig, UserProfile
from apps.core.services.role_defaults import ROLE_DEFAULTS, get_effective_config

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
        },
        "roles": [],
        "is_superuser": user.is_superuser,
    }
    
    # Get profile if exists
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return context
    
    if not profile.contact:
        return context
    
    context["contact_id"] = profile.contact.id
    context["roles"] = profile.get_roles()
    
    # Get org IDs for each type
    for org_type in ["customer", "vendor", "manufacturer", "employee"]:
        context["org_ids"][org_type] = profile.get_org_ids(org_type)
    
    return context


# =============================================================================
# Filter Configuration Lookup
# =============================================================================

def get_role_filter_config(
    model_name: str,
    role: str,
    use_db: bool = True
) -> Optional[dict]:
    """
    Get the filter configuration for a model/role combination.
    
    Checks database config first, falls back to ROLE_DEFAULTS.
    
    Args:
        model_name: e.g., "order", "invoice", "customer"
        role: e.g., "user_sales", "user_customer"
        use_db: If True, check DB first; if False, use defaults only
    
    Returns:
        Dict with query_filters, view_fields, edit_fields, etc.
        or None if role has no access to model
    """
    # Try database first
    if use_db:
        try:
            # Check role is active via RoleConfig
            role_active = RoleConfig.objects.filter(
                role=role, is_active=True
            ).exists()
            if role_active:
                db_config = ModelRoleConfig.objects.filter(
                    role=role,
                    model_name=model_name,
                ).first()

                if db_config:
                    return {
                        "query_filters": db_config.query_filters or {},
                        "view_fields": db_config.view_fields or [],
                        "edit_fields": db_config.edit_fields or [],
                        "allow_create": db_config.allow_create,
                        "allow_delete": db_config.allow_delete,
                    }
        except Exception:
            pass  # Fall back to defaults
    
    # Use code defaults
    return get_effective_config(role, model_name)


def get_user_filter_config(
    user: AbstractUser,
    model_name: str
) -> Optional[dict]:
    """
    Get the filter configuration for a user/model based on their roles.
    
    If user has multiple roles, uses the most permissive (superuser > admin > others).
    
    Args:
        user: Django User instance
        model_name: Model name to get config for
    
    Returns:
        Dict with query_filters, view_fields, etc.
    """
    # Superusers see everything
    if user.is_superuser:
        return {
            "query_filters": {},  # No filters = all records
            "view_fields": ["*"],
            "edit_fields": ["*"],
            "allow_create": True,
            "allow_delete": True,
        }
    
    # Get user's roles
    context = build_user_context(user)
    roles = context.get("roles", [])
    
    if not roles:
        return None  # No access
    
    # Priority order for roles (most permissive first)
    role_priority = [
        "admin",
        "user_accounting",
        "user_sales",
        "user_production",
        "user_warehouse",
        "user_rep",
        "user_manufacturer",
        "user_vendor",
        "user_customer",
    ]
    
    # Find the highest-priority role that has config for this model
    for priority_role in role_priority:
        if priority_role in roles:
            config = get_role_filter_config(model_name, priority_role)
            if config:
                return config
    
    # Try any role the user has
    for role in roles:
        config = get_role_filter_config(model_name, role)
        if config:
            return config
    
    return None  # No matching config


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
    
    # Handle $or at top level
    if "$or" in filter_dict:
        or_conditions = filter_dict.pop("$or")
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
        # refs__links__customer__contains → needs special handling
        # For now, use standard Django JSON lookups
        q &= Q(**{key: value})
    
    return q


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
    
    # Superusers bypass all filters
    if user.is_superuser:
        return existing_q
    
    # Get config for user's roles
    config = get_user_filter_config(user, model_name)
    
    if not config:
        # No access config means deny all
        return Q(pk__isnull=True)  # Returns no results
    
    query_filters = config.get("query_filters", {})
    
    if not query_filters:
        # Empty filters = no restrictions (e.g., admin role)
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
        List of field names, or ["*"] for all fields
    """
    if user.is_superuser:
        return ["*"]
    
    config = get_user_filter_config(user, model_name)
    
    if not config:
        return []
    
    field_key = "view_fields" if mode == "view" else "edit_fields"
    return config.get(field_key, [])


def can_create(user: AbstractUser, model_name: str) -> bool:
    """Check if user can create records for a model."""
    if user.is_superuser:
        return True
    
    config = get_user_filter_config(user, model_name)
    return config.get("allow_create", False) if config else False


def can_delete(user: AbstractUser, model_name: str) -> bool:
    """Check if user can delete records for a model."""
    if user.is_superuser:
        return True
    
    config = get_user_filter_config(user, model_name)
    return config.get("allow_delete", False) if config else False
