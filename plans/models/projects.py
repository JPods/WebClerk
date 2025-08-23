from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid

# Explanation: Records the aggregate across multiple proposals, orders, invoices, etc.
# Metadata fields include: _totalInventory, dtCompleted, dtCreated, dtGrantt, dtUpdated, idaCustomer

class Project(BaseModel):
    attention = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    publish = models.IntegerField(blank=True, null=True)
    scope = models.TextField(blank=True, null=True)
    status_gantt = models.CharField(max_length=255, blank=True, null=True)
    total_invoices = models.FloatField(blank=True, null=True)
    total_pos = models.FloatField(blank=True, null=True)
    total_proposals = models.FloatField(blank=True, null=True)
    total_sos = models.FloatField(blank=True, null=True)
