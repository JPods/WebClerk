from django.db import models
from .base_line_model import BaseExecLineModel


def default_events() -> list:
    return []


class WorkOrderLine(BaseExecLineModel):
    """A line of work: what to produce, or what to count.

    Bill, 2026-09-20: *"I think I like it better as an object array for each change."*

    A document line is something a person sends to someone — a quote line, an invoice
    line, a receipt line. A change event is not sent anywhere: it is what happened to
    this line. So the events live on the line, in ``events[]``, the way item.py keeps
    its price history.

    Every event is written by the pending applier, never by the request: one apply moves
    the buckets and appends the event under the same lock, so two people completing 3 and
    7 units at the same instant produce two pendings that serialize, and neither can
    clobber the other's event.

    An event carries: id (uuid, so an apply is idempotent), kind ('completion' | 'count'),
    dt, by, qty, warehouse, lot, serial, layer_id, unit_cost — and for a count, the book
    figure, what was counted and the variance.
    """
    workorder = models.ForeignKey(
        "transactions.WorkOrder",
        related_name="lines",
        on_delete=models.CASCADE,
        db_column="workorder_id",
        null=True,
        blank=True,
    )
    events = models.JSONField(
        default=default_events, blank=True,
        help_text="What happened to this line: completions and counts, each an event",
    )

    def __str__(self):
        return f"WorkOrderLine {self.id} on workorder {self.workorder_id}"

    class Meta:
        db_table = "work_order_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.workorder

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.workorder_id

    @property
    def events_qty(self) -> float:
        """How much this line has had done to it — the sum its remaining is measured against."""
        return round(sum(float((e or {}).get('qty') or 0)
                         for e in (self.events or []) if isinstance(e, dict)), 6)


__all__ = ["WorkOrderLine", "default_events"]
