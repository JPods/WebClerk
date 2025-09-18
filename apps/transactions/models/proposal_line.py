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