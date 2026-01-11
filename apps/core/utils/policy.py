from __future__ import annotations
from django.db.models import QuerySet
from typing import List, Optional

try:
    from apps.core.utils.model_policies import read_allowlist as _mp_read_allowlist
except Exception:
    _mp_read_allowlist = None

def inject_constraints(qs: QuerySet, *, request, model_key: str) -> QuerySet:
    """Enforce role/tenant/publish/reserved rules via Settings.
    
    This function applies constraint rules based on Django settings and user context.
    It supports multi-tenant isolation, role-based access control, and publish/reserved
    status filtering.
    
    Args:
        qs: QuerySet to apply constraints to
        request: Django request object for user context
        model_key: Model key for specific constraint lookup
        
    Returns:
        QuerySet with applied constraints
    """
    try:
        from django.contrib.auth import get_user_model
        from django.conf import settings
        from django.db.models import Q
        
        # Get user from request
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return qs.none()  # No access for unauthenticated users
            
        User = get_user_model()
        
        # Check if user is staff/admin - they get full access
        if hasattr(user, 'is_staff') and user.is_staff:
            return qs
        role_value = getattr(user, 'role', None)
        normalized_role = role_value.strip().lower() if isinstance(role_value, str) else None
        if normalized_role in {'staff', 'admin'}:
            return qs
        user_role = normalized_role
            
        # Initialize constraints list
        constraints = Q()
        
        # 1. TENANT ISOLATION
        # Apply tenant isolation if multi-tenant setup is enabled
        multi_tenant_enabled = getattr(settings, 'WCAPI_MULTI_TENANT_ENABLED', False)
        tenant_field = getattr(settings, 'WCAPI_TENANT_FIELD', 'tenant_id')
        
        if multi_tenant_enabled and hasattr(user, 'tenant_id'):
            tenant_constraint = {tenant_field: user.tenant_id}
            constraints &= Q(**tenant_constraint)
            
        # 2. ROLE-BASED ACCESS CONTROL
        # Apply role-based constraints from settings
        role_constraints = getattr(settings, 'WCAPI_ROLE_CONSTRAINTS', {})
        
        if user_role:
            # Model-specific role constraints
            model_role_constraints = role_constraints.get(model_key, {})
            role_specific_constraints = model_role_constraints.get(user_role, {})
            
            for constraint_field, constraint_value in role_specific_constraints.items():
                constraints &= Q(**{constraint_field: constraint_value})
                
            # Global role constraints (apply to all models)
            global_role_constraints = role_constraints.get('global', {})
            global_specific_constraints = global_role_constraints.get(user_role, {})
            
            for constraint_field, constraint_value in global_specific_constraints.items():
                constraints &= Q(**{constraint_field: constraint_value})
                
        # 3. PUBLISH STATUS FILTERING
        # Apply publish status filtering based on user role
        publish_constraints = getattr(settings, 'WCAPI_PUBLISH_CONSTRAINTS', {})
        
        if user_role:
            # Models that require publish status
            published_only_models = publish_constraints.get('published_only_models', [])
            if model_key in published_only_models:
                if user_role in ['public', 'guest']:
                    # Public users can only see published items
                    if 'is_published' in [f.name for f in qs.model._meta.get_fields()]:
                        constraints &= Q(is_published=True)
                elif user_role in ['user', 'member']:
                    # Regular users see published items and their own drafts
                    if 'is_published' in [f.name for f in qs.model._meta.get_fields()]:
                        constraints &= Q(is_published=True) | Q(created_by=user.id)
                        
        # 4. RESERVED STATUS FILTERING
        # Apply reserved status filtering
        reserved_constraints = getattr(settings, 'WCAPI_RESERVED_CONSTRAINTS', {})
        
        if user_role:
            # Models that have reserved status
            reserved_models = reserved_constraints.get('reserved_models', [])
            if model_key in reserved_models:
                if 'is_reserved' in [f.name for f in qs.model._meta.get_fields()]:
                    if user_role in ['admin', 'staff']:
                        # Admins can see both reserved and non-reserved
                        pass
                    elif user_role in ['manager', 'supervisor']:
                        # Managers can see reserved items they created or are assigned to
                        constraints &= Q(is_reserved=False) | Q(
                            Q(created_by=user.id) | Q(assigned_to=user.id)
                        )
                    else:
                        # Regular users only see non-reserved items
                        constraints &= Q(is_reserved=False)
                        
        # 5. CUSTOM MODEL CONSTRAINTS
        # Apply custom model-specific constraints from settings
        custom_constraints = getattr(settings, 'WCAPI_CUSTOM_CONSTRAINTS', {})
        model_custom_constraints = custom_constraints.get(model_key, {})
        
        # Apply status-based constraints
        status_constraints = model_custom_constraints.get('status_constraints', {})
        if user_role:
            status_filter = status_constraints.get(user_role)
            if status_filter:
                constraints &= Q(status=status_filter)
                
        # Apply ownership constraints
        ownership_constraints = model_custom_constraints.get('ownership_constraints', {})
        if ownership_constraints.get('enabled', False):
            if user_role in ['user', 'member']:
                # Users can only see their own records
                constraints &= Q(created_by=user.id)
            elif user_role in ['manager', 'supervisor']:
                # Managers can see their own records and records of users they manage
                managed_user_ids = getattr(user, 'managed_user_ids', [])
                if managed_user_ids:
                    constraints &= Q(created_by=user.id) | Q(created_by__in=managed_user_ids)
                    
        # 6. TIME-BASED CONSTRAINTS
        # Apply time-based access constraints
        time_constraints = getattr(settings, 'WCAPI_TIME_CONSTRAINTS', {})
        model_time_constraints = time_constraints.get(model_key, {})
        
        if model_time_constraints.get('enabled', False):
            from django.utils import timezone
            from datetime import timedelta
            
            # Only show records from the last N days for certain roles
            days_back = model_time_constraints.get('days_back', 30)
            if user_role in ['user', 'member']:
                cutoff_date = timezone.now() - timedelta(days=days_back)
                constraints &= Q(dt_created__gte=cutoff_date)
                
        # Apply all constraints to the queryset
        if constraints:
            qs = qs.filter(constraints)
            
        return qs
        
    except Exception as e:
        # Log the error but don't break the query
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error applying settings constraints for {model_key}: {str(e)}")
        return qs  # Return unfiltered queryset on error to avoid breaking functionality

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