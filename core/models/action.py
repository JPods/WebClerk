# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/action.py
import uuid
from django.db import models
from django.utils import timezone
from common.models import BaseModel

class Action(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    action = models.CharField(max_length=255, blank=True, null=True)
    action_by = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=255, blank=True, null=True)
    difficulty = models.CharField(max_length=255, blank=True, null=True)
    hours = models.FloatField(blank=True, null=True)
    percent = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    quality = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    dt_action = models.DateTimeField(null=True, blank=True)
    dt_completed = models.DateTimeField(null=True, blank=True)
    dt_due = models.DateTimeField(null=True, blank=True)
    dt_updated = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'actions'

    def __str__(self):
        return f"{self.action or 'Action'} ({self.uuid})"