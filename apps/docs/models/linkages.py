# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/models/domain.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone

class Linkage(BaseModel):
    comment = models.TextField(blank=True, null=True)
    # heavily uses .refs
   
