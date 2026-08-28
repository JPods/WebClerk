"""Canonical model registry keyed by singular model_name.

Single source of truth for all model-name resolution in WC3.
Replaces the former model_name_resolver.py and dashboard_counts local registry.

Each entry describes:
 - model: dotted path to Django model class
 - human labels: singular/plural
 - endpoint: primary REST collection slug (kebab)
 - kind: semantic grouping (header | line | support | generic)
 - aliases: optional list of legacy keys or equivalents (plural keys, legacy table names)

Resolvers accept:
 - canonical key (singular snake, e.g., 'order_line')
 - legacy alias (e.g., 'order_lines', 'projects')
 - endpoint slug (e.g., 'order-lines')
 - simple plural/singular variants (append/remove a single trailing 's')
 - hyphen/underscore variants are normalized where applicable
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelMeta:
    key: str  # canonical singular key (snake_case)
    model: str  # dotted path to Django model class
    singular: str
    plural: str
    endpoint: str  # kebab-case collection slug
    kind: str = "generic"
    aliases: List[str] = field(default_factory=list)

    def import_model(self):  # lazy importer to avoid cycles
        module_path, cls_name = self.model.rsplit('.', 1)
        module = __import__(module_path, fromlist=[cls_name])
        return getattr(module, cls_name)


# Canonical registry (keyed by singular code)
MODEL_REGISTRY: Dict[str, ModelMeta] = {
    # --- accounts --- (A->Z by key)
    'audit': ModelMeta('audit', 'apps.accounts.models.audit.Audit', 'Audit', 'Audits', 'audits', kind='support', aliases=['audits']),
    'currency': ModelMeta('currency', 'apps.accounts.models.currency.Currency', 'Currency', 'Currencies', 'currencies', kind='support', aliases=['currencies']),
    'gl_account': ModelMeta('gl_account', 'apps.accounts.models.gl_account.GlAccount', 'GL Account', 'GL Accounts', 'gl-accounts', kind='support', aliases=['gl_accounts']),
    'gl_journal': ModelMeta('gl_journal', 'apps.accounts.models.gl_journal.GlJournal', 'GL Journal', 'GL Journals', 'gl-journals', kind='support', aliases=['gl_journals']),
    'journal_batch': ModelMeta('journal_batch', 'apps.accounts.models.journal_batch.JournalBatch', 'Journal Batch', 'Journal Batches', 'journal-batches', kind='support', aliases=['journal_batches']),
    'ledger': ModelMeta('ledger', 'apps.accounts.models.ledger.Ledger', 'Ledger', 'Ledgers', 'ledgers', kind='support', aliases=['ledgers']),
    'tax_jurisdiction': ModelMeta('tax_jurisdiction', 'apps.accounts.models.tax_jurisdiction.TaxJurisdiction', 'Tax Jurisdiction', 'Tax Jurisdictions', 'tax-jurisdictions', kind='support', aliases=['tax_jurisdictions']),
    'term': ModelMeta('term', 'apps.accounts.models.term.Term', 'Term', 'Terms', 'terms', kind='support', aliases=['terms']),

    # --- communications --- (A->Z by key)
    'domain': ModelMeta('domain', 'apps.communications.models.domain.Domain', 'Domain', 'Domains', 'domains', kind='support', aliases=['domains']),
    'email': ModelMeta('email', 'apps.communications.models.email.Email', 'Email', 'Emails', 'emails', kind='support', aliases=['emails']),
    'address': ModelMeta('address', 'apps.communications.models.address.Address', 'Address', 'Addresses', 'addresses', kind='support', aliases=['addresses']),
    'phone': ModelMeta('phone', 'apps.communications.models.phone.Phone', 'Phone', 'Phones', 'phones', kind='support', aliases=['phones']),
    'touch': ModelMeta('touch', 'apps.communications.models.touch.Touch', 'Touch', 'Touches', 'touches', kind='support', aliases=['touches']),

    # --- orgs --- (A->Z by key)
    'customer': ModelMeta('customer', 'apps.orgs.models.Customer', 'Customer', 'Customers', 'customers', kind='support', aliases=['customers']),
    'employee': ModelMeta('employee', 'apps.orgs.models.Employee', 'Employee', 'Employees', 'employees', kind='support', aliases=['employees']),
    'manufacturer': ModelMeta('manufacturer', 'apps.orgs.models.Manufacturer', 'Manufacturer', 'Manufacturers', 'manufacturers', kind='support', aliases=['manufacturers']),
    'rep': ModelMeta('rep', 'apps.orgs.models.Rep', 'Rep', 'Reps', 'reps', kind='support', aliases=['reps']),
    'other_org': ModelMeta('other_org', 'apps.orgs.models.Other', 'Other Org', 'Other Orgs', 'other-orgs', kind='support', aliases=['other_orgs', 'other']),
    'vendor': ModelMeta('vendor', 'apps.orgs.models.Vendor', 'Vendor', 'Vendors', 'vendors', kind='support', aliases=['vendors']),

    # --- core --- (A->Z by key)
    'action': ModelMeta('action', 'apps.core.models.action.Action', 'Action', 'Actions', 'actions', kind='support', aliases=['actions']),
    'contact': ModelMeta('contact', 'apps.core.models.contact.Contact', 'Contact', 'Contacts', 'contacts', kind='support', aliases=['contacts']),
    'document': ModelMeta('document', 'apps.docs.models.document.Document', 'Document', 'Documents', 'documents', kind='support', aliases=['documents', 'doc']),
    'notification': ModelMeta('notification', 'apps.core.models.notification.Notification', 'Notification', 'Notifications', 'notifications', kind='support', aliases=['notifications']),
    'report': ModelMeta('report', 'apps.core.models.report.Report', 'Report', 'Reports', 'reports', kind='support', aliases=['reports']),
    'setting': ModelMeta('setting', 'apps.core.models.setting.Setting', 'Setting', 'Settings', 'settings', kind='support', aliases=['settings']),
    # Virtual namespaces — no model class, used as parent_model for system-level Settings
    'wc': ModelMeta('wc', 'apps.core.models.setting.Setting', 'WebClerk System', 'WebClerk System', 'wc', kind='support', aliases=['webclerk', 'system']),
    'gantt': ModelMeta('gantt', 'apps.core.models.setting.Setting', 'Gantt', 'Gantt', 'gantt', kind='support', aliases=[]),
    'databrowser': ModelMeta('databrowser', 'apps.core.models.setting.Setting', 'DataBrowser', 'DataBrowser', 'databrowser', kind='support', aliases=['db']),
    # 'template': ModelMeta('template', 'apps.core.models.template.Template', 'Template', 'Templates', 'templates', kind='support', aliases=['templates']),  # model not yet created
    'workspace': ModelMeta('workspace', 'apps.core.models.workspace.Workspace', 'Workspace', 'Workspaces', 'workspaces', kind='support', aliases=['workspaces']),

    # --- docs --- (A->Z by key)
    # 'doc' resolved via alias on 'document' entry above — no separate registry entry needed
    'linkage': ModelMeta('linkage', 'apps.docs.models.linkage_entry.LinkageEntry', 'Doc Linkage', 'Doc Linkages', 'doc-linkages', kind='support', aliases=['linkages', 'linkage_entry']),
    'question_answer': ModelMeta('question_answer', 'apps.docs.models.question_answer.QuestionAnswer', 'Doc QuestionAnswer', 'Doc QAs', 'doc-qas', kind='support', aliases=['question_answer']),
    'tag': ModelMeta('tag', 'apps.docs.models.tag.Tag', 'Doc Tag', 'Doc Tags', 'doc-tags', kind='support', aliases=['tags']),

    # --- products --- (A->Z by key)
    'item': ModelMeta('item', 'apps.products.models.item.Item', 'Item', 'Items', 'items', kind='support', aliases=['items', 'product']),
    'bill_of_material': ModelMeta('bill_of_material', 'apps.products.models.bill_of_material.BillOfMaterial', 'Bill Of Material', 'Bill Of Materials', 'bills-of-material', kind='support', aliases=['bill_of_materials', 'bill_of_material']),
    'catalog': ModelMeta('catalog', 'apps.products.models.catalog.Catalog', 'Catalog', 'Catalogs', 'catalogs', kind='support', aliases=['catalogs']),
    'delivery_line': ModelMeta('delivery_line', 'apps.products.models.flow.DeliveryLine', 'Delivery Line', 'Delivery Lines', 'delivery-lines', kind='support', aliases=['delivery_lines']),
    'delivery_visit': ModelMeta('delivery_visit', 'apps.products.models.flow.DeliveryVisit', 'Delivery Visit', 'Delivery Visits', 'delivery-visits', kind='support', aliases=['delivery_visits']),
    'inventory_adjustment_run': ModelMeta('inventory_adjustment_run', 'apps.products.models.processor_runs.InventoryAdjustmentProcessorRun', 'Inventory Adjustment Run', 'Inventory Adjustment Runs', 'inventory-adjustment-runs', kind='support', aliases=['inventory_adjustment_runs']),
    'inventory_check': ModelMeta('inventory_check', 'apps.products.models.inventory_check.InventoryCheck', 'Inventory Check', 'Inventory Checks', 'inventory-checks', kind='support', aliases=['inventory_checks']),
    'inventory_check_line': ModelMeta('inventory_check_line', 'apps.products.models.inventory_check.InventoryCheckLine', 'Inventory Check Line', 'Inventory Check Lines', 'inventory-check-lines', kind='support', aliases=['inventory_check_lines']),
    'inventory_layer': ModelMeta('inventory_layer', 'apps.products.models.inventory_layer.InventoryLayer', 'Inventory Layer', 'Inventory Layers', 'inventory-layers', kind='support', aliases=['inventory_layers']),
    'inventory_metrics_snapshot': ModelMeta('inventory_metrics_snapshot', 'apps.products.models.metrics.InventoryMetricsSnapshot', 'Inventory Metrics Snapshot', 'Inventory Metrics Snapshots', 'inventory-metrics-snapshots', kind='support', aliases=['inventory_metrics_snapshots']),
    'inventory_reservation': ModelMeta('inventory_reservation', 'apps.products.models.inventory_reservation.InventoryReservation', 'Inventory Reservation', 'Inventory Reservations', 'inventory-reservations', kind='support', aliases=['inventory_reservations']),
    'item_usage': ModelMeta('item_usage', 'apps.products.models.ItemUsage', 'Item Usage', 'Item Usages', 'item-usages', kind='support', aliases=['item_usages']),
    'item_xref': ModelMeta('item_xref', 'apps.products.models.ItemXRef', 'Item XRef', 'Item XRefs', 'item-xrefs', kind='support', aliases=['item_xrefs']),
    'org_item': ModelMeta('org_item', 'apps.products.models.org_item.OrgItem', 'Org Item', 'Org Items', 'org-items', kind='support', aliases=['org_items']),
    'serial': ModelMeta('serial', 'apps.products.models.serial.Serial', 'Serial', 'Serials', 'serials', kind='support', aliases=['serials']),
    'serial_log': ModelMeta('serial_log', 'apps.products.models.serial.SerialLog', 'Serial Log', 'Serial Logs', 'serial-logs', kind='support', aliases=['serial_logs']),
    'variant': ModelMeta('variant', 'apps.products.models.Variant', 'Variant', 'Variants', 'variants', kind='support', aliases=['variants']),
    'warehouse': ModelMeta('warehouse', 'apps.products.models.warehouse.Warehouse', 'Warehouse', 'Warehouses', 'warehouses', kind='support', aliases=['warehouses']),

    # --- sync --- (A->Z by key)
    'connection': ModelMeta('connection', 'apps.sync.models.connection.Connection', 'Connection', 'Connections', 'connections', kind='support', aliases=['connections']),
    'bundle': ModelMeta('sync_bundle', 'apps.sync.models.bundle.Bundle', 'Sync Bundle', 'Sync Bundles', 'sync-bundles', kind='support', aliases=['bundles_sync']),

    # --- transactions --- (A->Z by key)
    'invoice': ModelMeta('invoice', 'apps.transactions.models.Invoice', 'Invoice', 'Invoices', 'invoices', kind='header', aliases=['invoices']),
    'invoice_line': ModelMeta('invoice_line', 'apps.transactions.models.InvoiceLine', 'Invoice Line', 'Invoice Lines', 'invoice-lines', kind='line', aliases=['invoice_lines']),
    'project': ModelMeta('project', 'apps.transactions.models.project.Project', 'Project', 'Projects', 'projects', kind='support', aliases=['projects']),
    'project_association': ModelMeta('project_association', 'apps.transactions.models.project_links.ProjectAssociation', 'Project Association', 'Project Associations', 'project-associations', kind='support', aliases=['project_associations']),
    'proposal': ModelMeta('proposal', 'apps.transactions.models.Proposal', 'Proposal', 'Proposals', 'proposals', kind='header', aliases=['proposals', 'quote']),
    'proposal_line': ModelMeta('proposal_line', 'apps.transactions.models.ProposalLine', 'Proposal Line', 'Proposal Lines', 'proposal-lines', kind='line', aliases=['proposal_lines', 'quoteline']),
    'purchase': ModelMeta('purchase', 'apps.transactions.models.Purchase', 'Purchase', 'Purchases', 'purchases', kind='header', aliases=['purchases', 'po']),
    'purchase_line': ModelMeta('purchase_line', 'apps.transactions.models.PurchaseLine', 'Purchase Line', 'Purchase Lines', 'purchase-lines', kind='line', aliases=['purchase_lines', 'poline']),
    # 'purchase_receipt': ModelMeta('purchase_receipt', 'apps.transactions.models.purchase_receipt.PurchaseReceipt', 'Purchase Receipt', 'Purchase Receipts', 'purchase-receipts', kind='support', aliases=['purchase_receipts']),  # model not yet created
    'requisition': ModelMeta(
        'requisition',
        'apps.transactions.models.Requisition',
        'Requisition',
        'Requisitions',
        'requisitions',
        kind='header',
        aliases=['requisitions', 'req']
    ),
    'requisition_line': ModelMeta(
        'requisition_line',
        'apps.transactions.models.RequisitionLine',
        'Requisition Line',
        'Requisition Lines',
        'requisition-lines',
        kind='line',
        aliases=['requisition_lines', 'requisition-line', 'requisition-lines', 'reqline']
    ),
    'pending_payment_application': ModelMeta('pending_payment_application', 'apps.transactions.models.pending_payment.PendingPaymentApplication', 'Pending Payment Application', 'Pending Payment Applications', 'pending-payment-applications', kind='support', aliases=['pending_payment_applications']),
    # Alice
    'alice_observation': ModelMeta('alice_observation', 'apps.ai_assistant.models.alice.AliceObservation', 'Alice Observation', 'Alice Observations', 'alice-observations', kind='support', aliases=['alice_observations']),
    'alice_preset': ModelMeta('alice_preset', 'apps.ai_assistant.models.alice.AlicePreset', 'Alice Preset', 'Alice Presets', 'alice-presets', kind='support', aliases=['alice_presets']),
    'alice_coaching_log': ModelMeta('alice_coaching_log', 'apps.ai_assistant.models.alice.AliceCoachingLog', 'Alice Coaching Log', 'Alice Coaching Logs', 'alice-coaching-logs', kind='support', aliases=['alice_coaching_logs']),
    'order': ModelMeta('order', 'apps.transactions.models.Order', 'Order', 'Orders', 'orders', kind='header', aliases=['orders']),
    'order_line': ModelMeta('order_line', 'apps.transactions.models.OrderLine', 'Order Line', 'Order Lines', 'order-lines', kind='line', aliases=['order_lines']),
    'workorder': ModelMeta('workorder', 'apps.transactions.models.WorkOrder', 'Work Order', 'Work Orders', 'workorders', kind='header', aliases=['workorders', 'wo', 'work']),
    'workorder_line': ModelMeta('workorder_line', 'apps.transactions.models.WorkOrderLine', 'Work Order Line', 'Work Order Lines', 'workorder-lines', kind='line', aliases=['workorder_lines', 'woline']),
    'payment': ModelMeta('payment', 'apps.transactions.models.Payment', 'Payment', 'Payments', 'payments', kind='header', aliases=['payments']),
    'statement_line': ModelMeta('statement_line', 'apps.transactions.models.StatementLine', 'Statement Line', 'Statement Lines', 'statement-lines', kind='header', aliases=['statement_lines', 'statements']),
    'payment_application': ModelMeta('payment_application', 'apps.transactions.models.PaymentApplication', 'Payment Application', 'Payment Applications', 'payment-applications', kind='support', aliases=['payment_applications']),
    'payment_method': ModelMeta('payment_method', 'apps.transactions.models.PaymentMethod', 'Payment Method', 'Payment Methods', 'payment-methods', kind='support', aliases=['payment_methods']),
    'payment_term': ModelMeta('payment_term', 'apps.transactions.models.PaymentTerm', 'Payment Term', 'Payment Terms', 'payment-terms', kind='support', aliases=['payment_terms']),
    'receipt': ModelMeta('receipt', 'apps.transactions.models.Receipt', 'Receipt', 'Receipts', 'receipts', kind='header', aliases=['receipts']),
    'receipt_line': ModelMeta('receipt_line', 'apps.transactions.models.ReceiptLine', 'Receipt Line', 'Receipt Lines', 'receipt-lines', kind='line', aliases=['receipt_lines']),
}


# --- Normalization & resolution (consolidation) ---

def _normalize_token(token: str) -> str:
    """Normalize a user-supplied token to canonical snake_case."""
    if not token:
        return ''
    s = token.strip()
    # Insert underscore between lower/digit and upper (CamelCase -> snake_case)
    s = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', s)
    s = s.lower()
    # Replace any run of non-alphanumerics with single underscore
    s = re.sub(r'[^a-z0-9]+', '_', s)
    # Collapse duplicates, trim edges
    s = re.sub(r'_+', '_', s).strip('_')
    return s


# Build indexes once
_ENDPOINT_INDEX: Dict[str, str] = {}
_ALIAS_INDEX: Dict[str, str] = {}

for key, meta in MODEL_REGISTRY.items():
    # Canonical key
    _ALIAS_INDEX[_normalize_token(key)] = key
    # Endpoint
    _ENDPOINT_INDEX[_normalize_token(meta.endpoint)] = key
    # Provided aliases
    for a in meta.aliases:
        _ALIAS_INDEX[_normalize_token(a)] = key
    # Human labels
    _ALIAS_INDEX[_normalize_token(meta.singular)] = key
    _ALIAS_INDEX[_normalize_token(meta.plural)] = key
    # Simple plural of canonical (best-effort)
    if not key.endswith('s'):
        _ALIAS_INDEX[_normalize_token(f'{key}s')] = key


def get_model_meta(name: str) -> Optional[ModelMeta]:
    """Resolve by canonical key, alias, endpoint, or simple plural."""
    if not name:
        return None
    norm = _normalize_token(name)
    if norm in MODEL_REGISTRY:
        return MODEL_REGISTRY[norm]
    if norm in _ENDPOINT_INDEX:
        return MODEL_REGISTRY[_ENDPOINT_INDEX[norm]]
    if norm in _ALIAS_INDEX:
        return MODEL_REGISTRY[_ALIAS_INDEX[norm]]
    if norm.endswith('s'):
        base = norm[:-1]
        if base in MODEL_REGISTRY:
            return MODEL_REGISTRY[base]
        if base in _ALIAS_INDEX:
            return MODEL_REGISTRY[_ALIAS_INDEX[base]]
    return None


def get_model_meta_by_endpoint(endpoint: str) -> Optional[ModelMeta]:
    key = _ENDPOINT_INDEX.get(_normalize_token(endpoint))
    return MODEL_REGISTRY.get(key) if key else None


def import_model(name: str):
    """Import a Django model class from any accepted variant."""
    meta = get_model_meta(name)
    return meta.import_model() if meta else None


VALID_MODEL_NAMES: List[str] = list(MODEL_REGISTRY.keys())

# --- Transaction type subset (for routing) ---
TRANSACTION_TYPES = frozenset({
    'order', 'invoice', 'purchase', 'proposal', 'workorder', 'requisition',
})


# --- Functions formerly in model_name_resolver.py ---

def resolve_model_name(input_str: str, strict: bool = False) -> str:
    """Resolve any name variant to canonical model_registry key.

    Wrapper around get_model_meta that returns the key string
    (or the normalized input as fallback when strict=False).
    """
    if not input_str:
        raise ValueError('Model name is required')
    meta = get_model_meta(input_str)
    if meta:
        return meta.key
    if strict:
        raise ValueError(f'Unknown model name: {input_str}')
    norm = _normalize_token(input_str)
    logger.warning(f'[resolve_model_name] Unknown model "{input_str}", using normalized: "{norm}"')
    return norm


def get_model_class(model_name: str):
    """Return the Django model class for *model_name*, or None."""
    return import_model(model_name)


def model_name_to_url(model_name: str) -> str:
    """Convert a canonical key to its kebab-case endpoint slug."""
    meta = get_model_meta(model_name)
    if meta:
        return meta.endpoint
    return model_name.replace('_', '-')


def get_transaction_type(model_name: str) -> str:
    """Return the base transaction type for routing, or the resolved name."""
    resolved = resolve_model_name(model_name)
    # Strip _line suffix to get header type
    base = resolved.replace('_line', '')
    return base if base in TRANSACTION_TYPES else resolved


def parse_restful_path(path: str) -> Dict[str, Any]:
    """Extract model_name and optional id from a RESTful URL path.

    Handles patterns like:
        /api/transactions/order/22
        /transactions/purchase/detail/22
        /api/invoice/22
    """
    segments = [s for s in path.strip('/').split('/') if s]

    # Extract numeric segment as id
    id_value: Optional[int] = None
    numeric_indices = [i for i, s in enumerate(segments) if s.isdigit()]
    if numeric_indices:
        id_value = int(segments[numeric_indices[0]])
        segments = [s for i, s in enumerate(segments) if i not in numeric_indices]

    # Remove common URL noise
    filtered = [s for s in segments if s.lower() not in ('api', 'wcapi', 'detail', 'list', 'edit', 'new')]

    path_part = '/'.join(filtered)
    model_name = resolve_model_name(path_part) if path_part else ''

    result: Dict[str, Any] = {'model_name': model_name}
    if id_value is not None:
        result['id'] = id_value
    return result


def validate_model_name(model_name: str) -> bool:
    """Return True if *model_name* resolves to a known registry entry."""
    try:
        resolve_model_name(model_name, strict=True)
        return True
    except ValueError:
        return False


# --- Compatibility layer (formerly in wcapi_registry.py) ---

def get_model(model_key: str):
    """Resolve a model class from a slug, canonical key, alias, or dotpath.

    Tries the static MODEL_REGISTRY first, then falls back to scanning
    Django's installed models for names not in the registry.
    """
    if not model_key:
        return None
    # 1) Try the static registry
    cls = import_model(model_key)
    if cls is not None:
        return cls
    # 2) Fallback: scan Django installed models by model_name
    from django.apps import apps as django_apps
    norm = _normalize_token(model_key)
    for m in django_apps.get_models():
        if m._meta.model_name == norm:
            return m
    # 3) Singularize and retry
    singular = norm
    if singular.endswith('ies'):
        singular = singular[:-3] + 'y'
    elif singular.endswith('ses'):
        singular = singular[:-2]
    elif singular.endswith('s'):
        singular = singular[:-1]
    if singular != norm:
        for m in django_apps.get_models():
            if m._meta.model_name == singular:
                return m
    # 4) Dotpath "app_label.ModelName"
    if '.' in model_key:
        try:
            return django_apps.get_model(*model_key.rsplit('.', 1))
        except Exception:
            pass
    return None


def to_model_name(model_cls) -> Optional[str]:
    """Return the Django model_name for a model class."""
    try:
        return model_cls._meta.model_name
    except Exception:
        return None


def normalize_table_key(k: str) -> str:
    """Normalize a table key (strip, lowercase, remove slashes)."""
    return (k or '').strip().strip('/').lower()


def _discover_allowed_keys():
    from django.apps import apps as django_apps
    keys = set()
    for m in django_apps.get_models():
        mn = m._meta.model_name
        keys.add(mn)
        if not mn.endswith('s'):
            if mn.endswith('y'):
                keys.add(mn[:-1] + 'ies')
            else:
                keys.add(mn + 's')
    return sorted(keys)


# Lazy — only computed when accessed
_allowed_table_keys = None


def get_allowed_table_keys():
    global _allowed_table_keys
    if _allowed_table_keys is None:
        _allowed_table_keys = _discover_allowed_keys()
    return _allowed_table_keys


# Re-export helpers
__all__ = [
    'ModelMeta', 'MODEL_REGISTRY',
    'get_model_meta', 'get_model_meta_by_endpoint', 'import_model',
    'get_model_class', 'resolve_model_name', 'model_name_to_url',
    'get_transaction_type', 'parse_restful_path', 'validate_model_name',
    'VALID_MODEL_NAMES', 'TRANSACTION_TYPES',
    'get_model', 'to_model_name', 'normalize_table_key',
    'get_allowed_table_keys',
]
