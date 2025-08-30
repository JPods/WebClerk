from django.db import models
from common.models import BaseModel


class RequisitionStd(BaseModel):
    name = models.CharField(max_length=255, blank=True, db_index=True)
    purpose = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=64, blank=True, default='draft', db_index=True)
    description = models.TextField(blank=True)
    cost = models.FloatField(null=True, blank=True, default=0)
    cost_extended = models.FloatField(null=True, blank=True, default=0)
    lead_days = models.IntegerField(null=True, blank=True, default=0)
    quantity = models.FloatField(null=True, blank=True, default=0)
    quantity_extended = models.FloatField(null=True, blank=True, default=0)

    class Meta:
        db_table = 'requisitions_std'
        indexes = [
            models.Index(fields=['purpose']),
            models.Index(fields=['status']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"ReqStd {self.id} {self.name or ''} ({self.status})"
