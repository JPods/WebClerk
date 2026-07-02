"""Canonical model registry keyed by singular model_name.

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
from typing import Dict, List, Optional
import re


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
    'exchange_rate': ModelMeta('exchange_rate', 'apps.accounts.models.exchange_rate.ExchangeRate', 'Exchange Rate', 'Exchange Rates', 'exchange-rates', kind='support', aliases=['exchange_rates']),
    'exchange_transaction': ModelMeta('exchange_transaction', 'apps.accounts.models.exchange_transaction.ExchangeTransaction', 'Exchange Transaction', 'Exchange Transactions', 'exchange-transactions', kind='support', aliases=['exchange_transactions']),
    'gl_account': ModelMeta('gl_account', 'apps.accounts.models.gl_account.GlAccount', 'GL Account', 'GL Accounts', 'gl-accounts', kind='support', aliases=['gl_accounts']),
    'gl_journal': ModelMeta('gl_journal', 'apps.accounts.models.gl_journal.GlJournal', 'GL Journal', 'GL Journals', 'gl-journals', kind='support', aliases=['gl_journals']),
    'ledger': ModelMeta('ledger', 'apps.accounts.models.ledger.Ledger', 'Ledger', 'Ledgers', 'ledgers', kind='support', aliases=['ledgers']),
    'tax_jurisdiction': ModelMeta('tax_jurisdiction', 'apps.accounts.models.tax_jurisdiction.TaxJurisdiction', 'Tax Jurisdiction', 'Tax Jurisdictions', 'tax-jurisdictions', kind='support', aliases=['tax_jurisdictions']),
    'term': ModelMeta('term', 'apps.accounts.models.term.Term', 'Term', 'Terms', 'terms', kind='support', aliases=['terms']),

    # --- communications --- (A->Z by key)
    'domain': ModelMeta('domain', 'apps.communications.models.domain.Domain', 'Domain', 'Domains', 'domains', kind='support', aliases=['domains']),
    'email': ModelMeta('email', 'apps.communications.models.email.Email', 'Email', 'Emails', 'emails', kind='support', aliases=['emails']),
    'address': ModelMeta('address', 'apps.communications.models.address.Address', 'Address', 'Addresses', 'addresses', kind='support', aliases=['addresses']),
    'phone': ModelMeta('phone', 'apps.communications.models.phone.Phone', 'Phone', 'Phones', 'phones', kind='support', aliases=['phones']),

    # --- orgs --- (A->Z by key)
    'customer': ModelMeta('customer', 'apps.orgs.models.Customer', 'Customer', 'Customers', 'customers', kind='support', aliases=['customers']),
    'employee': ModelMeta('employee', 'apps.orgs.models.Employee', 'Employee', 'Employees', 'employees', kind='support', aliases=['employees']),
    'manufacturer': ModelMeta('manufacturer', 'apps.orgs.models.Manufacturer', 'Manufacturer', 'Manufacturers', 'manufacturers', kind='support', aliases=['manufacturers']),
    'rep': ModelMeta('rep', 'apps.orgs.models.Rep', 'Rep', 'Reps', 'reps', kind='support', aliases=['reps']),
    'vendor': ModelMeta('vendor', 'apps.orgs.models.Vendor', 'Vendor', 'Vendors', 'vendors', kind='support', aliases=['vendors']),

    # --- core --- (A->Z by key)
    'action': ModelMeta('action', 'apps.core.models.action.Action', 'Action', 'Actions', 'actions', kind='support', aliases=['actions']),
    'contact': ModelMeta('contact', 'apps.core.models.contact.Contact', 'Contact', 'Contacts', 'contacts', kind='support', aliases=['contacts']),
    'document': ModelMeta('document', 'apps.docs.models.document.Document', 'Document', 'Documents', 'documents', kind='support', aliases=['documents', 'doc']),
    'notification': ModelMeta('notification', 'apps.core.models.notification.Notification', 'Notification', 'Notifications', 'notifications', kind='support', aliases=['notifications']),
    'report': ModelMeta('report', 'apps.core.models.report.Report', 'Report', 'Reports', 'reports', kind='support', aliases=['reports']),
    'setting': ModelMeta('setting', 'apps.core.models.setting.Setting', 'Setting', 'Settings', 'settings', kind='support', aliases=['settings']),
    'template': ModelMeta('template', 'apps.core.models.template.Template', 'Template', 'Templates', 'templates', kind='support', aliases=['templates']),

    # --- docs --- (A->Z by key)
    'doc': ModelMeta('doc', 'apps.docs.models.document.Document', 'Document', 'Documents', 'docs', kind='support', aliases=['documents', 'document', 'docs']),
    'linkage': ModelMeta('linkage', 'apps.docs.models.linkage.Linkage', 'Doc Linkage', 'Doc Linkages', 'doc-linkages', kind='support', aliases=['linkages']),
    'question_answer': ModelMeta('question_answer', 'apps.docs.models.question_answer.QuestionAnswer', 'Doc QuestionAnswer', 'Doc QAs', 'doc-qas', kind='support', aliases=['question_answer']),
    'tag': ModelMeta('tag', 'apps.docs.models.tag.Tag', 'Doc Tag', 'Doc Tags', 'doc-tags', kind='support', aliases=['tags']),

    # --- products --- (A->Z by key)
    'item': ModelMeta('item', 'apps.products.models.item.Item', 'Item', 'Items', 'items', kind='support', aliases=['items']),
    'bill_of_material': ModelMeta('bill_of_material', 'apps.products.models.bill_of_material.BillOfMaterial', 'Bill Of Material', 'Bill Of Materials', 'bills-of-material', kind='support', aliases=['bill_of_materials', 'bill_of_material']),
    'catalog': ModelMeta('catalog', 'apps.products.models.catalog.Catalog', 'Catalog', 'Catalogs', 'catalogs', kind='support', aliases=['catalogs']),
    'delivery_line': ModelMeta('delivery_line', 'apps.products.models.flow.DeliveryLine', 'Delivery Line', 'Delivery Lines', 'delivery-lines', kind='support', aliases=['delivery_lines']),
    'delivery_visit': ModelMeta('delivery_visit', 'apps.products.models.flow.DeliveryVisit', 'Delivery Visit', 'Delivery Visits', 'delivery-visits', kind='support', aliases=['delivery_visits']),
    'inventory_adjustment_run': ModelMeta('inventory_adjustment_run', 'apps.products.models.processor_runs.InventoryAdjustmentProcessorRun', 'Inventory Adjustment Run', 'Inventory Adjustment Runs', 'inventory-adjustment-runs', kind='support', aliases=['inventory_adjustment_runs']),
    'inventory_check': ModelMeta('inventory_check', 'apps.products.models.inventory_check.InventoryCheck', 'Inventory Check', 'Inventory Checks', 'inventory-checks', kind='support', aliases=['inventory_checks']),
    'inventory_check_line': ModelMeta('inventory_check_line', 'apps.products.models.inventory_check.InventoryCheckLine', 'Inventory Check Line', 'Inventory Check Lines', 'inventory-check-lines', kind='support', aliases=['inventory_check_lines']),
    'inventory_metrics_snapshot': ModelMeta('inventory_metrics_snapshot', 'apps.products.models.metrics.InventoryMetricsSnapshot', 'Inventory Metrics Snapshot', 'Inventory Metrics Snapshots', 'inventory-metrics-snapshots', kind='support', aliases=['inventory_metrics_snapshots']),
    'inventory_reservation': ModelMeta('inventory_reservation', 'apps.products.models.inventory_reservation.InventoryReservation', 'Inventory Reservation', 'Inventory Reservations', 'inventory-reservations', kind='support', aliases=['inventory_reservations']),
    'item_usage': ModelMeta('item_usage', 'apps.products.models.ItemUsage', 'Item Usage', 'Item Usages', 'item-usages', kind='support', aliases=['item_usages']),
    'item_xref': ModelMeta('item_xref', 'apps.products.models.ItemXRef', 'Item XRef', 'Item XRefs', 'item-xrefs', kind='support', aliases=['item_xrefs']),
    'org_item': ModelMeta('org_item', 'apps.products.models.org_item.OrgItem', 'Org Item', 'Org Items', 'org-items', kind='support', aliases=['org_items']),
    'pending_inventory_adjustment': ModelMeta('pending_inventory_adjustment', 'apps.products.models.inventory_layer.PendingInventoryAdjustment', 'Pending Inventory Adjustment', 'Pending Inventory Adjustments', 'pending-inventory-adjustments', kind='support', aliases=['pending_inventory_adjustments']),
    'serial_log': ModelMeta('serial_log', 'apps.products.models.serial.SerialLog', 'Serial Log', 'Serial Logs', 'serial-logs', kind='support', aliases=['serial_logs']),
    'service': ModelMeta('service', 'apps.products.models.Service', 'Service', 'Services', 'services', kind='support', aliases=['services']),
    'variant': ModelMeta('variant', 'apps.products.models.Variant', 'Variant', 'Variants', 'variants', kind='support', aliases=['variants']),
    'warehouse': ModelMeta('warehouse', 'apps.products.models.warehouse.Warehouse', 'Warehouse', 'Warehouses', 'warehouses', kind='support', aliases=['warehouses']),

    # --- sync --- (A->Z by key)
    'connection': ModelMeta('connection', 'apps.sync.models.connection.Connection', 'Connection', 'Connections', 'connections', kind='support', aliases=['connections']),
    'bundle': ModelMeta('sync_bundle', 'apps.sync.models.bundle.Bundle', 'Sync Bundle', 'Sync Bundles', 'sync-bundles', kind='support', aliases=['bundles_sync']),

    # --- transactions --- (A->Z by key)
    'invoice': ModelMeta('invoice', 'apps.transactions.models.Invoice', 'Invoice', 'Invoices', 'invoices', kind='header', aliases=['invoices']),
    'invoice_line': ModelMeta('invoice_line', 'apps.transactions.models.InvoiceLine', 'Invoice Line', 'Invoice Lines', 'invoice-lines', kind='line', aliases=['invoice_lines']),
    'project': ModelMeta('project', 'apps.transactions.models.projects.Project', 'Project', 'Projects', 'projects', kind='support', aliases=['projects']),
    'project_association': ModelMeta('project_association', 'apps.transactions.models.project_links.ProjectAssociation', 'Project Association', 'Project Associations', 'project-associations', kind='support', aliases=['project_associations']),
    'proposal': ModelMeta('proposal', 'apps.transactions.models.Proposal', 'Proposal', 'Proposals', 'proposals', kind='header', aliases=['proposals']),
    'proposal_line': ModelMeta('proposal_line', 'apps.transactions.models.ProposalLine', 'Proposal Line', 'Proposal Lines', 'proposal-lines', kind='line', aliases=['proposal_lines']),
    'purchase': ModelMeta('purchase', 'apps.transactions.models.Purchase', 'Purchase', 'Purchases', 'purchases', kind='header', aliases=['purchases']),
    'purchase_line': ModelMeta('purchase_line', 'apps.transactions.models.PurchaseLine', 'Purchase Line', 'Purchase Lines', 'purchase-lines', kind='line', aliases=['purchase_lines']),
    'purchase_receipt': ModelMeta('purchase_receipt', 'apps.transactions.models.purchase_receipt.PurchaseReceipt', 'Purchase Receipt', 'Purchase Receipts', 'purchase-receipts', kind='support', aliases=['purchase_receipts']),
    'requisition': ModelMeta(
        'requisition',
        'apps.transactions.models.Requisition',
        'Requisition',
        'Requisitions',
        'requisitions',
        kind='header',
        aliases=['requisitions']  # TitleCase no longer needed; resolver normalizes it
    ),
    'requisition_line': ModelMeta(
        'requisition_line',
        'apps.transactions.models.RequisitionLine',
        'Requisition Line',
        'Requisition Lines',
        'requisition-lines',
        kind='line',
        aliases=['requisition_lines', 'requisition-line', 'requisition-lines']  # minimal; rest auto-derived
    ),
    'pending_payment_application': ModelMeta('pending_payment_application', 'apps.transactions.models.pending_payment.PendingPaymentApplication', 'Pending Payment Application', 'Pending Payment Applications', 'pending-payment-applications', kind='support', aliases=['pending_payment_applications']),
    # Alice
    'alice_observation': ModelMeta('alice_observation', 'apps.ai_assistant.models_alice.AliceObservation', 'Alice Observation', 'Alice Observations', 'alice-observations', kind='support', aliases=['alice_observations']),
    'alice_preset': ModelMeta('alice_preset', 'apps.ai_assistant.models_alice.AlicePreset', 'Alice Preset', 'Alice Presets', 'alice-presets', kind='support', aliases=['alice_presets']),
    'alice_coaching_log': ModelMeta('alice_coaching_log', 'apps.ai_assistant.models_alice.AliceCoachingLog', 'Alice Coaching Log', 'Alice Coaching Logs', 'alice-coaching-logs', kind='support', aliases=['alice_coaching_logs']),
    'order': ModelMeta('order', 'apps.transactions.models.Order', 'Order', 'Orders', 'orders', kind='header', aliases=['orders']),
    'order_line': ModelMeta('order_line', 'apps.transactions.models.OrderLine', 'Order Line', 'Order Lines', 'order-lines', kind='line', aliases=['order_lines']),
    'work_order': ModelMeta('work_order', 'apps.transactions.models.WorkOrder', 'Work Order', 'Work Orders', 'work-orders', kind='header', aliases=['work_orders']),
    'work_order_line': ModelMeta('work_order_line', 'apps.transactions.models.WorkOrderLine', 'Work Order Line', 'Work Order Lines', 'workorder-lines', kind='line', aliases=['work_order_lines']),
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

# Re-export helpers
__all__ = [
    'ModelMeta', 'MODEL_REGISTRY',
    'get_model_meta', 'get_model_meta_by_endpoint', 'import_model',
    'VALID_MODEL_NAMES',
]
