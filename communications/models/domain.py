from django.db import models
from common.models import BaseModel

class Domain(BaseModel):
    """Model for storing domain information."""
    path = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'domains'