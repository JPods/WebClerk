# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/setting.py
from django.db import models
from common.models import BaseModel
from .connections import Connection  # Relative import
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
#
    
class Exchange(BaseModel):
    connection_id = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='exchanges')
    direction = models.CharField(max_length=255)
    config = models.JSONField()
    status = models.CharField(max_length=255, blank=True, null=True)
    alert = models.CharField(max_length=255, blank=True, null=True)
    response = models.JSONField(blank=True, null=True)
    duration = models.BigIntegerField(default=0)  # in milliseconds
    payload = models.JSONField(blank=True, null=True)
    size = models.BigIntegerField(default=0)  # in bytes

    class Meta:
        db_table = 'exchanges'

    def __str__(self):
        return f"Exchange {self.id} for API {self.connection_id.id}"