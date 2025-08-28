# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/setting.py
import uuid
from django.db import models
from common.models import BaseModel
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
# 
class Connection(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    config = models.JSONField()
        #endpoints = models.JSONField(blank=True, null=True)
        #schedule = models.JSONField(blank=True, null=True)
        #path = models.JSONField(blank=True, null=True)
        #direction = models.CharField(max_length=255, blank=True)
        #path_completed = models.CharField(max_length=255, blank=True, null=True)
        #path_working = models.CharField(max_length=255, blank=True, null=True)
        #key = models.CharField(max_length=255, blank=True, null=True)
        #pin = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    scripts = models.JSONField(blank=True, null=True)
    relationships = models.JSONField(blank=True, null=True)
    action = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'apis'

    def __str__(self):
        return f"{self.name or 'API'} ({self.id})"
    
