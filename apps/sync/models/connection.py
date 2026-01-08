import uuid
from django.db import models

from common.models import BaseModel
from apps.sync.choices import (
    CONNECTION_PURPOSE_CHOICES,
    CONNECTION_STATUS_CHOICES,
    CONNECTION_TYPE_CHOICES,
)

# Mapping Tables
# Store relationships between local IDs and remote IDs (or UUIDs) for synchronization.
# Example: local_id, remote_id, uuid, source_system, sync_status.
# 2. Audit Logs
# Track every exchange, including timestamps, user, action, and status.
# Useful for troubleshooting and compliance.
# 3. Change Tracking
# Store hashes or version numbers for records to detect changes and avoid unnecessary updates.
# 4. Conflict Resolution
# Add fields or tables to record and resolve data conflicts (e.g., last updated, source of truth).
# 5. Status/Sync Flags
# Fields like synced, pending_sync, failed_sync, last_synced_at to manage and monitor sync status.
# 6. Transformation Rules
# Store rules or scripts for transforming data between formats (e.g., field mapping, type conversion).
# 7. Error Handling
# Tables or logs for failed exchanges, including error messages and retry logic.
# 8. Batch/Job Management
# Track batches of exchanges, job status, and results for bulk operations.
# 9. Metadata
# Store metadata about each exchange (e.g., source, destination, schema version, API version).
# 10. Encryption/Integrity
# Store checksums, signatures, or encryption keys for sensitive data exchanges.
# 11. Webhook/Event Log
# Log events or triggers for real-time updates and notifications.


class Connection(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=CONNECTION_TYPE_CHOICES)
    config = models.JSONField()
    comment = models.TextField(blank=True, default="", help_text="General notes")
        #endpoints = models.JSONField(blank=True, null=True)
        #schedule = models.JSONField(blank=True, null=True)
        #path = models.JSONField(blank=True, null=True)
        #direction = models.CharField(max_length=255, blank=True)
        #path_completed = models.CharField(max_length=255, blank=True, null=True)
        #path_working = models.CharField(max_length=255, blank=True, null=True)
        #key = models.CharField(max_length=255, blank=True, null=True)
        #pin = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=CONNECTION_STATUS_CHOICES,
    )
    scripts = models.JSONField(blank=True, null=True)
    relationships = models.JSONField(blank=True, null=True)
    action = models.CharField(max_length=255, blank=True)
    purpose = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=CONNECTION_PURPOSE_CHOICES,
    )
    #rules and paths for converting between datasets
    maps = models.JSONField(blank=True, null=True)
    encryption = models.JSONField(blank=True, null=True)
    rules = models.JSONField(blank=True, null=True)
    conflicts = models.JSONField(blank=True, null=True)
    changes = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'connections'

    def __str__(self):
        return f"{self.name or 'Connection'} ({self.id})"
    
