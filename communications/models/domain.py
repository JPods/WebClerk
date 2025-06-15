from django.db import models
from common.models import BaseModel
import uuid

class Domain(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    path = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'domains'