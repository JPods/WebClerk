#i Central registry foro Universal API accessiblen models.
# Limits exposure surface and provides a single whitelist for query/save endpoints.
from apps.accounts.models import (
    Currency, ExchangeRate, Exchange, GlAccount,
    GLJournal, Ledger, TaxJurisdiction, Term
)
from apps.core.models import Contact, Action, Setting, Template, Pending, Notifications, Report
from apps.communications.models import Phone, Domain, Email, Location
from apps.orgs.models import (
    OrgBase, Customer, Vendor, Rep, Employee, Manufacturer,
)  #QQQ
from apps.docs.models import Document, Linkage, QuestionAnswer, Tag
from apps.products.models import (
    Item, OrgItem, ItemXRef, Serial, SerialLog,
    Service, Specification, Variant, Warehouse,
    Usage, InventoryLayer,  #InventoryReservation,
    #Flow, DeliveryVisit, DeliveryLine,
    BillOfMaterial, Catalog,
)
# Initially scoped to invoices only; expanded to include work orders and sales orders.
from apps.transactions.models import (
    Invoice, InvoiceLine,
    WorkOrder, WorkOrderLine,
    SalesOrder, SalesOrderLine,
    PurchaseOrder, PurchaseOrderLine,
    Proposal, ProposalLine,
)

MODEL_MAP = {
    # account
    'currencies': Currency,
    'exchange_rates': ExchangeRate, 
    'exchanges': Exchange, 
    'gl_accounts': GlAccount, 
    'gl_journals': GLJournal,
    'ledgers': Ledger,
    'tax_jurisdictions': TaxJurisdiction,
    'terms': Term,

    # core
    'actions': Action,
    'contacts': Contact,
    'notifications': Notifications,
    'pendings': Pending,
    'reports': Report,
    'settings': Setting,
    'templates': Template,

    # communications
    'domains': Domain,
    'emails': Email,
    'locations': Location,
    'phones': Phone,

    # docs
    'documents': Document,
    'likages': Linkage,
    'qas': QuestionAnswer,
    'tags': Tag,

    # organization entity
    'customers': Customer,
    'vendors': Vendor,
    'reps': Rep,
    'employees': Employee,
    'manufacturers': Manufacturer,

    # products / inventory
    'boms': BillOfMaterial,  
    'catalogs': Catalog,
    # 'flows': Flow, DeliveryVisit, DeliveryLine
    'inventory_layers': InventoryLayer,
    'item_xrefs': ItemReference,
    'items': Item,
    'org_items': OrgItem,
    'serials': Serial,
    'serial_logs': SerialLog,
    'services': Service,
    'specifications': Specification,
    'usages': Usage,
    'variants': Variant,
    'warehouses': Warehouse,
    #'inventory_reservations': InventoryReservation,

    # support
    'campaigns': Campaign,

    # sync
    'connections': Connection,
    'bundles': Bundle,

    # transactional documents
    'invoices': Invoice,
    'invoice_lines': InvoiceLine,
    'work_orders': WorkOrder,
    'work_order_lines': WorkOrderLine,
    'purchase_orders': PurchaseOrder,
    'purchase_order_lines': PurchaseOrderLine,
    'sales_orders': SalesOrder,
    'sales_order_lines': SalesOrderLine,
    'proposals': Proposal,
    'proposal_lines': ProposalLine,
    #'projects': Project,
    #'project_lines': ProjectLine,
    #'requisitions': Requisition,
    #'requisition_lines': RequisitionLine,
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
    'pending': 'pendings',
    'phone': 'phones',
    'domain': 'domains',
    'email': 'emails',
    'location': 'locations',
    'address': 'locations',  # force to locations
    'item': 'items',
    'org_item': 'org_items',  # accept org_item as canonical alias
    'sales_order': 'sales_orders',
    'sales_order_line': 'sales_order_lines',
    'invoice': 'invoices',
    'invoice_line': 'invoice_lines',
    'proposal': 'proposals',
    'work_order': 'work_orders',
    'work_order_line': 'work_order_lines',
    'purchase_order': 'purchase_orders',
    'purchase_order_line': 'purchase_order_lines',
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
    'pendings': 'pending',
    'phones': 'phone',
    'domains': 'domain',
    'emails': 'email',
    'locations': 'location',
    'addresses': 'location',
    'items': 'item',
    'org_items': 'org_item',
    # transactional headers/lines (cover both explicit db_table names and defaults)
    'sales_orders': 'sales_order',
    'sales_order_lines': 'sales_order_line',
    'invoices': 'invoice',
    'invoice_lines': 'invoice_line',
    'purchase_orders': 'purchase_order',
    'purchase_order_lines': 'purchase_order_line',
    'work_orders': 'work_order',
    'work_order_lines': 'work_order_line',
    'proposals': 'proposal',
    'proposal_lines': 'proposal_line',
    'requisitions': 'requisition',
    'requisition_lines': 'requisition_line',
    # Default Django table names for headers without explicit db_table
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
