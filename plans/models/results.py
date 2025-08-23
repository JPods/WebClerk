from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid


# Explanation: Outcomes of action taken in objectives, may be it should be a lines object in objectives.
# Consider fields like result_description, impact, and related_objective (ForeignKey to Objective).

class Result(BaseModel):
    objective = models.ForeignKey('Objective', on_delete=models.CASCADE, related_name='results')
    comment = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    publish = models.IntegerField(blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    web_path = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name or str(self.uuid)
