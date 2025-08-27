# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/models/location.py
from django.db import models
<<<<<<< HEAD:communications/models/location.py
from common.models import BaseModel
from django.utils import timezone
=======
from common.base_model import BaseModel
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/communications/models/location.py
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
<<<<<<< HEAD:communications/models/location.py
        db_table = 'locations'
        
    def __str__(self):
        return f"{self.address1}, {self.city}, {self.state}"
    
=======
        db_table = 'locations'
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/communications/models/location.py
