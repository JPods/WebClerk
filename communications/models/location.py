# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/models/location.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid

class Location(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    address_type = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255, blank=True)
    instructions = models.TextField(blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    state = models.CharField(max_length=255, blank=True)
    zip = models.CharField(max_length=255, blank=True)
    full = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True, null=True)

    # all metadata changes occur in common.models.BaseModel


    class Meta:
        db_table = 'locations'
        
    def __str__(self):
        return f"{self.address1}, {self.city}, {self.state}"
    