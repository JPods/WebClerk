from decimal import Decimal
from typing import Dict, Any
from django.db import models
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.po_totals import compute_purchase_order_cost_totals

class PurchaseOrder(TransactionBaseModel):
    # Identifier for POs
    po_no = models.CharField(max_length=64, default="", db_index=True)
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

    # Use string refs for FKs/M2Ms to avoid import cycles
    sales_order = models.ForeignKey(
        "transactions.SalesOrder",  # app_label.ModelName
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders",
    )

    class Meta:
        db_table = "purchase_orders"

    def update_cost_totals(self) -> Dict[str, Any]:
        """Compute and optionally persist header cost totals from lines."""
        totals = compute_purchase_order_cost_totals(self)
        # If this model has a header-level 'cost' or 'totals' JSON, set it here.
        # Example (uncomment if you store header cost under 'cost'):
        # self.cost = totals
        # self.save(update_fields=["cost", "dt_modified", "version"])
        return totals

    def __str__(self) -> str:
        return f"PurchaseOrder #{self.id} ({self.ida or ''})"

__all__ = ["PurchaseOrder"]
