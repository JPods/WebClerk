from django.db import models
from common.models import BaseModel


class Report(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    model_name = models.CharField(max_length=255, blank=True, null=True)
    record_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    data = models.JSONField(default=dict)

    class Meta:
        db_table = 'reports'

    def __str__(self):
        return f"{self.name or 'Report'} ({self.id})"
    
