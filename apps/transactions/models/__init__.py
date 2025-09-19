# pyright: reportUnsupportedDunderAll=false
from __future__ import annotations
import importlib
import os
from typing import TYPE_CHECKING, Tuple

# Map public model names -> (module, class)
_MAPPING = {
    'Proposal': ('proposal', 'Proposal'),
    'ProposalLine': ('proposal_line', 'ProposalLine'),

    'SalesOrder': ('sales_order', 'SalesOrder'),
    'SalesOrderLine': ('sales_order_line', 'SalesOrderLine'),

    'Invoice': ('invoice', 'Invoice'),
    'InvoiceLine': ('invoice_line', 'InvoiceLine'),

    'PurchaseOrder': ('purchase_order', 'PurchaseOrder'),
    'PurchaseOrderLine': ('purchase_order_line', 'PurchaseOrderLine'),

    'WorkOrder': ('work_order', 'WorkOrder'),
    'WorkOrderLine': ('work_order_line', 'WorkOrderLine'),

    'Requisition': ('requisition', 'Requisition'),
    #'RequisitionStd': ('requisition', 'Requisition'),  # back-compat
    'RequisitionLine': ('requisition_line', 'RequisitionLine'),
}

def __getattr__(name: str):
    try:
        mod_name, attr = _MAPPING[name]
    except KeyError as e:
        raise AttributeError(f"module {__name__} has no attribute {name}") from e
    module = importlib.import_module(f".{mod_name}", __name__)
    return getattr(module, attr)

def _eager_bind_all() -> None:
    """Eagerly import and bind all mapped models into this package namespace."""
    for name, (mod_name, cls_name) in _MAPPING.items():
        module = importlib.import_module(f".{mod_name}", __name__)
        globals()[name] = getattr(module, cls_name)

def __dir__():
    # Expose dynamic names for editors/introspection
    return sorted(list(globals().keys()) + list(_MAPPING.keys()))

# Keep dynamic exports; use a typed tuple for better analyzer compatibility
__all__: Tuple[str, ...] = tuple(_MAPPING.keys())

# Optional: bind for type checkers or when explicitly requested
if TYPE_CHECKING or os.getenv("TRANSACTIONS_EAGER_IMPORT") == "1":
    _eager_bind_all()