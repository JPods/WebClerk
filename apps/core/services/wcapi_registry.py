# Central registry for Universal API accessible models.
# Limits exposure surface and provides a single whitelist for query/save endpoints.
from apps.core.models import Contact, Action
from apps.communications.models import Phone, Domain, Email, Location
from apps.orgs.models import (
    OrgBase, CustomerOrg, VendorOrg, RepOrg, EmployeeOrg, ManufacturerOrg,
)
from apps.products.models import Item
from apps.transactions.models.line_variants import Order, OrderLine

MODEL_MAP = {
    'contacts': Contact,
    'actions': Action,
    'phones': Phone,
    'domains': Domain,
    'emails': Email,
    'addresses': Location,
    # products
    'items': Item,
    # transactional documents (initial subset; add more as exposed)
    'orders': Order,
    'orderlines': OrderLine,
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
