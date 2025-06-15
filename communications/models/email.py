from django.db import models
from common.models import BaseModel
import uuid

class Email(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    address = models.CharField(max_length=255, blank=True)
    attention = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    opt_out = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'emails'