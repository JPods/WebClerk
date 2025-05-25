import uuid
from django.db import models
from django.db.models import JSONField
from django.utils import timezone

class Action(models.Model):
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
    dt_action = models.DateTimeField(default=timezone.now)
    dt_completed = models.DateTimeField(default=timezone.now)
    dt_due = models.DateTimeField(default=timezone.now)
    dt_updated = models.DateTimeField(default=timezone.now)
    comment = models.TextField(blank=True, null=True)
    refs = JSONField(default=dict)
    prefs = JSONField(default=dict)
    metadata = JSONField(default=dict)

    class Meta:
        db_table = 'actions'

    def __str__(self):
        return f"{self.action or 'Action'} ({self.uuid})"