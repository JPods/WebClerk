# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/pending.py
from django.db import models
import uuid
from django.utils import timezone
from common.models import default_metadata, default_refs, default_prefs, default_data

class Pending(models.Model):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    record_id = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(default=default_data)  # <-- always initialized
    metadata = models.JSONField(default=default_metadata)  # <-- always initialized
    prefs = models.JSONField(default=default_prefs)  # <-- always initialized
    refs = models.JSONField(default=default_refs)  # <-- always initialized
    dt_processed = models.BigIntegerField(default=0)  # 0 means not processed

    class Meta:
        db_table = 'pending'

    def save(self, *args, **kwargs):
        now_timestamp = int(timezone.now().timestamp() * 1000)
        user_id = getattr(self, 'created_by_id', 0)

        super().save(*args, **kwargs)

     # all metadata actions inside common/models/BaseModel.py

    def is_processed(self):
        """Return True if processed, False otherwise"""
        return self.dt_processed > 0


    def __str__(self):
        return f"{self.table_name}:{self.record_id}"