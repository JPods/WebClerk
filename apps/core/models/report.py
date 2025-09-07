from django.db import models
from django.utils import timezone
from common.models import BaseModel


class Pending(BaseModel):
    """Ephemeral queue / staging record (CoreModel only).

    Lightweight by design: no metadata/refs/prefs/comments overhead.
    Use for decoupling write spikes & deferred processing.
    """
    table_name = models.CharField(max_length=255, blank=True, null=True)
    record_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    purpose = models.CharField(max_length=120, blank=True, null=True)
    name = models.CharField(max_length=120, blank=True, null=True)
    data = models.JSONField(default=dict)
    dt_processed = models.BigIntegerField(default=0, db_index=True)

   

    class Meta:
        db_table = 'reports'

    def __str__(self):
        return f"{self.name or 'Report'} ({self.id})"
    
