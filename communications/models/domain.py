from django.db import models
from common.models import BaseModel
import uuid

class Domain(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    path = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True, null=True)
    dt_verified = models.DateTimeField(null=True, blank=True, help_text="When email was verified")

    
    class Meta:
        db_table = 'domains'
        
    def __str__(self):
        return f"{self.path}, {self.type}"
    
    class Meta:
        db_table = 'domains'