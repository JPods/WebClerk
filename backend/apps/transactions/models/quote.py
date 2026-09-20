from django.db import models
from .base_transaction_model import TransactionBaseModel


class Quote(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    # ── Rep assignment (Bill, 2026-09-20) ────────────────────────────
    # A value, not a ForeignKey: a rep org is a reference, and deleting one must never
    # cascade into the records it was assigned to. rep_id carries the assignment and
    # attention_rep the person at that rep, the way attention names the person at the org.
    rep_id = models.BigIntegerField(null=True, blank=True, db_index=True,
        help_text="Rep org credited with this document")
    attention_rep = models.CharField(max_length=255, blank=True, null=True,
        help_text="The person at the rep")

    class Meta:
        db_table = "quotes"

    dt_due = models.BigIntegerField(null=True, blank=True,
        help_text="Quote expiry date (epoch ms) — quote valid until this date")
    probability = models.FloatField(default=0.0, db_index=True,
        help_text="Close probability 0.0–1.0. Feeds forecast: totals × probability = weighted pipeline.")

    def __str__(self) -> str:
        return f"Quote #{self.id} ({self.ida or ''})"

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
            # Transient (not persisted) but allows Quote.objects.create(name=...)
            self._transient_name = value