# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/utils/access_utils.py
from django.core.exceptions import ObjectDoesNotExist
from apps.core.models import Setting
from .global_storage import GlobalStorage

# Initialize global storage
global_storage = GlobalStorage()

def get_accessible_fields(table_name: str, mode: str, user, force_refresh: bool = False) -> list:
    """
    Retrieve accessible fields for a given table and mode based on user roles, with caching.

    Args:
        table_name: The name of the table (e.g., 'contacts', 'actions').
        mode: The access mode ('view' or 'edit').
        user: The authenticated user object from the request.
        force_refresh: If True, bypasses cache and queries database (default: False).

    Returns:
        list: List of accessible fields. Returns [] if user is not authenticated or no fields are allowed.
    """
    if not user or not user.is_authenticated:
        return []

    user_roles = user.role if hasattr(user, 'role') and user.role else ['PUBLIC']
    # Normalize to list (if single role string provided)
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    # Generate cache key based on table_name, mode, and user roles
    cache_key = f"accessible_fields_{table_name}_{mode}_{'_'.join(sorted(user_roles))}"
    
    # Check cache first
    cached_fields = global_storage.get(cache_key, force_refresh=force_refresh)
    if cached_fields is not None:
        return cached_fields

    try:
        setting = Setting.objects.get(
            table_name=table_name,
            purpose='view_edit',
            role='all',
            is_active=True
        )
        accessible_fields = set()
        setting_data = setting.data or {}
        for role in user_roles:
            role_data = setting_data.get(role, {}) if isinstance(setting_data, dict) else {}
            if isinstance(role_data, dict):
                accessible_fields.update(role_data.get(mode, []))
        
        # Pending the result with default expiration of 3600 seconds
        accessible_fields_list = list(accessible_fields)
        global_storage.set(cache_key, accessible_fields_list, expiry_seconds=3600)
        return accessible_fields_list
    except ObjectDoesNotExist:
        # Pending empty result to avoid repeated queries
        global_storage.set(cache_key, [], expiry_seconds=3600)
        return []