"""Transaction-specific serializer behaviors.

Delegates universal behaviors (contact, org, status) to core/serializers/behaviors.py.
Adds transaction-specific field lists and any transaction-only validation.

Usage in transaction serializers:
    from apps.transactions.serializers.behaviors import (
        validate_customer_id, validate_vendor_id,
        validate_customer_vendor_different, validate_status_transition,
    )
"""

# Re-export universal behaviors so transaction serializers import from one place
from apps.core.serializers.behaviors import (  # noqa: F401
    validate_customer_id,
    validate_vendor_id,
    validate_manufacturer_id,
    validate_customer_vendor_different,
    validate_status_transition,
    validate_contact_id,
    validate_project_id,
    name_from_refs,
)


# Base fields that every transaction header serializer should expose
TRANSACTION_HEADER_FIELDS = [
    'id', 'uuid', 'ida', 'status', 'attention', 'priority',
    'dt_created', 'dt_modified', 'dt_needed',
    'customer_id', 'vendor_id', 'manufacturer_id',
    'ship_via', 'is_active',
    'totals', 'finance', 'shipping', 'commission',
    'metadata', 'refs', 'prefs', 'config', 'comments',
    'health_rating',
]

TRANSACTION_HEADER_READ_ONLY = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'totals',
    'health_rating',
]
