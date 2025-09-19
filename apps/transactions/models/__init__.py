from __future__ import annotations
import importlib
from typing import TYPE_CHECKING, Any, Dict, Tuple


_MAPPING: Dict[str, Tuple[str, str]] = {
    "Proposal": ("apps.transactions.models.proposal", "Proposal"),
    "ProposalLine": ("apps.transactions.models.proposal_line", "ProposalLine"),
    "SalesOrder": ("apps.transactions.models.sales_order", "SalesOrder"),
    "SalesOrderLine": ("apps.transactions.models.sales_order_line", "SalesOrderLine"),
    "Invoice": ("apps.transactions.models.invoice", "Invoice"),
    "InvoiceLine": ("apps.transactions.models.invoice_line", "InvoiceLine"),
    "WorkOrder": ("apps.transactions.models.work_order", "WorkOrder"),
    "WorkOrderLine": ("apps.transactions.models.work_order_line", "WorkOrderLine"),
    "PurchaseOrder": ("apps.transactions.models.purchase_order", "PurchaseOrder"),
    "PurchaseOrderLine": ("apps.transactions.models.purchase_order_line", "PurchaseOrderLine"),
}

__all__ = (
    "Proposal",
    "ProposalLine",
    "SalesOrder",
    "SalesOrderLine",
    "Invoice",
    "InvoiceLine",
    "WorkOrder",
    "WorkOrderLine",
    "PurchaseOrder",
    "PurchaseOrderLine",
)

def __getattr__(name: str) -> Any:
    try:
        mod_name, attr = _MAPPING[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    module = importlib.import_module(mod_name)
    value = getattr(module, attr)
    globals()[name] = value
    return value

def __dir__():
    return sorted(list(globals().keys()) + list(__all__))

if TYPE_CHECKING:  # pragma: no cover
    from .proposal import Proposal as Proposal
    from .proposal_line import ProposalLine as ProposalLine
    from .sales_order import SalesOrder as SalesOrder
    from .sales_order_line import SalesOrderLine as SalesOrderLine
    from .invoice import Invoice as Invoice
    from .invoice_line import InvoiceLine as InvoiceLine
    from .work_order import WorkOrder as WorkOrder
    from .work_order_line import WorkOrderLine as WorkOrderLine
    from .purchase_order import PurchaseOrder as PurchaseOrder
    from .purchase_order_line import PurchaseOrderLine as PurchaseOrderLine
