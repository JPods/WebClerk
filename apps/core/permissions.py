"""
Role-based permissions and field access rules for the application.
"""

from typing import Dict, List, Optional


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