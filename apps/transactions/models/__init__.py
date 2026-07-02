# pyright: reportUnsupportedDunderAll=false
from __future__ import annotations
import importlib
import os
from typing import TYPE_CHECKING, Tuple

# Map public model names -> (module, class)
_MAPPING = {
    'Proposal': ('proposal', 'Proposal'),
    'ProposalLine': ('proposal_line', 'ProposalLine'),

    'Order': ('order', 'Order'),
    'OrderLine': ('order_line', 'OrderLine'),

    'Invoice': ('invoice', 'Invoice'),
    'InvoiceLine': ('invoice_line', 'InvoiceLine'),

    'Purchase': ('purchase', 'Purchase'),
    'PurchaseLine': ('purchase_line', 'PurchaseLine'),

    'WorkOrder': ('workorder', 'WorkOrder'),
    'WorkOrderLine': ('workorder_line', 'WorkOrderLine'),

    'Requisition': ('requisition', 'Requisition'),
    #'RequisitionStd': ('requisition', 'Requisition'),  # back-compat
    'RequisitionLine': ('requisition_line', 'RequisitionLine'),

    'Receipt': ('receipt', 'Receipt'),
    'ReceiptLine': ('receipt_line', 'ReceiptLine'),

    'Payment': ('payment', 'Payment'),
    'PaymentMethod': ('payment', 'PaymentMethod'),
    'PaymentTerm': ('payment', 'PaymentTerm'),
    'PaymentApplication': ('payment_application', 'PaymentApplication'),
    'PendingPaymentApplication': ('pending_payment', 'PendingPaymentApplication'),
    'Project': ('project', 'Project'),
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

# Eagerly import and bind all mapped models so Django can resolve string FK targets
# like "transactions.Proposal" during system checks.
try:
    _eager_bind_all()  # defined above in this module
except Exception:
    # Tolerate optional models missing in some environments
    pass