"""
Role-based permissions and field access rules for the application.
"""

from typing import Dict, List, Optional

from rest_framework.permissions import BasePermission as DRFBasePermission


def _all_fields(model) -> List[str]:
    try:
        return [f.name for f in getattr(model, '_meta', {}).get('fields', [])]
    except Exception:
        return []


def _without(fields: List[str], excluded: List[str]) -> List[str]:
    excluded_set = set(excluded or [])
    return [f for f in fields if f not in excluded_set]


def get_role_field_rules(model, role: str) -> Dict[str, List[str]]:
    """
    Get field access rules for a specific model and user role.

    Args:
        model: Django model class
        role: User role string (e.g., 'admin', 'manager', 'user')

    Returns:
        Dict with 'view' and 'edit' keys containing lists of allowed field names
    """
    if not model:
        return {'view': [], 'edit': []}

    model_name = getattr(model, '_meta', {}).get('model_name', '').lower()

    base_fields = ['id', 'uuid', 'dt_created', 'dt_modified']
    ownership_fields = ['created_by', 'owner', 'contact', 'user', 'assigned_to', 'assignee']

    model_name = getattr(model, '_meta', {}).get('model_name', '').lower()
    all_fields = _all_fields(model)

    default_rules = {
        'admin': {'view': None, 'edit': None},
        'employee': {'view': None, 'edit': None},
        'user': {
            'view': base_fields + ownership_fields + ['name', 'status', 'description'],
            'edit': base_fields + ownership_fields + ['description', 'status'],
        },
        '': {'view': base_fields, 'edit': []},
    }

    # Per-model overrides
    contact_view_user = base_fields + [
        'email', 'name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix',
        'company', 'title', 'department', 'comment', 'attention',
        'is_active', 'dt_joined'
    ]
    contact_edit_user = base_fields + [
        'name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix',
        'company', 'title', 'department', 'comment'
    ]

    contact_edit_employee = _without(all_fields, [
        'role', 'is_superuser', 'is_staff', 'password', 'last_login'
    ]) or contact_edit_user

    model_rules = {
        'contact': {
            'admin': {'view': None, 'edit': None},
            'employee': {'view': None, 'edit': contact_edit_employee},
            'user': {'view': contact_view_user, 'edit': contact_edit_user},
        },
    }

    role_rules = model_rules.get(model_name, default_rules)
    rules = role_rules.get(role, role_rules.get('user', default_rules['user']))

    if rules.get('view') is None:
        rules = dict(rules)
        rules['view'] = all_fields
    if rules.get('edit') is None:
        rules = dict(rules)
        rules['edit'] = all_fields

    return rules


def has_permission(user, permission: str, obj=None) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user: Django user object
        permission: Permission string
        obj: Optional object for object-level permissions

    Returns:
        Boolean indicating if user has permission
    """
    if not user or not user.is_authenticated:
        return False

    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Check user role
    user_role = getattr(user, 'role', '')

    # Role-based permissions
    role_permissions = {
        'admin': ['*'],
        'employee': [
            'view_all', 'edit_own', 'edit_team', 'create', 'approve', 'manage_team'
        ],
        'user': [
            'view_own', 'edit_own', 'create'
        ],
    }

    allowed_permissions = role_permissions.get(user_role, [])

    # Wildcard permission
    if '*' in allowed_permissions:
        return True

    return permission in allowed_permissions


def get_user_permissions(user) -> List[str]:
    """
    Get all permissions for a user.

    Args:
        user: Django user object

    Returns:
        List of permission strings
    """
    if not user or not user.is_authenticated:
        return []

    if user.is_superuser:
        return ['*']

    user_role = getattr(user, 'role', '')
    role_permissions = {
        'admin': ['*'],
        'employee': [
            'view_all', 'edit_own', 'edit_team', 'approve', 'manage_team',
            'create_invoice', 'edit_invoice', 'delete_invoice',
            'create_order', 'edit_order', 'approve_order',
            'create', 'create_proposal', 'edit_proposal', 'view_invoice', 'view_order'
        ],
        'user': [
            'view_own', 'edit_own', 'create',
            'create_proposal', 'edit_proposal',
            'view_invoice', 'view_order'
        ],
    }

    return role_permissions.get(user_role, [])


# ---------------------------------------------------------------------------
# DRF permission class – enforces authentication + role-based view/edit rules
# ---------------------------------------------------------------------------
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class ViewEditPermission(DRFBasePermission):
    """Check authentication and role-based access for view/edit operations.

    Resolves the model from the view's ``queryset`` (or ``get_queryset()``)
    and delegates to ``get_role_field_rules()`` to determine whether the
    current user's role is allowed to *view* (safe methods) or *edit*
    (write methods) that model.

    Usage::

        class OrderLineListCreate(generics.ListCreateAPIView):
            permission_classes = [ViewEditPermission]
            queryset = OrderLine.objects.active()
    """

    def _resolve_model(self, view):
        """Extract the model class from the view's queryset."""
        qs = getattr(view, 'queryset', None)
        if qs is not None:
            return qs.model
        if hasattr(view, 'get_queryset'):
            try:
                return view.get_queryset().model
            except Exception:
                pass
        return None

    def has_permission(self, request, view):
        # 1. Must be authenticated
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # 2. Superusers / admins bypass further checks
        if user.is_superuser:
            return True

        user_role = getattr(user, 'role', '') or ''
        if user_role == 'admin':
            return True

        # 3. Resolve model and field rules
        model = self._resolve_model(view)
        if model is None:
            # Cannot determine model — fall back to auth-only
            return True

        rules = get_role_field_rules(model, user_role)

        # 4. For read requests, the role must have at least one viewable field
        if request.method in SAFE_METHODS:
            return bool(rules.get('view'))

        # 5. For write requests, the role must have at least one editable field
        return bool(rules.get('edit'))