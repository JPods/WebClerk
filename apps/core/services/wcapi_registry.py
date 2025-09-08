# Central registry for Universal API accessible models.
# Limits exposure surface and provides a single whitelist for query/save endpoints.
from apps.core.models import Contact, Action, Setting, Template, Pending
from apps.communications.models import Phone, Domain, Email, Location
from apps.orgs.models import (
    OrgBase, CustomerOrg, VendorOrg, RepOrg, EmployeeOrg, ManufacturerOrg,
)
from apps.products.models import Item
from apps.transactions.models.line_variants import SalesOrder, SalesOrderLine

MODEL_MAP = {
    'contacts': Contact,
    'actions': Action,
    'settings': Setting,
    'templates': Template,
    'pending': Pending,
    'phones': Phone,
    'domains': Domain,
    'emails': Email,
    'locations': Location,
    'addresses': Location,  # alias for backward compatibility
    # products
    'items': Item,
    # transactional documents (initial subset; add more as exposed)
    'sales_orders': SalesOrder,
    'sales_order_lines': SalesOrderLine,
    # Unified organization entity + proxy filtered types
    'orgs': OrgBase,
    'customers': CustomerOrg,
    'vendors': VendorOrg,
    'reps': RepOrg,
    'employees': EmployeeOrg,
    'manufacturers': ManufacturerOrg,
}

ALLOWED_TABLE_KEYS = set(MODEL_MAP.keys())

"""
Helpers for mapping between table keys and model_name.
normalize_table_key accepts either a plural registry key ("table key") or a singular model_name and
returns the canonical table key used by the registry. to_model_name returns the
singular form for responses and logs.
"""

# Explicit singular->plural aliases for exposed models
_SINGULAR_ALIAS_TO_TABLE = {
    'contact': 'contacts',
    'action': 'actions',
    'setting': 'settings',
    'template': 'templates',
    'pending': 'pending',
    'phone': 'phones',
    'domain': 'domains',
    'email': 'emails',
    'location': 'locations',
    'address': 'locations',  # force to locations
    'item': 'items',
    'sales_order': 'sales_orders',
    'sales_order_line': 'sales_order_lines',
    'org': 'orgs',
    'customer': 'customers',
    'vendor': 'vendors',
    'rep': 'reps',
    'employee': 'employees',
    'manufacturer': 'manufacturers',
}

# Canonical reverse: table key -> singular model_name
_TABLE_TO_MODEL_NAME = {
    'contacts': 'contact',
    'actions': 'action',
    'settings': 'setting',
    'templates': 'template',
    'pending': 'pending',
    'phones': 'phone',
    'domains': 'domain',
    'emails': 'email',
    'locations': 'location',
    'addresses': 'location',
    'items': 'item',
    # transactional headers/lines (cover both explicit db_table names and defaults)
    'sales_orders': 'sales_order',
    'sales_order_lines': 'sales_order_line',
    'purchase_orders': 'purchase_order',
    'purchase_order_lines': 'purchase_order_line',
    'work_orders': 'work_order',
    'work_order_lines': 'work_order_line',
    'proposal_line': 'proposal_line',
    'invoice_line': 'invoice_line',
    'requisition_line': 'requisition_line',
    # Default Django table names for headers without explicit db_table
    'transactions_proposal': 'proposal',
    'transactions_invoice': 'invoice',
    'transactions_requisition': 'requisition',
    'orgs': 'org',
    'customers': 'customer',
    'vendors': 'vendor',
    'reps': 'rep',
    'employees': 'employee',
    'manufacturers': 'manufacturer',
}

def normalize_table_key(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    if key in MODEL_MAP:
        return key
    # Allow singular model_name inputs
    alias = _SINGULAR_ALIAS_TO_TABLE.get(key)
    if alias:
        return alias
    return None

def to_model_name(table_key: str | None) -> str | None:
    if not table_key:
        return None
    key = table_key.strip().lower()
    return _TABLE_TO_MODEL_NAME.get(key, key[:-1] if key.endswith('s') else key)

def get_model(table_key: str):
    if not table_key:
        return None
    key = normalize_table_key(table_key)
    if not key:
        return None
    return MODEL_MAP.get(key)
