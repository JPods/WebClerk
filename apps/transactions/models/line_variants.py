"""Concrete parent + line models for transactional documents.

Each *Line model inherits from BaseLineModel to get unified JSON structures.
Parent models are intentionally minimal placeholders; expand as needed.
"""
from django.db import models
from django.core.exceptions import ValidationError
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
    STATUS_PLANNED = 'planned'
    STATUS_RELEASED = 'released'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_HOLD = 'hold'
    STATUS_COMPLETE = 'complete'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = (
        (STATUS_PLANNED, 'Planned'),
        (STATUS_RELEASED, 'Released'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_HOLD, 'Hold'),
        (STATUS_COMPLETE, 'Complete'),
        (STATUS_CANCELED, 'Canceled'),
    )

    work_no = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, db_index=True, default=STATUS_PLANNED, help_text='Lifecycle state')
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "work_orders"
        indexes = [
            models.Index(fields=("status", "dt_created"), name="workorder_status_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"WO:{self.work_no}" if self.work_no else f"WO:{self.pk}"

    def _validate_transition(self, prev: str | None, new: str) -> None:
        if prev is None or prev == new:
            return
        allowed: dict[str, set[str]] = {
            self.STATUS_PLANNED: {self.STATUS_RELEASED, self.STATUS_CANCELED},
            self.STATUS_RELEASED: {self.STATUS_IN_PROGRESS, self.STATUS_HOLD, self.STATUS_CANCELED},
            self.STATUS_IN_PROGRESS: {self.STATUS_HOLD, self.STATUS_COMPLETE},
            self.STATUS_HOLD: {self.STATUS_RELEASED, self.STATUS_CANCELED},
            self.STATUS_COMPLETE: set(),
            self.STATUS_CANCELED: set(),
        }
        if new not in allowed.get(prev, set()):
            raise ValidationError({
                'status': f"Invalid transition {prev} -> {new}"
            })

        # Additional completion guard: all lines must be done before completing
        if new == self.STATUS_COMPLETE and self.pk:
            # Only consider concrete line statuses equal to 'done'
            if self.lines.exclude(status='done').exists():
                raise ValidationError({'status': 'Cannot complete while some lines are not done'})

    def save(self, *args, **kwargs):
        prev = None
        if getattr(self, 'pk', None):
            try:
                prev = Workorder.objects.only('status').get(pk=self.pk).status
            except Workorder.DoesNotExist:
                prev = None
        self._validate_transition(prev, self.status)
        return super().save(*args, **kwargs)


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

    # Line-level status lifecycle (validated in save())
    STATUS_PLANNED = 'planned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_SKIPPED = 'skipped'
    STATUS_REWORK = 'rework'
    STATUS_CHOICES = (
        (STATUS_PLANNED, 'Planned'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_DONE, 'Done'),
        (STATUS_SKIPPED, 'Skipped'),
        (STATUS_REWORK, 'Rework'),
    )

    class Meta:
        db_table = "work_order_lines"
        indexes = [
            # Keep index name <=30 chars for cross-DB compatibility
            models.Index(fields=("parent_ref_id", "status"), name="wo_line_parent_status_idx"),
        ]

    def _validate_transition(self, prev: str | None, new: str) -> None:
        # Empty/None treated as planned on first set
        if not new:
            return
        if prev is None or prev == new:
            return
        allowed: dict[str, set[str]] = {
            self.STATUS_PLANNED: {self.STATUS_IN_PROGRESS, self.STATUS_SKIPPED, self.STATUS_DONE},
            self.STATUS_IN_PROGRESS: {self.STATUS_DONE, self.STATUS_REWORK},
            self.STATUS_REWORK: {self.STATUS_DONE},
            self.STATUS_DONE: set(),
            self.STATUS_SKIPPED: set(),
        }
        # If previous was None or empty string, treat as planned
        prev_eff = prev if prev else self.STATUS_PLANNED
        if new not in allowed.get(prev_eff, set()):
            raise ValidationError({'status': f"Invalid line transition {prev or 'planned'} -> {new}"})

    def save(self, *args, **kwargs):
        # Default empty status to planned
        if not self.status:
            self.status = self.STATUS_PLANNED
        prev = None
        if getattr(self, 'pk', None):
            try:
                prev = WorkorderLine.objects.only('status').get(pk=self.pk).status
            except WorkorderLine.DoesNotExist:
                prev = None
        self._validate_transition(prev, self.status)
        return super().save(*args, **kwargs)


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
