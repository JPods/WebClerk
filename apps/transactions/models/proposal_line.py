from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel
from .proposal import Proposal

class ProposalLine(BaseLineModel):
    parent_id = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    # ProposalLine-specific win probability (0-100)
    probability = models.IntegerField(blank=True, null=True, help_text="0-100 percent likelihood")

    def __str__(self) -> str:  # pragma: no cover
        return f"ProposalLine:{self.pk}" if self.pk else "ProposalLine:new"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.probability is not None and not (0 <= self.probability <= 100):
            raise ValidationError({"probability": "Must be between 0 and 100."})
        return super().clean()


    class Meta:
        db_table = "proposal_line"


__all__ = ["ProposalLine"]