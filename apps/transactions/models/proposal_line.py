from django.db import models
from .base_line_model import BaseSellLineModel

class ProposalLine(BaseSellLineModel):
    proposal_id = models.ForeignKey(
        "transactions.Proposal",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "proposal_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction."""
        return self.proposal_id

    @property
    def proposal_ref_id(self):
        # Mirror FK id for test helpers - use Django's FK attname directly
        return self.proposal_id.pk if self.proposal_id else None

    @proposal_ref_id.setter
    def proposal_ref_id(self, value):
        # Set the FK by id using Django's standard pattern
        self.proposal_id_id = value  # This is correct Django syntax when FK is named 'proposal_id'