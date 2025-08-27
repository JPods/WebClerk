# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/models/phone.py
from django.db import models
<<<<<<< HEAD:communications/models/phone.py
from common.models import BaseModel
from django.utils import timezone  # Add this import
=======
from common.base_model import BaseModel
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/communications/models/phone.py
import uuid

class Phone(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    number = models.CharField(max_length=20, blank=True, help_text="Phone number")
    country_code = models.CharField(max_length=5, blank=True, help_text="Country code (e.g., +1)")
    format = models.CharField(max_length=50, blank=True, help_text="Formatted phone number")
    name = models.CharField(max_length=100, blank=True, help_text="Display name for this phone")
    attention = models.CharField(max_length=100, blank=True, help_text="Person or department attention line")
    opt_out = models.BooleanField(default=False, help_text="Opted out of communications")
    comment = models.TextField(blank=True, null=True, help_text="Additional notes about this phone")
    
    # Remove this database field - now using metadata
    # dt_verified = models.DateTimeField(null=True, blank=True, help_text="When phone was verified")

    class Meta:
        db_table = 'phones'
        verbose_name = 'Phone Number'
        verbose_name_plural = 'Phone Numbers'
        
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.number})"
        return self.number
