from django.db import models
from common.models import BaseModel


class TransactionBaseModel(BaseModel):
    """Abstract Django base for transaction headers.

    Minimal fields only; JSON envelopes and lifecycle come from common.BaseModel.
    """

    STATUS_PLANNED = "planned"
    STATUS_RELEASED = "released"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_HOLD = "hold"
    STATUS_COMPLETE = "complete"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = (
        (STATUS_PLANNED, "Planned"),
        (STATUS_RELEASED, "Released"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_HOLD, "Hold"),
        (STATUS_COMPLETE, "Complete"),
        (STATUS_CANCELED, "Canceled"),
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PLANNED, db_index=True)
    priority = models.CharField(max_length=32, blank=True, null=True)
    price_level = models.CharField(max_length=50, blank=True, null=True)
    customer_id = models.BigIntegerField(default=0, db_index=True)
    manufacturer_id = models.BigIntegerField(default=0, db_index=True)
    vendor_id = models.BigIntegerField(default=0, db_index=True)

    class Meta:
        abstract = True


