from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel

class InvoiceLine(BaseLineModel):
    # Add any Order-specific fields or methods here
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

    quantity_packed = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)

  