"""
Mandatory Constants Definition and Initialization

This module defines the mandatory constants that must be present in the system
for proper operation. These constants are created automatically if they don't exist
during system initialization.

Mandatory constants are categorized and stored as Setting records with purpose='constant_init'.
They provide essential configuration values that the application depends on.
"""

from typing import Dict, Any, List, Tuple
from django.db import models
from apps.core.models.setting import Setting


# Define mandatory constants with their default values
MANDATORY_CONSTANTS = {
    "system_defaults": {
        "default_currency": "USD",
        "default_timezone": "UTC",
        "max_upload_size_mb": 10,
        "session_timeout_minutes": 60,
        "max_login_attempts": 5,
        "password_min_length": 8,
        "default_language": "en",
        "items_per_page": 25,
        "max_items_per_page": 100,
    },
    "business_rules": {
        "default_tax_rate": 0.0,
        "invoice_due_days": 30,
        "quote_valid_days": 30,
        "default_payment_terms": "Net 30",
        "auto_save_interval_seconds": 30,
        "max_line_items_per_transaction": 100,
        "decimal_precision": 2,
        "rounding_mode": "HALF_UP",
    },
    "ui_defaults": {
        "theme": "light",
        "date_format": "MM/DD/YYYY",
        "time_format": "12h",
        "number_format": "en-US",
        "currency_display": "symbol",
        "table_density": "comfortable",
        "sidebar_collapsed": False,
        "notifications_enabled": True,
    },
    "security": {
        "password_history_count": 5,
        "password_expiry_days": 90,
        "session_inactivity_timeout": 30,
        "two_factor_required": False,
        "audit_log_retention_days": 365,
        "max_concurrent_sessions": 3,
    },
    "integrations": {
        "email_enabled": True,
        "sms_enabled": False,
        "api_rate_limit_per_minute": 60,
        "webhook_timeout_seconds": 30,
        "max_webhook_retries": 3,
    },
    "performance": {
        "cache_ttl_seconds": 3600,
        "db_query_timeout_seconds": 30,
        "max_concurrent_requests": 100,
        "file_cache_size_mb": 100,
        "memory_cache_size_mb": 50,
    }
}


def get_mandatory_constants() -> Dict[str, Dict[str, Any]]:
    """
    Get the complete definition of mandatory constants.

    Returns:
        Dictionary with categories as keys and constant definitions as values.
    """
    return MANDATORY_CONSTANTS.copy()


def get_mandatory_constant(category: str, key: str, default=None) -> Any:
    """
    Get a specific mandatory constant value.

    Args:
        category: Constant category name
        key: Constant key within the category
        default: Default value if not found

    Returns:
        The constant value or default
    """
    return MANDATORY_CONSTANTS.get(category, {}).get(key, default)


def ensure_mandatory_constants_exist(verbose: bool = True) -> Dict[str, Any]:
    """
    Ensure all mandatory constants exist in the database.
    Creates any missing Setting records with default values.

    Args:
        verbose: Whether to print status messages

    Returns:
        Dictionary with 'created' and 'existing' lists of constant identifiers.
    """
    created = []
    existing = []
    updated = []

    for category, constants in MANDATORY_CONSTANTS.items():
        # Check if category setting exists
        # Note: Setting model validates model_name against registered models,
        # but for constants we use category names that aren't actual models.
        # We'll set model_name to None and use name field for identification.
        setting, created_flag = Setting.objects.get_or_create(
            purpose='constant_init',
            name=category,
            defaults={
                'data': constants,
                'is_active': True,
                'model_name': None
            }
        )

        if created_flag:
            if verbose:
                print(f"[CONSTANTS] Created {category} with {len(constants)} constants")
        else:
            if verbose:
                print(f"[CONSTANTS] Found existing {category} setting")

        if created_flag:
            created.append(f"{category}:all")
            if verbose:
                print(f"[CONSTANTS] Created {category} with {len(constants)} constants")
        else:
            existing.append(f"{category}:all")
            # Ensure all required keys exist in existing setting
            setting_updated = False
            current_data = setting.data or {}
            if not isinstance(current_data, dict):
                current_data = {}
                setting_updated = True

            for key, default_value in constants.items():
                if key not in current_data:
                    current_data[key] = default_value
                    setting_updated = True
                    if verbose:
                        print(f"[CONSTANTS] Added missing constant {category}.{key} = {default_value}")

            if setting_updated:
                setting.save(update_fields=['data'])
                updated.append(category)

    result = {
        'created': created,
        'existing': existing,
        'updated': updated,
        'total_categories': len(MANDATORY_CONSTANTS),
        'total_constants': sum(len(constants) for constants in MANDATORY_CONSTANTS.values())
    }

    if verbose:
        print(f"[CONSTANTS] Initialization complete: {len(created)} created, {len(updated)} updated, {len(existing)} existing")
        print(f"[CONSTANTS] Total: {result['total_categories']} categories, {result['total_constants']} constants")

    return result


def validate_mandatory_constants() -> Dict[str, Any]:
    """
    Validate that all mandatory constants are properly configured.

    Returns:
        Dictionary with validation results including any missing or invalid constants.
    """
    issues = {
        'missing_categories': [],
        'missing_constants': [],
        'invalid_types': [],
        'warnings': []
    }

    for category, required_constants in MANDATORY_CONSTANTS.items():
        try:
            # Get current setting - try name field first, then model_name
            setting = Setting.objects.filter(
                purpose='constant_init',
                is_active=True
            ).filter(
                models.Q(name=category) | models.Q(model_name=category)
            ).first()

            if not setting:
                issues['missing_categories'].append(category)
                continue

            current_data = setting.data or {}

            # Check for missing constants
            for key, expected_value in required_constants.items():
                if key not in current_data:
                    issues['missing_constants'].append(f"{category}.{key}")
                else:
                    # Type validation
                    current_value = current_data[key]
                    expected_type = type(expected_value)
                    if not isinstance(current_value, expected_type):
                        issues['invalid_types'].append(
                            f"{category}.{key}: expected {expected_type.__name__}, got {type(current_value).__name__}"
                        )

        except Exception as e:
            issues['warnings'].append(f"Error validating {category}: {e}")

    return {
        'valid': len(issues['missing_categories']) == 0 and len(issues['missing_constants']) == 0 and len(issues['invalid_types']) == 0,
        'issues': issues
    }


def get_constant_with_fallback(category: str, key: str, default=None):
    """
    Get a constant value with fallback to mandatory defaults.

    This function first tries to get the value from the cached constants,
    then falls back to the mandatory defaults if not found.

    Args:
        category: Constant category
        key: Constant key
        default: Final fallback value

    Returns:
        The constant value
    """
    from .constants_init import get_constant

    # Try to get from database constants first
    value = get_constant(category, key)
    if value is not None:
        return value

    # Fall back to mandatory defaults
    return get_mandatory_constant(category, key, default)


# Export public API
__all__ = [
    'MANDATORY_CONSTANTS',
    'get_mandatory_constants',
    'get_mandatory_constant',
    'ensure_mandatory_constants_exist',
    'validate_mandatory_constants',
    'get_constant_with_fallback',
]