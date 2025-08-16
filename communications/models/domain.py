# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/models/domain.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid

class Domain(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    path = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True, null=True)
    # Remove this line: dt_verified = models.DateTimeField(null=True, blank=True, help_text="When domain was verified")

    # all metadata changes inside common/models/BaseModel.py

    class Meta:
        db_table = 'domains'
        
    def __str__(self):
        return f"{self.path}, {self.type}"
    