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
    def proposal_ref_id(self):
        # Mirror FK id for test helpers
        return getattr(self, "proposal_id_id", None)

    @proposal_ref_id.setter
    def proposal_ref_id(self, value):
        self.proposal_id_id = value