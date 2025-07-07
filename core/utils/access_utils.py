from django.core.exceptions import ObjectDoesNotExist
from ..models import Setting

def get_accessible_fields(table_name, mode, user):
    """
    Retrieve accessible fields for a given table and mode based on user roles.
    
    Args:
        table_name (str): The name of the table (e.g., 'addresses', 'emails').
        mode (str): The access mode ('view' or 'edit').
        user: The authenticated user object from the request.
    
    Returns:
        list: List of accessible fields. Returns [] if user is not authenticated or no fields are allowed.
    """
    if not user or not user.is_authenticated:
        return []

    user_roles = user.role if hasattr(user, 'role') and user.role else ['PUBLIC']

    try:
        setting = Setting.objects.get(
            table_name=table_name,
            purpose='view_edit',
            role='all',
            is_active=True
        )
        accessible_fields = set()
        for role in user_roles:
            role_data = setting.data.get(role, {})
            accessible_fields.update(role_data.get(mode, []))
        return list(accessible_fields)
    except ObjectDoesNotExist:
        return []