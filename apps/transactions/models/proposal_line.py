from django.db import models
from .base_line_model import BaseSellLineModel

class ProposalLine(BaseSellLineModel):
    parent = models.ForeignKey(
        "transactions.Proposal",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "proposal_lines"

    @property
    def parent_ref_id(self):
        # Mirror FK id for test helpers
        return getattr(self, "parent_id", None)

    @parent_ref_id.setter
    def parent_ref_id(self, value):
        self.parent_id = value