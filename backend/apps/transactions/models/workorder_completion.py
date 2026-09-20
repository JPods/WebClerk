from django.db import models

from .base_line_model import BaseExecLineModel


class WorkOrderCompletion(BaseExecLineModel):
    """Goods produced by a workorder, arriving in inventory.

    Bill, 2026-09-20: *"Because wo are internal should we just make the wo_line itself
    the receiving document that triggers a pending... We can add another object in the
    workorder."*

    A receipt is the document that says goods came from **outside** — it carries a
    vendor, terms and an AP ledger. Production comes from inside: nothing is owed to
    anyone, so a completion is not a receipt and can never become a payable. That is
    structural here, not a rule somebody has to remember.

    It is still a line like any other: a child of the WorkOrderLine it completes
    (``parent_line_id``), so that line's ``remaining`` is recomputed by the one writer,
    and partial completions each keep their own warehouse, lot and cost.
    """
    workorder = models.ForeignKey(
        "transactions.WorkOrder",
        related_name="completions",
        on_delete=models.CASCADE,
        db_column="workorder_id",
    )
    warehouse = models.ForeignKey(
        "products.Warehouse",
        related_name="workorder_completions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Warehouse the produced goods entered",
    )
    inventory_layer = models.ForeignKey(
        "products.InventoryLayer",
        related_name="workorder_completions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Inventory layer created for this completion (FIFO/LIFO)",
    )
    lot = models.CharField(max_length=100, blank=True, help_text="Lot number")
    serial_batch = models.CharField(max_length=100, blank=True, help_text="Serial or batch number")

    class Meta:
        db_table = "workorder_completion"
        indexes = [
            models.Index(fields=['workorder', 'warehouse']),
        ]

    @property
    def parent(self):
        """The header this line belongs to (uniform across all line types)."""
        return self.workorder

    @property
    def parent_id_value(self):
        return self.workorder_id

    def __str__(self) -> str:  # pragma: no cover
        return f"WorkOrderCompletion {self.id} on workorder {self.workorder_id}"


__all__ = ["WorkOrderCompletion"]
