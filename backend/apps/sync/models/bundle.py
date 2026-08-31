from django.db import models

from common.models import BaseModel
from apps.sync.choices import (
    BUNDLE_ALERT_CHOICES,
    BUNDLE_DIRECTION_CHOICES,
    BUNDLE_STATUS_CHOICES,
)
from .connection import Connection  # Relative import


class Bundle(BaseModel):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='bundles', db_column='connection_id')
    direction = models.CharField(max_length=255, choices=BUNDLE_DIRECTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True, default="", db_index=True)
    # config inherited from CoreModel
    # status — inherited from CoreModel
    dt_processed = models.BigIntegerField(default=0, db_index=True)
    alert = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=BUNDLE_ALERT_CHOICES,
    )
    response = models.JSONField(blank=True, null=True)
    duration = models.BigIntegerField(default=0)
    # payload is DEPRECATED — payloads go to disk via bundle_storage.py.
    # Field kept for migration; new code must not write to it.
    payload = models.JSONField(blank=True, null=True)
    size = models.BigIntegerField(default=0)
    #at the time of the bundle
    maps = models.JSONField(blank=True, null=True)
    encryption = models.JSONField(blank=True, null=True)
    rules = models.JSONField(blank=True, null=True)
    conflicts = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'bundles'

    def __str__(self):
        return f"Bundle {self.id} ({self.model_name or 'general'}) for connection {self.connection.id}"

    def get_payload(self):
        """Load payload from disk. Falls back to DB field for legacy records."""
        payload_path = (self.config or {}).get("payload_path")
        if payload_path:
            from apps.sync.services.bundle_storage import load_payload_by_path
            return load_payload_by_path(payload_path)
        # Legacy fallback — old records still have payload in DB
        return self.payload

    def save_payload_to_disk(self, payload_data):
        """Write payload to disk and store path in config. Clears DB payload field."""
        from apps.sync.services.bundle_storage import save_payload
        path = save_payload(
            bundle_id=self.pk,
            model_name=self.model_name or "general",
            direction=self.direction or "incoming",
            payload=payload_data,
        )
        config = self.config if isinstance(self.config, dict) else {}
        config["payload_path"] = path
        self.config = config
        self.payload = None
        self.save(update_fields=["config", "payload", "dt_modified", "version"])