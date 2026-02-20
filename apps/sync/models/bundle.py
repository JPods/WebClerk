from django.db import models

from common.models import BaseModel
from apps.sync.choices import (
    BUNDLE_ALERT_CHOICES,
    BUNDLE_DIRECTION_CHOICES,
    BUNDLE_STATUS_CHOICES,
)
from .connection import Connection  # Relative import
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
#
    
class Bundle(BaseModel):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='bundles', db_column='connection_id')
    direction = models.CharField(max_length=255, choices=BUNDLE_DIRECTION_CHOICES)
    config = models.JSONField()
    status = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=BUNDLE_STATUS_CHOICES,
    )
    alert = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=BUNDLE_ALERT_CHOICES,
    )
    response = models.JSONField(blank=True, null=True)
    duration = models.BigIntegerField(default=0)
    payload = models.JSONField(blank=True, null=True)
    size = models.BigIntegerField(default=0)
    #at the time of the bundle
    maps = models.JSONField(blank=True, null=True)
    encryption = models.JSONField(blank=True, null=True)
    rules = models.JSONField(blank=True, null=True)
    conflicts = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'bundles'

    def __str__(self):
        return f"Bundle {self.id} for connection {self.connection.id}"