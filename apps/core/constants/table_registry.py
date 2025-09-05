"""Central registry for canonical table metadata.

Each entry describes a backend table (db_table), its Django model class path,
singular object label, plural collection label, and primary API endpoint slug.

This allows consistent usage across:
 - Settings (enforcing valid table_name values)
 - Permission matrix queries
 - Front-end discovery / docs
 - Potential code generation

Fields:
  key: internal identifier (same as db_table by convention)
  model: dotted import path to Django model (lazy import to avoid cycles)
  singular: human singular label
  plural: human plural label
  endpoint: primary REST collection endpoint segment
  kind: 'header' | 'line' | 'support' (optional semantic grouping)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TableMeta:
    key: str
    model: str
    singular: str
    plural: str
    endpoint: str
    kind: str = "generic"

    def import_model(self):  # lazy importer
        module_path, cls_name = self.model.rsplit('.', 1)
        module = __import__(module_path, fromlist=[cls_name])
        return getattr(module, cls_name)


# Canonical registry (add new tables here)
TABLE_REGISTRY: Dict[str, TableMeta] = {
    # Transaction headers
    'sales_orders': TableMeta('sales_orders', 'apps.transactions.models.line_variants.SalesOrder', 'Sales Order', 'Sales Orders', 'sales-orders', kind='header'),
    'purchase_orders': TableMeta('purchase_orders', 'apps.transactions.models.line_variants.PurchaseOrder', 'Purchase Order', 'Purchase Orders', 'purchase-orders', kind='header'),
    'work_orders': TableMeta('work_orders', 'apps.transactions.models.line_variants.Workorder', 'Work Order', 'Work Orders', 'work-orders', kind='header'),
    'proposal': TableMeta('proposal', 'apps.transactions.models.line_variants.Proposal', 'Proposal', 'Proposals', 'proposals', kind='header'),
    'invoice': TableMeta('invoice', 'apps.transactions.models.line_variants.Invoice', 'Invoice', 'Invoices', 'invoices', kind='header'),
    'requisition': TableMeta('requisition', 'apps.transactions.models.line_variants.Requisition', 'Requisition', 'Requisitions', 'requisitions', kind='header'),
    # Transaction lines
    'sales_order_lines': TableMeta('sales_order_lines', 'apps.transactions.models.line_variants.SalesOrderLine', 'Sales Order Line', 'Sales Order Lines', 'sales-order-lines', kind='line'),
    'purchase_order_lines': TableMeta('purchase_order_lines', 'apps.transactions.models.line_variants.PurchaseOrderLine', 'Purchase Order Line', 'Purchase Order Lines', 'purchase-order-lines', kind='line'),
    'work_order_lines': TableMeta('work_order_lines', 'apps.transactions.models.line_variants.WorkorderLine', 'Work Order Line', 'Work Order Lines', 'workorder-lines', kind='line'),
    'proposal_line': TableMeta('proposal_line', 'apps.transactions.models.line_variants.ProposalLine', 'Proposal Line', 'Proposal Lines', 'proposal-lines', kind='line'),
    'invoice_line': TableMeta('invoice_line', 'apps.transactions.models.line_variants.InvoiceLine', 'Invoice Line', 'Invoice Lines', 'invoice-lines', kind='line'),
    'requisition_line': TableMeta('requisition_line', 'apps.transactions.models.line_variants.RequisitionLine', 'Requisition Line', 'Requisition Lines', 'requisition-lines', kind='line'),
    # Projects / associations
    'projects': TableMeta('projects', 'apps.transactions.models.projects.Project', 'Project', 'Projects', 'projects', kind='support'),
    'project_associations': TableMeta('project_associations', 'apps.transactions.models.project_links.ProjectAssociation', 'Project Association', 'Project Associations', 'project-associations', kind='support'),
    # Settings
    'settings': TableMeta('settings', 'apps.core.models.setting.Setting', 'Setting', 'Settings', 'settings', kind='support'),
    # Generic documents (legacy / keyword indexing placeholder)
    'documents': TableMeta('documents', 'apps.core.models.setting.Setting', 'Document', 'Documents', 'documents', kind='support'),
    # Products / org assortment
    'org_items': TableMeta('org_items', 'apps.products.models.org_item.OrgItem', 'Org Item', 'Org Items', 'org-items', kind='support'),
}

VALID_TABLE_NAMES: List[str] = list(TABLE_REGISTRY.keys())

# Reverse lookup by endpoint slug (unique by convention)
TABLE_REGISTRY_BY_ENDPOINT: Dict[str, TableMeta] = {m.endpoint: m for m in TABLE_REGISTRY.values()}

def get_table_meta(key: str) -> TableMeta | None:
    return TABLE_REGISTRY.get(key)

def get_table_meta_by_endpoint(endpoint: str) -> TableMeta | None:
    return TABLE_REGISTRY_BY_ENDPOINT.get(endpoint)

def is_valid_table_name(name: str) -> bool:
    return name in TABLE_REGISTRY

__all__ = [
    'TableMeta', 'TABLE_REGISTRY', 'VALID_TABLE_NAMES', 'TABLE_REGISTRY_BY_ENDPOINT',
    'is_valid_table_name', 'get_table_meta', 'get_table_meta_by_endpoint'
]
