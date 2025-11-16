from django.db import models
from common.models import BaseModel

class PurchaseReceipt(BaseModel):
	"""Received shipment representing one or more received PO line partials."""
	#id is inherited from BaseModel
	#receipt_no = models.CharField(max_length=40, unique=True)
	dt_received = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "purchase_receipts"

	def __str__(self) -> str:  # pragma: no cover
		return f"PR:{self.receipt_no}" if self.receipt_no else f"PR:{self.pk}"