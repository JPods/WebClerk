from django.db import models
from .base_transaction_model import TransactionBaseModel


class Proposal(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    class Meta:
        db_table = "proposals"

    dt_due = models.BigIntegerField(null=True, blank=True,
        help_text="Proposal expiry date (epoch ms) — quote valid until this date")

    def __str__(self) -> str:
        return f"Proposal #{self.id} ({self.ida or ''})"

    @property
    def name(self) -> str:
        # Prefer existing title/label/display_name if present; fallback to transient
        return (
            getattr(self, 'title', None)
            or getattr(self, 'label', None)
            or getattr(self, 'display_name', None)
            or getattr(self, '_transient_name', '')
            or ''
        )

    @name.setter
    def name(self, value: str) -> None:
        if hasattr(self, 'title'):
            self.title = value
        elif hasattr(self, 'label'):
            self.label = value
        elif hasattr(self, 'display_name'):
            self.display_name = value
        else:
            # Transient (not persisted) but allows Proposal.objects.create(name=...)
            self._transient_name = value