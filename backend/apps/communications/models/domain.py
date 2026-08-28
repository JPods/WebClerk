# path: apps/communications/models/domain.py
from django.db import models

from common.models import BaseModel
from apps.communications.choices import DOMAIN_STATUS_CHOICES, DOMAIN_TYPE_CHOICES

class Domain(BaseModel):
    # Value, not FK — communications survive contact deactivation.
    # Alice watches for orphan records.
    contact_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Contact id (value, not FK — no cascade)"
    )
    
    path = models.CharField(max_length=255, blank=True, db_index=True, help_text="URL or handle (indexed)")
    type = models.CharField(max_length=50, blank=True, choices=DOMAIN_TYPE_CHOICES, default="", db_index=True)
    # status — inherited from CoreModel
    sequence = models.PositiveIntegerField(default=0, db_index=True, help_text="Custom ordering value")
    count_accessed = models.PositiveIntegerField(default=0, help_text="Access counter")

    # all metadata changes inside common/models/BaseModel.py

    class Meta:
        db_table = 'domains'
        indexes = [
            models.Index(fields=['contact_id']),
            models.Index(fields=['path']),
            models.Index(fields=['type', 'status']),
        ]
        
    def __str__(self):
        return f"{self.path}, {self.type}"

    # lightweight helpers
    def increment_access(self, by: int = 1, save: bool = True):
        self.count_accessed = (self.count_accessed or 0) + by
        if save:
            self.save(update_fields=['count_accessed', 'dt_modified', 'version'])
        return self.count_accessed
    
    def queue_verification(self, connection_name: str | None = None) -> None:
        try:
            from apps.communications.tasks import validate_domain_basic
            validate_domain_basic(self.pk)
        except Exception:
            pass
    