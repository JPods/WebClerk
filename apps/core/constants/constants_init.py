"""
Dynamic constants initialization from database Settings.

This module provides a flexible system for loading constants from Setting records
with purpose='constant_init'. This enables:

- Remote updates of constants without code deployments
- Industry-specific constant variations
- Auditable constant changes
- Cached performance with Redis backend

Setting records structure:
- purpose: 'constant_init'
- model_name: category name (e.g., 'industry_specific', 'ui_defaults', 'business_rules')
- data: JSON object with constant key-value pairs
- is_active: boolean flag for enabling/disabling

Example Setting record:
{
    "purpose": "constant_init",
    "model_name": "industry_specific",
    "data": {
        "default_currency": "USD",
        "tax_rate": 0.08,
        "business_hours": {"start": "09:00", "end": "17:00"}
    },
    "is_active": true
}
"""

from typing import Dict, Any, Optional, Union
from apps.core.services.cache_service import cache_service
from apps.core.models.setting import Setting


def load_constants_from_settings() -> Dict[str, Dict[str, Any]]:
    """
    Load all constants from active Setting records with purpose='constant_init'.

    Returns:
        Dict with category names as keys, containing constant dictionaries as values.
        Example: {
            'industry_specific': {'default_currency': 'USD', 'tax_rate': 0.08},
            'ui_defaults': {'theme': 'dark', 'language': 'en'}
        }
    """
    constants = {}

    try:
        # Query all active constant_init settings
        setting_qs = Setting.objects.filter(
            purpose='constant_init',
            is_active=True
        ).only('model_name', 'data')

        for setting in setting_qs:
            category = setting.name or setting.model_name or 'general'  # Try name first, fallback to model_name
            if category not in constants:
                constants[category] = {}

            # Merge setting data into category (later settings override earlier ones)
            setting_data = setting.data or {}
            constants[category].update(setting_data)

    except Exception:
        # Graceful degradation if database unavailable during startup
        pass

    return constants


def get_constants(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get constants with Redis caching.

    Args:
        category: Optional category name to get only that category's constants.
                 If None, returns all categories.

    Returns:
        Dictionary of constants for the requested category, or all categories if None.
    """
    cache_key = cache_service.make_key('constants', 'all')
    all_constants = cache_service.get(cache_key)

    if all_constants is None:
        all_constants = load_constants_from_settings()
        cache_service.set(cache_key, all_constants, ttl=3600)  # 1 hour cache

    if category:
        return all_constants.get(category, {})

    return all_constants


def get_constant(category: str, key: str, default=None) -> Any:
    """
    Get a specific constant value.

    Args:
        category: Category name
        key: Constant key within the category
        default: Default value if constant not found

    Returns:
        The constant value or default
    """
    category_constants = get_constants(category)
    return category_constants.get(key, default)


def invalidate_constants_cache():
    """Invalidate the constants cache, forcing reload on next access."""
    cache_key = cache_service.make_key('constants', 'all')
    cache_service.delete(cache_key)


# Global constants cache for fast access during runtime
_CACHED_CONSTANTS = None

def get_cached_constants(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get constants with in-memory caching for high-performance access.

    This provides faster access than Redis for frequently accessed constants,
    while still allowing dynamic updates through cache invalidation.
    """
    global _CACHED_CONSTANTS

    if _CACHED_CONSTANTS is None:
        _CACHED_CONSTANTS = get_constants()

    if category:
        return _CACHED_CONSTANTS.get(category, {})

    return _CACHED_CONSTANTS


def refresh_cached_constants():
    """Refresh the in-memory constants cache."""
    global _CACHED_CONSTANTS
    _CACHED_CONSTANTS = get_constants()