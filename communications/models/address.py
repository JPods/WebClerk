from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid

class Address(BaseModel):
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
    comment2 = models.TextField(blank=True, null=True)
    
    # Remove this line: dt_verified = models.DateTimeField(null=True, blank=True, help_text="When address was verified")

    @property
    def dt_verified(self):
        """Get verified timestamp from metadata.history.verified.dt."""
        if not self.metadata:
            return None
        verified_dt_ms = self.metadata.get('history', {}).get('verified', {}).get('dt', 0)
        if verified_dt_ms:
            return timezone.datetime.fromtimestamp(verified_dt_ms / 1000, tz=timezone.get_current_timezone())
        return None

    class Meta:
        db_table = 'addresses'
        
    def __str__(self):
        return f"{self.address1}, {self.city}, {self.state}"
    