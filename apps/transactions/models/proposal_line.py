from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel

BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

# Deprecated module: ProposalLine is defined in line_variants.
# Re-export here for backward compatibility if anything imports apps.transactions.models.proposal_line.ProposalLine
from .line_variants import ProposalLine  # noqa: F401

__all__ = ["ProposalLine"]