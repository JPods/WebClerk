"""
Role-based permissions and field access rules for the application.
"""

from typing import Dict, List, Optional


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

    # Base fields that are always accessible
    base_fields = ['id', 'uuid', 'dt_created', 'dt_modified']

    # Role-based field access rules
    role_rules = {
        'admin': {
            'view': None,  # None means all fields
            'edit': None,  # None means all fields
        },
        'manager': {
            'view': None,  # Can view all fields
            'edit': None,  # Can edit all fields
        },
        'user': {
            'view': base_fields + [
                'name', 'status', 'id_customer', 'id_vendor',
                'amount', 'total', 'price', 'quantity', 'description'
            ],
            'edit': base_fields + [
                'status', 'notes', 'description'
            ],
        },
        '': {  # Anonymous/empty role
            'view': base_fields,
            'edit': [],
        }
    }

    # Get rules for the role, default to user rules
    rules = role_rules.get(role, role_rules['user'])

    # If view/edit is None, get all fields from model
    if rules['view'] is None:
        rules = dict(rules)  # Make a copy
        model_fields = [f.name for f in getattr(model, '_meta', {}).get('fields', [])]
        rules['view'] = model_fields

    if rules['edit'] is None:
        rules = dict(rules)  # Make a copy
        model_fields = [f.name for f in getattr(model, '_meta', {}).get('fields', [])]
        rules['edit'] = model_fields

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
        'admin': ['*'],  # All permissions
        'manager': [
            'view_all', 'edit_own', 'approve', 'manage_team'
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
        'manager': [
            'view_all', 'edit_own', 'edit_team', 'approve', 'manage_team',
            'create_invoice', 'edit_invoice', 'delete_invoice',
            'create_order', 'edit_order', 'approve_order'
        ],
        'user': [
            'view_own', 'edit_own', 'create',
            'create_proposal', 'edit_proposal',
            'view_invoice', 'view_order'
        ],
    }

    return role_permissions.get(user_role, [])