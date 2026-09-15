# Core utility modules

# Import commonly used utilities for convenience (tolerant if misc module is absent)
try:
    from ..management.commands.misc.misc import (
        validate_filename_length,
        sanitize_filename,
        generate_barcode_data,
        extract_keywords_from_text,
        format_currency_amount,
        calculate_percentage_change,
        safe_divide,
        truncate_text,
        merge_dicts,
        WebClerk2Utils,
    )
    _MISC_EXPORTS = [
        'validate_filename_length',
        'sanitize_filename',
        'generate_barcode_data',
        'extract_keywords_from_text',
        'format_currency_amount',
        'calculate_percentage_change',
        'safe_divide',
        'truncate_text',
        'merge_dicts',
        'WebClerk2Utils',
    ]
except Exception:
    _MISC_EXPORTS = []

from .policy import get_accessible_fields

__all__ = _MISC_EXPORTS + [
    'get_accessible_fields',
]