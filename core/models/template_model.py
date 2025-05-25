import uuid
from django.db import models
from django.db.models import JSONField

class Template(models.Model):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    refs = JSONField(default=dict)
    prefs = JSONField(default=dict)
    metadata = JSONField(default=dict)

    class Meta:
        db_table = 'templates'

    def __str__(self):
        return f"{self.name or 'Template'} ({self.uuid})"