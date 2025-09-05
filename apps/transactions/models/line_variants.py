"""Concrete parent + line models for transactional documents.

Each *Line model inherits from BaseLineModel to get unified JSON structures.
Parent models are intentionally minimal placeholders; expand as needed.
"""
from django.db import models
from .base_line_model import BaseLineModel

# ---------------------------------------------------------------------------
# Parent (header) models
# ---------------------------------------------------------------------------
class Proposal(models.Model):
    name = models.CharField(max_length=120)
    dt_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Proposal:{self.pk}:{self.name}" if self.pk else "Proposal:new"


class SalesOrder(models.Model):
    order_no = models.CharField(max_length=40, unique=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_orders"

    def __str__(self) -> str:  # pragma: no cover
        return f"SO:{self.order_no}" if self.order_no else f"SO:{self.pk}"


class Invoice(models.Model):
    invoice_no = models.CharField(max_length=40, unique=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Invoice:{self.invoice_no}" if self.invoice_no else f"Invoice:{self.pk}"


class PurchaseOrder(models.Model):
    po_no = models.CharField(max_length=40, unique=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchase_orders"

    def __str__(self) -> str:  # pragma: no cover
        return f"PO:{self.po_no}" if self.po_no else f"PO:{self.pk}"


class Workorder(models.Model):
    work_no = models.CharField(max_length=40, unique=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "work_orders"

    def __str__(self) -> str:  # pragma: no cover
        return f"WO:{self.work_no}" if self.work_no else f"WO:{self.pk}"


class Requisition(models.Model):
    req_no = models.CharField(max_length=40, unique=True)
    dt_created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"REQ:{self.req_no}" if self.req_no else f"REQ:{self.pk}"


# ---------------------------------------------------------------------------
# Line models
# ---------------------------------------------------------------------------
class ProposalLine(BaseLineModel):
    parent = models.ForeignKey(Proposal, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "proposal_line"


class SalesOrderLine(BaseLineModel):
    parent = models.ForeignKey(SalesOrder, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "sales_order_lines"


class InvoiceLine(BaseLineModel):
    parent = models.ForeignKey(Invoice, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "invoice_line"


class PurchaseOrderLine(BaseLineModel):
    parent = models.ForeignKey(PurchaseOrder, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "purchase_order_lines"


class WorkorderLine(BaseLineModel):
    parent = models.ForeignKey(Workorder, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "work_order_lines"


class RequisitionLine(BaseLineModel):
    parent = models.ForeignKey(Requisition, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "requisition_line"


__all__ = [
    "Proposal", "ProposalLine",
    "SalesOrder", "SalesOrderLine",
    "Invoice", "InvoiceLine",
    "PurchaseOrder", "PurchaseOrderLine",
    "Workorder", "WorkorderLine",
    "Requisition", "RequisitionLine",
]
