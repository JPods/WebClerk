from decimal import Decimal
from django.db import models
from .BaseLineModel import BaseLineModel

class PurchaseLine(BaseLineModel):
    # Add any Order-specific fields or methods here
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

    quantity_received = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
