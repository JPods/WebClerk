import uuid
from django.db import models

from common.models import BaseModel
from apps.core.services.access import CONNECTION_ROLES
from apps.sync.choices import (
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


CONNECTION_ROLE_CHOICES = [(r, r) for r in CONNECTION_ROLES]
SCOPE_KEYS = ('customer', 'vendor', 'manufacturer', 'employee', 'rep')


def validate_connection_scope(scope) -> None:
    """A scope names org types and lists integer ids — nothing else rides in it."""
    from django.core.exceptions import ValidationError
    if not isinstance(scope, dict):
        raise ValidationError({'scope': 'scope is an object of org type → [ids]'})
    for key, ids in scope.items():
        if key not in SCOPE_KEYS:
            raise ValidationError({'scope': f'unknown scope key {key!r}; one of {SCOPE_KEYS}'})
        if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool)
                                                for i in ids):
            raise ValidationError({'scope': f'scope.{key} is a list of integer ids'})


class Connection(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=CONNECTION_TYPE_CHOICES)
    # config inherited from CoreModel
        #endpoints = models.JSONField(blank=True, null=True)
        #schedule = models.JSONField(blank=True, null=True)
        #path = models.JSONField(blank=True, null=True)
        #direction = models.CharField(max_length=255, blank=True)
        #path_completed = models.CharField(max_length=255, blank=True, null=True)
        #path_working = models.CharField(max_length=255, blank=True, null=True)
        #key = models.CharField(max_length=255, blank=True, null=True)
        #pin = models.CharField(max_length=255, blank=True, null=True)
    # status — inherited from CoreModel
    scripts = models.JSONField(blank=True, null=True)
    relationships = models.JSONField(blank=True, null=True)
    action = models.CharField(max_length=255, blank=True)
    #rules and paths for converting between datasets
    maps = models.JSONField(blank=True, null=True)
    encryption = models.JSONField(blank=True, null=True)
    rules = models.JSONField(blank=True, null=True)
    conflicts = models.JSONField(blank=True, null=True)
    changes = models.JSONField(blank=True, null=True)
    # Authority, not data (Bill, 2026-09-23): a Connection is a pipe that holds one role in
    # code plus the ids it speaks for. The door guards a sync actor by these exactly as it
    # guards a login by its role and org ids. No role = sees and writes nothing; an inactive
    # Connection holds no role. Only staff may write Connections (STAFF_ONLY_MODELS).
    role = models.CharField(max_length=30, blank=True, default='', choices=CONNECTION_ROLE_CHOICES,
                            help_text='The role this Connection acts as (access.CONNECTION_ROLES)')
    scope = models.JSONField(default=dict, blank=True,
                             help_text='Ids this Connection speaks for, e.g. {"vendor": [12]}')

    class Meta:
        db_table = 'connections'

    def save(self, *args, **kwargs):
        # Fail fast: a malformed grant is refused at the door, never stored and read loosely.
        from django.core.exceptions import ValidationError
        if self.role and self.role not in CONNECTION_ROLES:
            raise ValidationError({'role': f'{self.role!r} is not a Connection role; one of {CONNECTION_ROLES}'})
        validate_connection_scope(self.scope if self.scope is not None else {})
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name or 'Connection'} ({self.id})"
    
