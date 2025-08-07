import uuid
from django.db import models
from django.utils import timezone
from common.models import BaseModel

class Cache(BaseModel):

    ida = models.CharField(max_length=255, unique=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    table_name = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    references = models.JSONField(null=True, blank=True)



    class Meta:
        db_table = 'caches'

    def __str__(self):
        return f"{self.cache or 'Cache'} ({self.uuid})"