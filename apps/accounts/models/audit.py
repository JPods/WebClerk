from django.db import models
from common.models import BaseModel
from django.utils import timezone
# bulk of this table is in the .refs to relate other tables
# example use is to link line items in orders, proposals, etc. 
# with one document that passes on specs, paths, comments, and other details
class Audit(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    # heavily uses .refs and .metadata
    conflicts = models.JSONField(blank=True, null=True)
    changes = models.JSONField(blank=True, null=True)
    actions = models.JSONField(blank=True, null=True)
    recommendations = models.JSONField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    is_completed = models.BooleanField(default=True)
    priority = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'audits'

    def __str__(self):
        return f"{self.name or 'Audit'} ({self.id})"
    