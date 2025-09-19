from django.db import models

class PurchaseOrderLine(models.Model):
    parent = models.ForeignKey(
        "transactions.PurchaseOrder",
        on_delete=models.CASCADE,
        related_name="lines",
    )

    class Meta:
        db_table = "purchase_order_lines"
