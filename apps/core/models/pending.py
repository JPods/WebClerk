from django.db import models
from django.utils import timezone
from common.models import CoreModel, default_data


class Pending(CoreModel):
    """Ephemeral queue / staging record (CoreModel only).

    Lightweight by design: no metadata/refs/prefs/comments overhead.
    Use for decoupling write spikes & deferred processing.
    """
    # Canonical model identifier
    model_name = models.CharField(max_length=255, blank=True, null=True)
    id_record = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    purpose = models.CharField(max_length=120, blank=True, null=True)
    name = models.CharField(max_length=120, blank=True, null=True)
    data = models.JSONField(default=default_data)
    dt_processed = models.BigIntegerField(default=0, db_index=True)

    class Meta:
        db_table = 'pending'
        indexes = [
            models.Index(fields=['model_name']),
            models.Index(fields=['id_record']),
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
        return f"{self.model_name}:{self.id_record} (processed={self.is_processed()})"