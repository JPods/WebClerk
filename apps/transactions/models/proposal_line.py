from django.db import models
from decimal import Decimal

BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

class ProposalLine(models.Model):
    # Add any Proposal-specific fields or methods here

    quantity_ordered = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_blanket = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)