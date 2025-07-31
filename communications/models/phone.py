from django.db import models
from common.models import BaseModel
import uuid

class Phone(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    attention = models.CharField(max_length=255, blank=True)
    country_code = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=255, blank=True)
    opt_out = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True, null=True)
    dt_verified = models.DateTimeField(null=True, blank=True, help_text="When phone was verified")

        # Add the missing webClerk3 standard JSONB fields
    refs = models.JSONField(default=dict, blank=True, help_text="Keywords, tags, and related references")
    metadata = models.JSONField(default=dict, blank=True, help_text="Health, profiles, undefined and other user defined data")
    pres = models.JSONField(default=dict, blank=True, help_text="Various user defined preferences for the data")

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.number})"
        return self.number
    
    class Meta:
        db_table = 'phones'