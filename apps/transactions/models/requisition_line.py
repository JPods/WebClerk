from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel

class RequisitionLine(BaseLineModel):
    # Add any RequisitionLine-specific fields or methods here
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

 class Meta:
        db_table = "requisition_lines"
  