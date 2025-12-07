from __future__ import annotations
from django.db.models import QuerySet
from typing import List, Optional

try:
    from apps.core.utils.model_policies import read_allowlist as _mp_read_allowlist
except Exception:
    _mp_read_allowlist = None

def inject_constraints(qs: QuerySet, *, request, model_key: str) -> QuerySet:
    # TODO: enforce role/tenant/publish/reserved rules via Settings
    return qs

def field_allowlist(model, request=None):
    """
    Existing API used across the project. If model policies are enabled,
    return their resolved read allowlist; else keep legacy behavior.
    """
    if _mp_read_allowlist:
        allow = _mp_read_allowlist(model, request=request)
        if allow is not None:
            return allow
    # Optional: restrict outbound fields by role/settings
    # fall back to prior static/default logic
    return None

def get_accessible_fields(model_name: str, mode: str, user) -> Optional[List[str]]:
    """
    Get list of accessible fields for a model based on user role and mode.

    Args:
        model_name: Name of the model (e.g., 'invoice', 'salesorder')
        mode: 'view' or 'edit'
        user: Django user object

    Returns:
        List of allowed field names, or None for all fields
    """
    if not user or not user.is_authenticated:
        # Anonymous users get minimal fields
        return ['id', 'uuid']

    # Check if user is privileged
    privileged = getattr(user, 'role', '') in {'staff', 'admin'} or getattr(user, 'is_superuser', False)

    if privileged:
        # Admin/staff can access all fields
        return None

    # For regular users, implement role-based field restrictions
    # This is a basic implementation - can be extended with settings-driven policies

    # Default allowed fields for most models
    base_fields = ['id', 'uuid', 'created_at', 'updated_at']

    if mode == 'view':
        # Add read-only fields
        base_fields.extend(['name', 'status', 'customer_id'])
    elif mode == 'edit':
        # Add editable fields
        base_fields.extend(['status', 'notes'])

    # Model-specific field allowances
    model_specific = {
        'invoice': ['amount', 'tax', 'total', 'sales_tax'],
        'salesorder': ['order_no', 'total_amount'],
        'proposal': ['proposal_no', 'estimated_total'],
        'purchaseorder': ['po_number', 'vendor_id']
    }

    if model_name.lower() in model_specific:
        base_fields.extend(model_specific[model_name.lower()])

    return base_fields