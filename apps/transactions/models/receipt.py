from django.db import models
from common.models import BaseModel

class Receipt(BaseModel):
	"""Received shipment representing one or more received PO line partials."""
	# id is inherited from BaseModel
	# ida is used as the receipt identifier (auto-generated from id)
	dt_received = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "inventory_receipt"

	def __str__(self) -> str:  # pragma: no cover
		return f"R:{self.ida}" if self.ida else f"R:{self.pk}"