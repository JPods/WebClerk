from django.db import models
from common.models import BaseModel

class Email(BaseModel):
    """Model for storing email information."""
    address = models.CharField(max_length=255, blank=True)
    attention = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    opt_out = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'emails'