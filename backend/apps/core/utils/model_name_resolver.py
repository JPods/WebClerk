"""
Model Name Resolver

Centralizes all model name translation for the wcapi endpoints.
Converts RESTful-style paths and various naming conventions to 
the canonical wcapi model_name format.

Security: All data access flows through wcapi endpoints, never directly to REST endpoints.
This provides a single point of control for authentication, authorization, and auditing.

Usage:
    from apps.core.utils.model_name_resolver import resolve_model_name, parse_restful_path
    
    resolve_model_name('order')           -> 'order'
    resolve_model_name('purchase')         -> 'purchase'
    resolve_model_name('invoice')         -> 'invoice'
    
    parse_restful_path('/api/transactions/order/22')
    -> {'model_name': 'order', 'id': 22}
"""

import re
from typing import Optional, Dict, Any
from django.apps import apps


# Canonical model name mappings
# Keys are normalized (lowercase, no separators), values are the wcapi model_name
MODEL_NAME_MAP: Dict[str, str] = {
    # Transactions
    'order': 'order',
    'invoice': 'invoice',
    'purchase': 'purchase',
    'po': 'purchase',
    'proposal': 'proposal',
    'quote': 'proposal',
    'workorder': 'workorder',
    'work': 'workorder',
    'wo': 'workorder',
    'requisition': 'requisition',
    'req': 'requisition',
    
    # Transaction Lines
    'orderline': 'order_line',
    'invoiceline': 'invoice_line',
    'purchaseline': 'purchase_line',
    'poline': 'purchase_line',
    'proposalline': 'proposal_line',
    'quoteline': 'proposal_line',
    'workorderline': 'work_order_line',
    'woline': 'work_order_line',
    'requisitionline': 'requisition_line',
    'reqline': 'requisition_line',
    
    # Organizations
    'customer': 'customer',
    'vendor': 'vendor',
    'manufacturer': 'manufacturer',
    'rep': 'rep',
    'employee': 'employee',
    'organization': 'organization',
    'org': 'organization',
    
    # Products
    'item': 'item',
    'product': 'item',
    'category': 'category',
    'warehouse': 'warehouse',
    'serial': 'serial',
    'variant': 'variant',
    'specification': 'specification',
    'spec': 'specification',
    
    # Core
    'contact': 'contact',
    'address': 'address',
    'setting': 'setting',
    'report': 'report',
    'action': 'action',
    
    # Communications
    'email': 'email',
    'phone': 'phone',
    'domain': 'domain',
    
    # Accounts
    'audit': 'audit',
    'currency': 'currency',
    'glaccount': 'gl_account',
    'gljournal': 'gl_journal',
    'ledger': 'ledger',
    'taxjurisdiction': 'tax_jurisdiction',
    'term': 'term',
    
    # Support
    'campaign': 'campaign',
    'task': 'task',
    'event': 'event',
    
    # Sync
    'bundle': 'bundle',
}

# RESTful path patterns to model name
# Handles paths like /api/transactions/order/22
PATH_PATTERN_MAP: Dict[str, str] = {
    'transactions/order': 'order',
    'transactions/orders': 'order',
    'transactions/invoice': 'invoice',
    'transactions/purchase': 'purchase',
    'transactions/proposal': 'proposal',
    'transactions/work-order': 'workorder',
    'transactions/workorder': 'workorder',
    'transactions/requisition': 'requisition',
    'orgs/customer': 'customer',
    'orgs/vendor': 'vendor',
    'orgs/manufacturer': 'manufacturer',
    'orgs/rep': 'rep',
    'orgs/employee': 'employee',
    'orgs/organization': 'organization',
    'products/item': 'item',
    'products/category': 'category',
    'products/warehouse': 'warehouse',
    'core/contact': 'contact',
    'core/address': 'address',
    'core/setting': 'setting',
    'core/action': 'action',
    'communications/email': 'email',
    'communications/phone': 'phone',
    'accounts/audit': 'audit',
    'accounts/currency': 'currency',
    'accounts/gl-account': 'gl_account',
    'accounts/ledger': 'ledger',
    'support/campaign': 'campaign',
    'support/task': 'task',
}

# URL-friendly format mappings (model_name -> url_segment)
URL_MAP: Dict[str, str] = {
    'order': 'order',
    'purchase': 'purchase',
    'workorder': 'work-order',
    'order_line': 'order-line',
    'purchase_line': 'purchase-line',
    'work_order_line': 'work-order-line',
    'invoice_line': 'invoice-line',
    'proposal_line': 'proposal-line',
    'gl_account': 'gl-account',
    'gl_journal': 'gl-journal',
    'tax_jurisdiction': 'tax-jurisdiction',
}

# Transaction type mappings for routing
TRANSACTION_TYPE_MAP: Dict[str, str] = {
    'order': 'order',
    'invoice': 'invoice',
    'purchase': 'purchase',
    'proposal': 'proposal',
    'workorder': 'work_order',
    'requisition': 'requisition',
}


