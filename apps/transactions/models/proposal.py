from typing import Dict
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.proposal_totals import compute_proposal_sell_cost_totals

class Proposal(TransactionBaseModel):
    probability = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probability of closing this proposal (0-100%)"
    )

    class Meta:
        db_table = "proposals"

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, float]]:
        """Compute sell/cost/totals from lines. If persist=True and fields exist, save them."""
        computed = compute_proposal_sell_cost_totals(self)

        if persist:
            update_fields: list[str] = []
            if hasattr(self, "sell"):
                self.sell = computed["sell"]  # type: ignore[assignment]
                update_fields.append("sell")
            if hasattr(self, "cost"):
                self.cost = computed["cost"]  # type: ignore[assignment]
                update_fields.append("cost")
            if hasattr(self, "totals"):
                self.totals = computed["totals"]  # type: ignore[assignment]
                update_fields.append("totals")
            if update_fields:
                update_fields += ["dt_modified", "version"]
                self.save(update_fields=update_fields)

        return computed

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