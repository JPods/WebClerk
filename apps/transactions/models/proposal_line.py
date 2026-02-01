from django.db import models
from .base_line_model import BaseSellLineModel


class ProposalLine(BaseSellLineModel):
    proposal = models.ForeignKey(
        "transactions.Proposal",
        related_name="lines",
        on_delete=models.CASCADE,
        db_column="proposal_id",
    )

    class Meta:
        db_table = "proposal_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.proposal

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.proposal_id


__all__ = ["ProposalLine"]