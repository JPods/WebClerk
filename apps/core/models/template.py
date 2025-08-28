# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/template.py
import uuid
from django.db import models
from common.models import BaseModel

class Template(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'templates'

    def __str__(self):
        return f"{self.name or 'Template'} ({self.id})"