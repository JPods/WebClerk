from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid

# Explanation: Records for tracking fidelity to mission.

class Feedback(BaseModel):
    user_id = models.UUIDField()
    name = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    status = models.CharField(max_length=255, default='new')

    class Meta:
        db_table = 'feedback'
