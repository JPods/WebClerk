from __future__ import annotations
from django.db.models import QuerySet
from typing import List, Optional

try:
    from apps.core.utils.model_policies import read_allowlist as _mp_read_allowlist
except Exception:
    _mp_read_allowlist = None

def _org_scope_q(model_fields: set[str], user) -> Optional["Q"]:
    """Build org-based visibility constraints derived from the user's org associations."""
    try:
        from django.db.models import Q  # local import to avoid hard dependency at module import
    except Exception:
        return None

    org_field_names = {
        "org_id",
        "organization_id",
        "customer_id",
        "vendor_id",
        "manufacturer_id",
        "rep_id",
        "employee_id",
        "other_id",
    }

    # Capture user org pointers from Contact fields when present
    user_org_ids: dict[str, int] = {}
    for name in org_field_names:
        val = getattr(user, name.replace("_id", "_id"), None)
        if isinstance(val, int):
            user_org_ids[name] = val

    if not user_org_ids:
        return None

    clauses = []
    for field in org_field_names:
        if field in model_fields and field in user_org_ids:
            clauses.append(Q(**{field: user_org_ids[field]}))

    if not clauses:
        return None

    scope = clauses[0]
    for clause in clauses[1:]:
        scope |= clause
    return scope


def inject_constraints(qs: QuerySet, *, request, model_key: str) -> QuerySet:
    """Enforce tenant isolation and strict role-based visibility."""
    try:
        from django.conf import settings
        from django.db.models import Q

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return qs.none()

        role_value = getattr(user, 'role', None)
        user_role = str(role_value).lower() if role_value else None

        # Admin/staff/full-control roles: unrestricted
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False) or user_role == 'admin':
            return qs

        constraints = Q()

        # Tenant isolation first
        multi_tenant_enabled = getattr(settings, 'WCAPI_MULTI_TENANT_ENABLED', False)
        tenant_field = getattr(settings, 'WCAPI_TENANT_FIELD', 'tenant_id')
        if multi_tenant_enabled and hasattr(user, 'tenant_id'):
            constraints &= Q(**{tenant_field: getattr(user, 'tenant_id')})

        fields = {f.name for f in qs.model._meta.get_fields()}

        # Org-based scoping for employees and users (must be linked to an org profile)
        org_scope = _org_scope_q(fields, user)
        if org_scope is not None:
            constraints &= org_scope

        # Employees: after org scoping, allow ownership-like access as well
        if user_role == 'employee':
            ownership_clauses = []
            if 'created_by' in fields:
                ownership_clauses.append(Q(created_by=getattr(user, 'id', None)))
            if 'contact' in fields:
                ownership_clauses.append(Q(contact_id=getattr(user, 'id', None)))
            if 'owner' in fields:
                ownership_clauses.append(Q(owner_id=getattr(user, 'id', None)))
            if 'assigned_to' in fields:
                ownership_clauses.append(Q(assigned_to_id=getattr(user, 'id', None)) | Q(assigned_to=user))
            if 'assignee' in fields:
                ownership_clauses.append(Q(assignee_id=getattr(user, 'id', None)) | Q(assignee=user))
            if ownership_clauses:
                scope = ownership_clauses[0]
                for clause in ownership_clauses[1:]:
                    scope |= clause
                constraints &= scope
            if constraints:
                qs = qs.filter(constraints).distinct()
            return qs

        # User-level scope: own or explicitly assigned records
        ownership_clauses = []

        if 'created_by' in fields:
            ownership_clauses.append(Q(created_by=getattr(user, 'id', None)))
        if 'contact' in fields:
            ownership_clauses.append(Q(contact_id=getattr(user, 'id', None)))
        if 'owner' in fields:
            ownership_clauses.append(Q(owner_id=getattr(user, 'id', None)))
        if 'user' in fields:
            ownership_clauses.append(Q(user_id=getattr(user, 'id', None)))
        if 'assigned_to' in fields:
            ownership_clauses.append(Q(assigned_to_id=getattr(user, 'id', None)) | Q(assigned_to=user))
        if 'assignee' in fields:
            ownership_clauses.append(Q(assignee_id=getattr(user, 'id', None)) | Q(assignee=user))
        if 'shared_with' in fields:
            ownership_clauses.append(Q(shared_with__id=getattr(user, 'id', None)))
        
        # Transaction models: allow access via customer_id relationship
        # (Proposal, Order, Invoice, Purchase, WorkOrder, etc.)
        if 'customer_id' in fields:
            ownership_clauses.append(Q(customer_id=getattr(user, 'id', None)))

        # Special-case: Contact model (no ownership fields) -> allow self only
        model_name = getattr(qs.model._meta, 'model_name', '')
        if model_name.lower() == 'contact':
            constraints &= Q(pk=getattr(user, 'id', None))
        
        # Transaction models without ownership fields: allow all for authenticated users
        # These are business documents that employees need to access
        transaction_models = {
            'proposal', 'order', 'invoice', 'purchase', 'workorder',
            'proposalline', 'orderline', 'invoiceline', 'purchaseline', 'workorderline',
        }
        org_models = {
            'org',
            'orgbase',
            'customer',
            'vendor',
            'manufacturer',
            'rep',
            'employee',
        }
        is_transaction_model = model_name.lower() in transaction_models
        is_org_model = model_name.lower() in org_models

        if ownership_clauses:
            scope = ownership_clauses[0]
            for clause in ownership_clauses[1:]:
                scope |= clause
            constraints &= scope
        elif is_transaction_model or is_org_model:
            # Transaction models: authenticated users can access all records
            # (org-level scoping already applied above if enabled)
            pass
        elif model_name.lower() != 'contact':
            # No ownership-related fields and not contact/transaction; safest default is no access
            constraints &= Q(pk__in=[])

        if constraints:
            qs = qs.filter(constraints).distinct()
        return qs

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error applying settings constraints for {model_key}: {str(e)}")
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