def normalize(input_str: str) -> str:
    """
    Normalize a string by removing separators and converting to lowercase.
    
    Args:
        input_str: String to normalize
        
    Returns:
        Normalized string (lowercase, no separators)
    """
    if not input_str:
        return ''
    # Remove hyphens, underscores, slashes and convert to lowercase
    return re.sub(r'[-_/]', '', input_str).lower()


def resolve_model_name(input_str: str, strict: bool = False) -> str:
    """
    Resolve a model name from various formats to the canonical wcapi model_name.
    
    Args:
        input_str: Model name in any format (kebab-case, snake_case, camelCase, etc.)
        strict: If True, raise ValueError for unknown model names
        
    Returns:
        Canonical wcapi model_name
        
    Raises:
        ValueError: If input is empty or (if strict=True) model name cannot be resolved
        
    Examples:
        resolve_model_name('order')          -> 'order'
        resolve_model_name('purchase')        -> 'purchase'
        resolve_model_name('invoice')        -> 'invoice'
    """
    if not input_str:
        raise ValueError('Model name is required')
    
    # First, try direct lookup after normalization
    normalized = normalize(input_str)
    if normalized in MODEL_NAME_MAP:
        return MODEL_NAME_MAP[normalized]
    
    # If input looks like a path, try path pattern matching
    lower_input = input_str.lower()
    for pattern, model_name in PATH_PATTERN_MAP.items():
        if pattern in lower_input:
            return model_name
    
    # Strict mode: raise error for unknown model names
    if strict:
        raise ValueError(f'Unknown model name: {input_str}')
    
    # Fallback: assume the normalized input IS the model name
    # This handles cases where the exact model name is passed
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f'[resolve_model_name] Unknown model "{input_str}", using normalized: "{normalized}"')
    return normalized


def parse_restful_path(path: str) -> Dict[str, Any]:
    """
    Extract model name and ID from a RESTful path.
    
    Handles patterns like:
        /api/transactions/order/22
        /transactions/purchase-order/detail/22
        /api/invoice/22
    
    Args:
        path: URL path
        
    Returns:
        Dict with 'model_name' and optional 'id'
        
    Examples:
        parse_restful_path('/api/transactions/order/22')
        -> {'model_name': 'order', 'id': 22}
        
        parse_restful_path('/transactions/purchase/detail/22')
        -> {'model_name': 'purchase', 'id': 22}
    """
    # Remove leading slash and split
    segments = [s for s in path.strip('/').split('/') if s]
    
    # Try to find an ID (numeric segment)
    id_value: Optional[int] = None
    numeric_indices = [i for i, s in enumerate(segments) if s.isdigit()]
    if numeric_indices:
        id_value = int(segments[numeric_indices[0]])
        segments = [s for i, s in enumerate(segments) if i not in numeric_indices]
    
    # Remove common prefixes
    filtered = [s for s in segments if s.lower() not in ('api', 'wcapi', 'detail', 'list', 'edit', 'new')]
    
    # Join remaining segments and resolve
    path_part = '/'.join(filtered)
    model_name = resolve_model_name(path_part) if path_part else ''
    
    result: Dict[str, Any] = {'model_name': model_name}
    if id_value is not None:
        result['id'] = id_value
    
    return result


def url_to_model_name(url_segment: str) -> str:
    """
    Convert a URL path segment to wcapi model_name format.
    Used for URL-based routing to API calls.
    
    Args:
        url_segment: URL segment like "order" or "purchase"
        
    Returns:
        wcapi model_name like "order" or "purchase"
    """
    return resolve_model_name(url_segment)


def model_name_to_url(model_name: str) -> str:
    """
    Convert a wcapi model_name to URL-friendly format.
    Used for building navigation URLs.
    
    Args:
        model_name: wcapi model_name like "order"
        
    Returns:
        URL segment like "order"
    """
    if model_name in URL_MAP:
        return URL_MAP[model_name]
    return model_name.replace('_', '-')


def get_transaction_type(model_name: str) -> str:
    """
    Get the transaction type for routing purposes from a model name.
    
    Args:
        model_name: wcapi model_name
        
    Returns:
        Transaction type for routing (e.g., "order", "invoice")
    """
    resolved = resolve_model_name(model_name)
    return TRANSACTION_TYPE_MAP.get(resolved, resolved)


def get_model_class(model_name: str):
    """
    Get the Django model class for a given model name.
    
    Args:
        model_name: Model name in any format
        
    Returns:
        Django model class or None if not found
    """
    resolved = resolve_model_name(model_name)
    
    # Try to find the model in registered apps
    for app_config in apps.get_app_configs():
        try:
            # Try various name formats
            for name in [resolved, resolved.replace('_', ''), resolved.title().replace('_', '')]:
                try:
                    return app_config.get_model(name)
                except LookupError:
                    continue
        except Exception:
            continue
    
    return None


def validate_model_name(model_name: str) -> bool:
    """
    Check if a model name is valid (exists in the mapping or Django models).
    
    Args:
        model_name: Model name to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        resolved = resolve_model_name(model_name, strict=True)
        return bool(resolved)
    except ValueError:
        # Check if it's a valid Django model
        return get_model_class(model_name) is not None
