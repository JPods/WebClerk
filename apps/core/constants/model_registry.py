"""Canonical model registry keyed by singular model_name.

Each entry describes:
 - model: dotted path to Django model class
 - human labels: singular/plural
 - endpoint: primary REST collection slug (kebab)
 - kind: semantic grouping (header | line | support | generic)
 - aliases: optional list of legacy keys or equivalents (plural keys, legacy table names)

Resolvers accept:
 - canonical key (singular snake, e.g., 'sales_order_line')
 - legacy alias (e.g., 'sales_order_lines', 'projects')
 - endpoint slug (e.g., 'sales-order-lines')
 - simple plural/singular variants (append/remove a single trailing 's')
 - hyphen/underscore variants are normalized where applicable
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


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
    'account_exchange': ModelMeta('account_exchange', 'apps.accounts.models.exchange.Exchange', 'Account Exchange', 'Account Exchanges', 'account-exchanges', kind='support', aliases=['exchanges_account']),
    'audit': ModelMeta('audit', 'apps.accounts.models.audit.Audit', 'Audit', 'Audits', 'audits', kind='support', aliases=['audits']),
    'currency': ModelMeta('currency', 'apps.accounts.models.currency.Currency', 'Currency', 'Currencies', 'currencies', kind='support', aliases=['currencies']),
    'exchange_rate': ModelMeta('exchange_rate', 'apps.accounts.models.exchange_rate.ExchangeRate', 'Exchange Rate', 'Exchange Rates', 'exchange-rates', kind='support', aliases=['exchange_rates']),
    'exchange_transaction': ModelMeta('exchange_transaction', 'apps.accounts.models.exchange_transaction.ExchangeTransaction', 'Exchange Transaction', 'Exchange Transactions', 'exchange-transactions', kind='support', aliases=['exchange_transactions']),
    'gl_account': ModelMeta('gl_account', 'apps.accounts.models.gl_account.Gl_account', 'GL Account', 'GL Accounts', 'gl-accounts', kind='support', aliases=['gl_accounts']),
    'gl_journal': ModelMeta('gl_journal', 'apps.accounts.models.gl_journal.Gl_journal', 'GL Journal', 'GL Journals', 'gl-journals', kind='support', aliases=['gl_journals']),
    'ledger': ModelMeta('ledger', 'apps.accounts.models.ledger.Ledger', 'Ledger', 'Ledgers', 'ledgers', kind='support', aliases=['ledgers']),
    'tax_jurisdiction': ModelMeta('tax_jurisdiction', 'apps.accounts.models.tax_jurisdiction.TaxJurisdiction', 'Tax Jurisdiction', 'Tax Jurisdictions', 'tax-jurisdictions', kind='support', aliases=['tax_jurisdictions']),
    'term': ModelMeta('term', 'apps.accounts.models.term.Term', 'Term', 'Terms', 'terms', kind='support', aliases=['terms']),

    # --- communications --- (A->Z by key)
    'domain': ModelMeta('domain', 'apps.communications.models.domain.Domain', 'Domain', 'Domains', 'domains', kind='support', aliases=['domains']),
    'email': ModelMeta('email', 'apps.communications.models.email.Email', 'Email', 'Emails', 'emails', kind='support', aliases=['emails']),
    'location': ModelMeta('location', 'apps.communications.models.location.Location', 'Location', 'Locations', 'locations', kind='support', aliases=['locations']),
    'phone': ModelMeta('phone', 'apps.communications.models.phone.Phone', 'Phone', 'Phones', 'phones', kind='support', aliases=['phones']),

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
    'doc_linkage': ModelMeta('doc_linkage', 'apps.docs.models.linkage.Linkage', 'Doc Linkage', 'Doc Linkages', 'doc-linkages', kind='support', aliases=['linkages']),
    'doc_qa': ModelMeta('doc_qa', 'apps.docs.models.qa.Qa', 'Doc QA', 'Doc QAs', 'doc-qas', kind='support', aliases=['qa']),
    'doc_tag': ModelMeta('doc_tag', 'apps.docs.models.tag.Tag', 'Doc Tag', 'Doc Tags', 'doc-tags', kind='support', aliases=['tags']),

    # --- products --- (A->Z by key)
    'item': ModelMeta('item', 'apps.products.models.item.Item', 'Item', 'Items', 'items', kind='support', aliases=['items']),
    'bill_of_material': ModelMeta('bill_of_material', 'apps.products.models.bom.BillOfMaterial', 'Bill Of Material', 'Bill Of Materials', 'bills-of-material', kind='support', aliases=['bill_of_materials', 'bom']),
    'catalog': ModelMeta('catalog', 'apps.products.models.catalog.Catalog', 'Catalog', 'Catalogs', 'catalogs', kind='support', aliases=['catalogs']),
    'delivery_line': ModelMeta('delivery_line', 'apps.products.models.flow.DeliveryLine', 'Delivery Line', 'Delivery Lines', 'delivery-lines', kind='support', aliases=['delivery_lines']),
    'delivery_visit': ModelMeta('delivery_visit', 'apps.products.models.flow.DeliveryVisit', 'Delivery Visit', 'Delivery Visits', 'delivery-visits', kind='support', aliases=['delivery_visits']),
    'inventory_adjustment_run': ModelMeta('inventory_adjustment_run', 'apps.products.models.processor_runs.InventoryAdjustmentProcessorRun', 'Inventory Adjustment Run', 'Inventory Adjustment Runs', 'inventory-adjustment-runs', kind='support', aliases=['inventory_adjustment_runs']),
    'inventory_check': ModelMeta('inventory_check', 'apps.products.models.inventory_check.InventoryCheck', 'Inventory Check', 'Inventory Checks', 'inventory-checks', kind='support', aliases=['inventory_checks']),
    'inventory_check_line': ModelMeta('inventory_check_line', 'apps.products.models.inventory_check.InventoryCheckLine', 'Inventory Check Line', 'Inventory Check Lines', 'inventory-check-lines', kind='support', aliases=['inventory_check_lines']),
    'inventory_metrics_snapshot': ModelMeta('inventory_metrics_snapshot', 'apps.products.models.metrics.InventoryMetricsSnapshot', 'Inventory Metrics Snapshot', 'Inventory Metrics Snapshots', 'inventory-metrics-snapshots', kind='support', aliases=['inventory_metrics_snapshots']),
    'inventory_reservation': ModelMeta('inventory_reservation', 'apps.products.models.inventory_reservation.InventoryReservation', 'Inventory Reservation', 'Inventory Reservations', 'inventory-reservations', kind='support', aliases=['inventory_reservations']),
    'org_item': ModelMeta('org_item', 'apps.products.models.org_item.OrgItem', 'Org Item', 'Org Items', 'org-items', kind='support', aliases=['org_items']),
    'pending_inventory_adjustment': ModelMeta('pending_inventory_adjustment', 'apps.products.models.inventory_layer.PendingInventoryAdjustment', 'Pending Inventory Adjustment', 'Pending Inventory Adjustments', 'pending-inventory-adjustments', kind='support', aliases=['pending_inventory_adjustments']),
    'serial_log': ModelMeta('serial_log', 'apps.products.models.serial.SerialLog', 'Serial Log', 'Serial Logs', 'serial-logs', kind='support', aliases=['serial_logs']),
    'warehouse': ModelMeta('warehouse', 'apps.products.models.warehouse.Warehouse', 'Warehouse', 'Warehouses', 'warehouses', kind='support', aliases=['warehouses']),

    # --- sync --- (A->Z by key)
    'connection': ModelMeta('connection', 'apps.sync.models.connection.Connection', 'Connection', 'Connections', 'connections', kind='support', aliases=['connections']),
    'sync_exchange': ModelMeta('sync_exchange', 'apps.sync.models.exchange.Exchange', 'Sync Exchange', 'Sync Exchanges', 'sync-exchanges', kind='support', aliases=['exchanges_sync']),

    # --- transactions --- (A->Z by key)
    'invoice': ModelMeta('invoice', 'apps.transactions.models.line_variants.Invoice', 'Invoice', 'Invoices', 'invoices', kind='header', aliases=['invoices']),
    'invoice_line': ModelMeta('invoice_line', 'apps.transactions.models.line_variants.InvoiceLine', 'Invoice Line', 'Invoice Lines', 'invoice-lines', kind='line', aliases=['invoice_lines']),
    'project': ModelMeta('project', 'apps.transactions.models.projects.Project', 'Project', 'Projects', 'projects', kind='support', aliases=['projects']),
    'project_association': ModelMeta('project_association', 'apps.transactions.models.project_links.ProjectAssociation', 'Project Association', 'Project Associations', 'project-associations', kind='support', aliases=['project_associations']),
    'proposal': ModelMeta('proposal', 'apps.transactions.models.line_variants.Proposal', 'Proposal', 'Proposals', 'proposals', kind='header', aliases=['proposals']),
    'proposal_line': ModelMeta('proposal_line', 'apps.transactions.models.line_variants.ProposalLine', 'Proposal Line', 'Proposal Lines', 'proposal-lines', kind='line', aliases=['proposal_lines']),
    'purchase_order': ModelMeta('purchase_order', 'apps.transactions.models.line_variants.PurchaseOrder', 'Purchase Order', 'Purchase Orders', 'purchase-orders', kind='header', aliases=['purchase_orders']),
    'purchase_order_line': ModelMeta('purchase_order_line', 'apps.transactions.models.line_variants.PurchaseOrderLine', 'Purchase Order Line', 'Purchase Order Lines', 'purchase-order-lines', kind='line', aliases=['purchase_order_lines']),
    'purchase_receipt': ModelMeta('purchase_receipt', 'apps.transactions.models.purchase_receipt.PurchaseReceipt', 'Purchase Receipt', 'Purchase Receipts', 'purchase-receipts', kind='support', aliases=['purchase_receipts']),
    'requisition': ModelMeta('requisition', 'apps.transactions.models.line_variants.Requisition', 'Requisition', 'Requisitions', 'requisitions', kind='header', aliases=['requisitions']),
    'requisition_line': ModelMeta('requisition_line', 'apps.transactions.models.line_variants.RequisitionLine', 'Requisition Line', 'Requisition Lines', 'requisition-lines', kind='line', aliases=['requisition_lines']),
    'sales_order': ModelMeta('sales_order', 'apps.transactions.models.line_variants.SalesOrder', 'Sales Order', 'Sales Orders', 'sales-orders', kind='header', aliases=['sales_orders']),
    'sales_order_line': ModelMeta('sales_order_line', 'apps.transactions.models.line_variants.SalesOrderLine', 'Sales Order Line', 'Sales Order Lines', 'sales-order-lines', kind='line', aliases=['sales_order_lines']),
    'work_order': ModelMeta('work_order', 'apps.transactions.models.line_variants.Workorder', 'Work Order', 'Work Orders', 'work-orders', kind='header', aliases=['work_orders']),
    'work_order_line': ModelMeta('work_order_line', 'apps.transactions.models.line_variants.WorkorderLine', 'Work Order Line', 'Work Order Lines', 'workorder-lines', kind='line', aliases=['work_order_lines']),
}


# Indexes for fast resolution
_ENDPOINT_INDEX: Dict[str, str] = {m.endpoint: m.key for m in MODEL_REGISTRY.values()}
_ALIAS_INDEX: Dict[str, str] = {}
for key, meta in MODEL_REGISTRY.items():
    # register canonical and provided aliases
    _ALIAS_INDEX[key] = key
    for a in meta.aliases:
        _ALIAS_INDEX[a] = key
    # naively add trailing 's' plural when helpful
    if not key.endswith('s'):
        _ALIAS_INDEX[f"{key}s"] = key


def _normalize_token(token: str) -> str:
    return token.strip().lower()


def get_model_meta(name: str) -> Optional[ModelMeta]:
    """Resolve a model by canonical name, alias, endpoint, or simple plural.

    Accepts hyphen/underscore variants.
    """
    if not name:
        return None
    raw = _normalize_token(name)
    # direct matches
    if raw in MODEL_REGISTRY:
        return MODEL_REGISTRY[raw]
    if raw in _ENDPOINT_INDEX:
        return MODEL_REGISTRY[_ENDPOINT_INDEX[raw]]
    if raw in _ALIAS_INDEX:
        return MODEL_REGISTRY[_ALIAS_INDEX[raw]]
    # normalize hyphens to underscores
    norm = raw.replace('-', '_')
    if norm in MODEL_REGISTRY:
        return MODEL_REGISTRY[norm]
    if norm in _ALIAS_INDEX:
        return MODEL_REGISTRY[_ALIAS_INDEX[norm]]
    # try removing a single trailing 's'
    if norm.endswith('s') and norm[:-1] in MODEL_REGISTRY:
        return MODEL_REGISTRY[norm[:-1]]
    return None


def get_model_meta_by_endpoint(endpoint: str) -> Optional[ModelMeta]:
    key = _ENDPOINT_INDEX.get(_normalize_token(endpoint))
    return MODEL_REGISTRY.get(key) if key else None


def is_valid_model_name(name: str) -> bool:
    return get_model_meta(name) is not None


VALID_MODEL_NAMES: List[str] = list(MODEL_REGISTRY.keys())


__all__ = [
    'ModelMeta', 'MODEL_REGISTRY', 'VALID_MODEL_NAMES',
    'is_valid_model_name', 'get_model_meta', 'get_model_meta_by_endpoint'
]
