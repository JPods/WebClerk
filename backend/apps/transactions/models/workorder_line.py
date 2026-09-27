from django.db import models
from .base_line_model import BaseExecLineModel, EVENTS_HELP, default_events


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
    events = models.JSONField(default=default_events, blank=True, help_text=EVENTS_HELP)
    # Found stock on a count/adjust line lands in a layer of its own, as a receipt line's does.
    inventory_layer = models.ForeignKey(
        "products.InventoryLayer",
        related_name="workorder_lines",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Layer created for stock this line found",
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

    def save(self, *args, **kwargs):
        """A count line records the book itself (plan §16a.1/§16c.1): on first save its staged is
        the item's on_hand, whatever the caller sent (the line editors always send staged). After
        that the book never moves: a save that changes it is refused. (Per-warehouse books wait
        for the warehouse review, action 31277.)"""
        from apps.transactions.services.line_door import is_correction
        if self.line_type == 'count' and is_correction(self):
            quantity = dict(self.quantity) if isinstance(self.quantity, dict) else {}
            if self.pk is None:
                quantity['staged'] = self._book()
                self.quantity = quantity
            else:
                loaded = getattr(self, '_loaded', None) or {}
                if 'staged' in loaded and round(float(quantity.get('staged') or 0) - loaded['staged'], 6):
                    from apps.core.services.door import Refused
                    raise Refused(400, 'count_book_fixed',
                                  f"Line {self.pk}'s book ({loaded['staged']}) was taken when it was "
                                  "counted; it does not change. Change the count (active) instead.",
                                  {'line_id': self.pk})
        return super().save(*args, **kwargs)

    def _book(self) -> float:
        from apps.products.models import Item
        from apps.transactions.models.base_line_model import line_item_id
        item = Item.objects.filter(pk=line_item_id(self)).only('quantity').first()
        return float(((item.quantity or {}) if item else {}).get('on_hand') or 0)

    @property
    def events_qty(self) -> float:
        """How much this line has had done to it — the sum its remaining is measured against."""
        return round(sum(float((e or {}).get('qty') or 0)
                         for e in (self.events or []) if isinstance(e, dict)), 6)


__all__ = ["WorkOrderLine", "default_events"]
