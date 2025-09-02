from django.db import models
from common.models import BaseModel

class Term(BaseModel):
    approved_by = models.CharField(max_length=255, blank=True, null=True)
    day_cut_off_due = models.IntegerField(blank=True, null=True)
    day_cut_off_invoice = models.IntegerField(blank=True, null=True)
    days_discount = models.IntegerField(blank=True, null=True)
    days_due = models.IntegerField(blank=True, null=True)
    days_in_period = models.IntegerField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    discount_rate = models.FloatField(blank=True, null=True)
    period_count = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Term ({self.id})"

    class Meta:
        db_table = 'terms'
    