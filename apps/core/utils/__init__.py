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
from .model_name_resolver import (
    resolve_model_name,
    parse_restful_path,
    url_to_model_name,
    model_name_to_url,
    get_transaction_type,
    get_model_class,
    validate_model_name,
    MODEL_NAME_MAP,
)

__all__ = _MISC_EXPORTS + [
    'get_accessible_fields',
    'resolve_model_name',
    'parse_restful_path',
    'url_to_model_name',
    'model_name_to_url',
    'get_transaction_type',
    'get_model_class',
    'validate_model_name',
    'MODEL_NAME_MAP',
]