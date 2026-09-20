from django.db import models
from .base_transaction_model import TransactionBaseModel


class WorkOrder(TransactionBaseModel):
    """Work to be done that changes inventory without anyone being owed money.

    Two kinds (Bill, 2026-09-20):

    * **production** — material becomes stock. Lines commit on_wo; completions turn
      that work in progress into on_hand.
    * **count** — an audit. A line names an item, ``quantity.staged`` holds the book
      figure when the line was opened and ``quantity.active`` is what the counter saw.
      Counting reserves nothing, so a count line commits no bucket; completing it moves
      on_hand to the counted number.

      *"I think users counting what they see is the best approach. They do not need to
      do the math. Perhaps staged versus active so they need to know to hunt harder if
      the count is off."*
    """
    KIND_PRODUCTION = 'production'
    KIND_COUNT = 'count'
    KIND_CHOICES = [
        (KIND_PRODUCTION, 'Production'),
        (KIND_COUNT, 'Count'),
    ]

    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES, default=KIND_PRODUCTION, db_index=True,
        help_text="production — material becomes stock; count — an inventory audit",
    )

    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    class Meta:
        db_table = "work_orders"

    @property
    def is_count(self) -> bool:
        return self.kind == self.KIND_COUNT

    def __str__(self) -> str:
        return f"WorkOrder #{self.id} ({self.ida or ''})"


__all__ = ["WorkOrder"]
