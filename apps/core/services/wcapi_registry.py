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

ALLOWED_TABLE_NAMES = set(MODEL_MAP.keys())

def get_model(table_name: str):
    if not table_name:
        return None
    return MODEL_MAP.get(table_name.lower())
