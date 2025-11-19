from django.db import models
from common.models import BaseModel

class Template(BaseModel):
    purpose = models.CharField(max_length=120, blank=True, null=True)
    name = models.CharField(max_length=120, blank=True, null=True)
    data = models.JSONField(default=dict)
    dt_processed = models.BigIntegerField(default=0, db_index=True)
    

    class Meta:
        db_table = 'templates'

    def __str__(self):
        return f"{self.name or 'Template'} ({self.id})"