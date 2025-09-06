import uuid
from django.db import models
from common.models import BaseModel

class Template(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    

    class Meta:
        db_table = 'templates'

    def __str__(self):
        return f"{self.name or 'Template'} ({self.id})"