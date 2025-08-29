"""Concrete parent + line models for transactional documents.

Each *Line model inherits from BaseLineModel to get unified JSON structures.
Parent models are intentionally minimal placeholders; expand as needed.
"""
from django.db import models
from .base_line_model import BaseLineModel

# Parent (header) models -------------------------------------------------
class Proposal(models.Model):
    name = models.CharField(max_length=120)
    created_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Proposal:{self.pk}:{self.name}" if self.pk else "Proposal:new"


class Order(models.Model):
    order_no = models.CharField(max_length=40, unique=True)
    created_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Order:{self.order_no}" if self.order_no else f"Order:{self.pk}"


class Invoice(models.Model):
    invoice_no = models.CharField(max_length=40, unique=True)
    created_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Invoice:{self.invoice_no}" if self.invoice_no else f"Invoice:{self.pk}" 


class Purchase(models.Model):
    po_no = models.CharField(max_length=40, unique=True)
    created_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"PO:{self.po_no}" if self.po_no else f"PO:{self.pk}" 


class Workorder(models.Model):
    work_no = models.CharField(max_length=40, unique=True)
    created_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"WO:{self.work_no}" if self.work_no else f"WO:{self.pk}" 


class Requisition(models.Model):
    req_no = models.CharField(max_length=40, unique=True)
    created_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"REQ:{self.req_no}" if self.req_no else f"REQ:{self.pk}" 


# Line models ------------------------------------------------------------
class ProposalLine(BaseLineModel):
    parent = models.ForeignKey(Proposal, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "proposal_line"


class OrderLine(BaseLineModel):
    parent = models.ForeignKey(Order, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "order_line"


class InvoiceLine(BaseLineModel):
    parent = models.ForeignKey(Invoice, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "invoice_line"


class PurchaseLine(BaseLineModel):
    parent = models.ForeignKey(Purchase, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "purchase_line"


class WorkorderLine(BaseLineModel):
    parent = models.ForeignKey(Workorder, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "workorder_line"


class RequisitionLine(BaseLineModel):
    parent = models.ForeignKey(Requisition, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "requisition_line"


__all__ = [
    "Proposal", "ProposalLine",
    "Order", "OrderLine",
    "Invoice", "InvoiceLine",
    "Purchase", "PurchaseLine",
    "Workorder", "WorkorderLine",
    "Requisition", "RequisitionLine",
]
