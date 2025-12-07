from django.db import models
from common.models import BaseModel
from .connection import Connection  # Relative import
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
#
    
class Bundle(BaseModel):
    id_connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='bundles')
    direction = models.CharField(max_length=255)
    config = models.JSONField()
    status = models.CharField(max_length=255, blank=True, null=True)
    alert = models.CharField(max_length=255, blank=True, null=True)
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
        return f"Bundle {self.id} for connection {self.id_connection.id}"