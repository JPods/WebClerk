from django.db import models
from common.models import BaseModel


class Notification(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    model_name = models.CharField(max_length=255, blank=True, null=True)
    record_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    config = models.JSONField(default=dict)

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return f"{self.name or 'Notification'} ({self.id})"
    
