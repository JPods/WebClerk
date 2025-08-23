# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/setting.py
import uuid
from django.db import models
from common.models import BaseModel

class Setting(BaseModel):
    is_active = models.BooleanField(default=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'settings'

    def __str__(self):
        return f"{self.name or 'Setting'} ({self.uuid})"