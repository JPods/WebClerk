from django.db import models
from common.models import BaseModel

class Phone(BaseModel):
    """Model for storing phone information."""
    attention = models.CharField(max_length=255, blank=True)
    country_code = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=255, blank=True)
    opt_out = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'phones'