from django.db import models
from django.utils import timezone
from common.models import CoreModel


class Pending(CoreModel):
    """Ephemeral queue / staging record (CoreModel only).

    Lightweight by design: no metadata/refs/prefs/comments overhead.
    Use for decoupling write spikes & deferred processing.
    """
    # Canonical model identifier
    model_name = models.CharField(max_length=255, blank=True, null=True)
    record_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=120, blank=True, null=True)
    dt_processed = models.BigIntegerField(default=0, db_index=True)
    sequence = models.PositiveIntegerField(default=0, help_text="Order within a connection. 0 = unordered.")
    attempts = models.PositiveIntegerField(default=0)
    changes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'pending'
        indexes = [
            models.Index(fields=['model_name']),
            models.Index(fields=['record_id']),
            models.Index(fields=['dt_processed']),
        ]

    def mark_processed(self, save: bool = True):
        if self.dt_processed == 0:
            self.dt_processed = int(timezone.now().timestamp() * 1000)
            if save:
                self.save(update_fields=['dt_processed', 'dt_modified', 'version'])
        return self.dt_processed

    def is_processed(self):
        return self.dt_processed > 0

    def __str__(self):
        return f"{self.model_name}:{self.record_id} (processed={self.is_processed()})"